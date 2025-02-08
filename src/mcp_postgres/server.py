"""PostgreSQL MCP 服务器实现"""

import asyncio
import sys
import yaml
import argparse
from typing import Optional
from contextlib import asynccontextmanager

import psycopg2
from psycopg2.pool import SimpleConnectionPool
from mcp.server import Server, NotificationOptions
import mcp.types as types
from mcp.server.stdio import stdio_server

from .config import PostgresConfig
from .log import create_logger

class PostgresServer:
    def __init__(self, config: PostgresConfig):
        self.config = config
        self.log = create_logger("postgres", config.debug)

        # 创建连接池
        try:
            conn_params = config.get_connection_params()
            masked_conn_params = config.get_masked_connection_info()
            self.log("debug", f"正在连接数据库，参数: {masked_conn_params}")

            # 测试连接
            test_conn = psycopg2.connect(**conn_params)
            test_conn.close()
            self.log("info", "测试连接成功")

            # 创建连接池
            self.pool = SimpleConnectionPool(1, 5, **conn_params)
            self.log("info", "数据库连接池创建成功")
        except psycopg2.Error as e:
            self.log("error", f"数据库连接失败: {str(e)}")
            raise

        # 初始化MCP服务器
        self.server = Server("postgres-server")
        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            """列出所有表资源"""
            try:
                conn = self.pool.getconn()
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            table_name,
                            obj_description(
                                (quote_ident(table_schema) || '.' || quote_ident(table_name))::regclass,
                                'pg_class'
                            ) as description
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                    tables = cur.fetchall()

                    return [
                        types.Resource(
                            uri=f"postgres://{self.config.host}/{table[0]}/schema",
                            name=f"{table[0]} schema",
                            description=table[1] if table[1] else None,
                            mimeType="application/json"
                        ) for table in tables
                    ]
            except psycopg2.Error as e:
                self.log("error", f"获取表列表失败: {str(e)}")
                raise
            finally:
                self.pool.putconn(conn)

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """读取表结构信息"""
            try:
                table_name = uri.split('/')[-2]
                conn = self.pool.getconn()
                with conn.cursor() as cur:
                    # 获取列信息
                    cur.execute("""
                        SELECT 
                            column_name,
                            data_type,
                            is_nullable,
                            col_description(
                                (quote_ident(table_schema) || '.' || quote_ident(table_name))::regclass,
                                ordinal_position
                            ) as description
                        FROM information_schema.columns 
                        WHERE table_name = %s
                        ORDER BY ordinal_position
                    """, (table_name,))
                    columns = cur.fetchall()

                    # 获取约束信息
                    cur.execute("""
                        SELECT
                            conname as constraint_name,
                            contype as constraint_type
                        FROM pg_constraint c
                        JOIN pg_class t ON c.conrelid = t.oid
                        WHERE t.relname = %s
                    """, (table_name,))
                    constraints = cur.fetchall()

                    return str({
                        'columns': [{
                            'name': col[0],
                            'type': col[1],
                            'nullable': col[2] == 'YES',
                            'description': col[3]
                        } for col in columns],
                        'constraints': [{
                            'name': con[0],
                            'type': con[1]
                        } for con in constraints]
                    })
            except psycopg2.Error as e:
                self.log("error", f"读取表结构失败: {str(e)}")
                raise
            finally:
                self.pool.putconn(conn)

        @self.server.list_tools()
        async def handle_list_tools(self) -> list[types.Tool]:
            """列出可用的工具"""
            return [
                types.Tool(
                    name="query_db",
                    description="在指定的数据库配置上执行只读SQL查询",
                    properties={
                        "database_profile": {
                            "type": "string",
                            "description": "数据库配置名称，例如：compass-prod, compass-staging等",
                            "required": True
                        },
                        "sql": {
                            "type": "string",
                            "description": "SQL查询语句（仅支持SELECT）",
                            "required": True
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_query_db(self, name: str, arguments: dict) -> list[types.TextContent]:
            """处理数据库查询"""
            if name != "query_db":
                return [types.TextContent(type="text", text=f"未知工具: {name}")]

            profile_name = arguments.get("database_profile")
            sql = arguments.get("sql", "").strip()

            if not profile_name:
                return [types.TextContent(type="text", text="必须提供数据库配置名称")]
            if not sql:
                return [types.TextContent(type="text", text="SQL查询不能为空")]
            if not sql.lower().startswith("select"):
                return [types.TextContent(type="text", text="仅支持SELECT查询")]

            try:
                # 使用指定的数据库配置
                config = PostgresConfig.from_yaml(self.config_path, profile_name, self.local_host)
                conn_params = config.get_connection_params()

                self.log("info", f"在数据库 {profile_name} 上执行查询: {sql}")

                # 建立连接并执行查询
                conn = psycopg2.connect(**conn_params)
                try:
                    with conn.cursor() as cur:
                        cur.execute("BEGIN TRANSACTION READ ONLY")
                        try:
                            cur.execute(sql)
                            results = cur.fetchall()
                            columns = [desc[0] for desc in cur.description]

                            formatted_results = [dict(zip(columns, row)) for row in results]
                            result_text = str({
                                'columns': columns,
                                'rows': formatted_results,
                                'row_count': len(results)
                            })

                            self.log("info", f"查询完成，返回{len(results)}行结果")
                            return [types.TextContent(type="text", text=result_text)]
                        finally:
                            cur.execute("ROLLBACK")
                finally:
                    conn.close()
            except Exception as e:
                error_msg = f"数据库操作失败: {str(e)}"
                self.log("error", error_msg)
                return [types.TextContent(type="text", text=error_msg)]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """处理工具调用"""
            if name != "query":
                raise ValueError(f"未知工具: {name}")

            sql = arguments.get("sql", "").strip()
            if not sql:
                raise ValueError("SQL查询不能为空")

            # 仅允许SELECT语句
            if not sql.lower().startswith("select"):
                raise ValueError("仅支持SELECT查询")

            self.log("info", f"执行查询: {sql}")

            try:
                conn = self.pool.getconn()
                with conn.cursor() as cur:
                    # 启动只读事务
                    cur.execute("BEGIN TRANSACTION READ ONLY")
                    try:
                        cur.execute(sql)
                        results = cur.fetchall()
                        columns = [desc[0] for desc in cur.description]

                        formatted_results = [dict(zip(columns, row)) for row in results]
                        result_text = str({
                            'columns': columns,
                            'rows': formatted_results,
                            'row_count': len(results)
                        })

                        self.log("info", f"查询完成，返回{len(results)}行结果")
                        return [types.TextContent(type="text", text=result_text)]
                    finally:
                        cur.execute("ROLLBACK")
            except psycopg2.Error as e:
                error_msg = f"查询执行失败: {str(e)}"
                self.log("error", error_msg)
                return [types.TextContent(type="text", text=error_msg)]
            finally:
                self.pool.putconn(conn)

    async def run(self):
        """运行服务器"""
        async with stdio_server() as streams:
            await self.server.run(
                streams[0],
                streams[1],
                self.server.create_initialization_options()
            )

    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'pool'):
            self.log("info", "关闭数据库连接池")
            self.pool.closeall()

async def run_server():
    """服务器实际运行逻辑"""
    parser = argparse.ArgumentParser(description='MCP PostgreSQL Server')
    parser.add_argument('--config', help='YAML配置文件路径')
    parser.add_argument('--database-url', help='数据库连接URL（可选，优先使用配置文件）')
    parser.add_argument('--local-host', help='本地主机地址', default=None)
    parser.add_argument('--db-name', help='要使用的数据库配置名称')

    args = parser.parse_args()
    logger = create_logger("postgres", False)

    try:
        if args.config:
            # 首先检查所有数据库连接
            with open(args.config, 'r') as f:
                config_data = yaml.safe_load(f)

            success = False
            available_dbs = []
            for db_name in config_data['databases'].keys():
                try:
                    test_config = PostgresConfig.from_yaml(args.config, db_name, args.local_host)
                    conn_params = test_config.get_connection_params()

                    # 测试连接
                    test_conn = psycopg2.connect(**conn_params)
                    test_conn.close()
                    logger("info", f"数据库 {db_name} 连接成功")
                    success = True
                    available_dbs.append(db_name)
                except Exception as e:
                    logger("warning", f"数据库 {db_name} 连接失败: {str(e)}")

            if not success:
                raise ConnectionError("所有数据库连接均失败")

            # 如果没有指定数据库名称，使用第一个可用的数据库
            selected_db = args.db_name if args.db_name else available_dbs[0]
            config = PostgresConfig.from_yaml(args.config, selected_db, args.local_host)

        elif args.database_url:
            config = PostgresConfig.from_url(args.database_url, args.local_host)
        else:
            raise ValueError("必须提供配置文件路径或数据库URL")

        server = PostgresServer(config)
        await server.run()
    except KeyboardInterrupt:
        print("\n服务器已停止", file=sys.stderr)
    finally:
        if 'server' in locals():
            server.cleanup()

def main():
    """命令行入口函数"""
    asyncio.run(run_server())

if __name__ == "__main__":
    main()
