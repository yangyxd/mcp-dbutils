"""MySQL MCP server implementation"""
import threading
from typing import Optional
import mcp.types as types
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB

# 获取包信息用于日志命名
from ..base import LOG_NAME, ConnectionServer
from ..log import create_logger
from .config import MySQLConfig


class MySQLServer(ConnectionServer):
    _instance: dict[str, PooledDB] = {}
    _lock = threading.RLock()
    
    def __init__(self, config: MySQLConfig, config_path: Optional[str] = None):
        """初始化MySQL服务器
        Args:
            config: 数据库配置
            config_path: 配置文件路径(可选)
        """
        super().__init__(config_path, config.debug)
        self.config = config
        self.config_path = config_path
        self.log = create_logger(f"{LOG_NAME}.db.mysql", config.debug)
        # 创建连接池
        try:
            masked_params = config.get_masked_connection_info()
            self.log("debug", f"正在连接数据库，参数: {masked_params}")
            self.pool = self.get_connection(self.config.get_connection_params())
            self.log("info", "连接池创建成功")
        except Exception as e:
            self.log("error", f"连接失败: {str(e)}")
            raise
        
    def get_connection(self, mysql_config: dict) -> PooledDB:
        key = f"{mysql_config['host']}:{mysql_config['port']}:{mysql_config['database']}"
        with MySQLServer._lock:
            if key not in MySQLServer._instance:
                host = mysql_config["host"]
                port = mysql_config["port"]
                username = mysql_config["user"]
                database = mysql_config["database"]
                self.log('info', "Connect mysql ... (host: {}:{}, database: {})", host, port, database)
                while True:
                    try:
                        MySQLServer._instance[key] = PooledDB(creator=pymysql,  # 使用链接数据库的模块
                                            maxconnections=200,  # 连接池允许的最大连接数
                                            mincached=5,  # 初始化时，链接池中至少创建的空闲的链接
                                            maxcached=5,  # 链接池中最多闲置的链接
                                            maxshared=2,  # 链接池中最多共享的链接数量
                                            blocking=True,  # 连接池中如果没有可用连接后，是否阻塞等待
                                            autocommit=True,  # 是否自动提交
                                            host=host,  # 数据库服务器地址
                                            port=port,  # 数据库服务器端口
                                            user=username,  # 数据库用户名
                                            password=str(mysql_config["password"]),  # 数据库密码
                                            database=database,  # 数据库名
                                            cursorclass=DictCursor)
                        break
                    except Exception as e:
                        self.log('error', 'Connect mysql failed. host: {}:{}, username: {}, database: {}, {}', host, port, username, database, str(e))
                self.log('info', 'Connect mysql success.')
            return MySQLServer._instance[key]
        return None

    async def list_resources(self) -> list[types.Resource]:
        """列出所有表资源"""
        try:
            conn = self.pool.connection()
            with conn.cursor() as cur:  # NOSONAR - dictionary参数是正确的，用于返回字典格式的结果
                cur.execute("""
                    SELECT
                        table_name,
                        table_comment as description
                    FROM information_schema.tables
                    WHERE table_schema = %s
                """, (self.config.database,))
                tables = cur.fetchall()
                return [
                    types.Resource(
                        uri=f"mysql://{self.config.host}/{table['table_name']}/schema",
                        name=f"{table['table_name']} schema",
                        description=table['description'] if table['description'] else None,
                        mimeType="application/json"
                    ) for table in tables
                ]
        except Exception as e:
            error_msg = f"获取表列表失败: {str(e)}"
            self.log("error", error_msg)
            raise
        finally:
            conn.close()

    async def read_resource(self, uri: str) -> str:
        """读取表结构信息"""
        try:
            table_name = uri.split('/')[-2]
            conn = self.pool.connection()
            with conn.cursor() as cur:  # NOSONAR - dictionary参数是正确的，用于返回字典格式的结果
                # 获取列信息
                cur.execute("""
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_comment as description
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (self.config.database, table_name))
                columns = cur.fetchall()

                # 获取约束信息
                cur.execute("""
                    SELECT
                        constraint_name,
                        constraint_type
                    FROM information_schema.table_constraints
                    WHERE table_schema = %s AND table_name = %s
                """, (self.config.database, table_name))
                constraints = cur.fetchall()

                return str({
                    'columns': [{
                        'name': col['column_name'],
                        'type': col['data_type'],
                        'nullable': col['is_nullable'] == 'YES',
                        'description': col['description']
                    } for col in columns],
                    'constraints': [{
                        'name': con['constraint_name'],
                        'type': con['constraint_type']
                    } for con in constraints]
                })
        except Exception as e:
            error_msg = f"读取表结构失败: {str(e)}"
            self.log("error", error_msg)
            raise
        finally:
            conn.close()

    def get_tools(self) -> list[types.Tool]:
        """获取可用工具列表"""
        return [
            types.Tool(
                name="query",
                description="执行只读SQL查询",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "connection": {
                            "type": "string",
                            "description": "数据库连接名称（可选）"
                        },
                        "sql": {
                            "type": "string",
                            "description": "SQL查询语句（仅支持SELECT）"
                        }
                    },
                    "required": ["sql"]
                }
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[types.TextContent]:
        """执行工具调用"""
        if name != "query":
            raise ValueError(f"未知工具: {name}")
        sql = arguments.get("sql", "").strip()
        if not sql:
            raise ValueError("SQL查询不能为空")
        # 仅允许SELECT语句
        if not sql.lower().startswith("select"):
            raise ValueError("仅支持SELECT查询")

        connection = arguments.get("connection")
        conn = None
        results = []
        columns = []

        try:
            if connection and self.config_path:
                # 使用指定的数据库连接
                config = MySQLConfig.from_yaml(self.config_path, connection)
                conn_params = config.get_connection_params()
                masked_params = config.get_masked_connection_info()
                self.log("info", f"使用配置 {connection} 连接数据库: {masked_params}")
                pool = self.get_connection(conn_params)
                if not pool:
                    raise ValueError(f"无法获取连接池: {masked_params}")
                conn = pool.connection()
                self.log("info", f"连接成功，使用配置: {masked_params}")
            else:
                # 使用现有连接池
                conn = self.pool.connection()

            self.log("info", f"执行查询: {sql}")
            with conn.cursor() as cur:  # NOSONAR - dictionary参数是正确的，用于返回字典格式的结果
                # 设置只读事务
                cur.execute("SET TRANSACTION READ ONLY")
                try:
                    cur.execute(sql)
                    results = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                finally:
                    cur.execute("ROLLBACK")

            # 处理结果（在连接操作完成后）
            result_text = str({
                'type': 'mysql',
                'config_name': connection or 'default',
                'query_result': {
                    'columns': columns,
                    'rows': results,
                    'row_count': len(results)
                }
            })
            self.log("info", f"查询完成，返回{len(results)}行结果")
            return [types.TextContent(type="text", text=result_text)]

        except Exception as e:
            error = f"查询执行失败: {str(e)}"
            error_msg = str({
                'type': 'mysql',
                'config_name': connection or 'default',
                'error': error
            })
            self.log("error", error_msg)
            return [types.TextContent(type="text", text=error_msg)]
        finally:
            # 确保连接始终被关闭
            if conn:
                try:
                    conn.close()  # 关闭连接（连接池会自动处理）
                except Exception as e:
                    self.log("warning", f"关闭连接时出错: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        if hasattr(self, 'pool'):
            self.log("info", "关闭MySQL连接池")
            # MySQL连接池没有直接的closeall方法，但我们可以主动关闭连接
            try:
                # 尝试获取并关闭所有活动连接
                for _ in range(5):  # 假设最多有5个连接在池中
                    try:
                        conn = self.pool.connection()
                        conn.close()
                    except Exception as e:
                        # 如果没有更多连接或出现其他错误，跳出循环
                        self.log("debug", f"连接池清理: {str(e)}")
                        break
                self.log("info", "MySQL连接池清理完成")
            except Exception as e:
                self.log("warning", f"清理MySQL连接池时出错: {str(e)}")
