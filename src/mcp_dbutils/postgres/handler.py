"""PostgreSQL database handler implementation"""

import psycopg2
from psycopg2.pool import SimpleConnectionPool
import mcp.types as types

from ..base import DatabaseHandler
from .config import PostgresConfig

class PostgresHandler(DatabaseHandler):
    def __init__(self, config_path: str, database: str, debug: bool = False):
        """初始化 PostgreSQL 处理器

        Args:
            config_path: 配置文件路径
            database: 数据库配置名称
            debug: 是否开启调试模式
        """
        super().__init__(config_path, database, debug)
        self.config = PostgresConfig.from_yaml(config_path, database)

        # 初始化时不再创建连接池
        masked_params = self.config.get_masked_connection_info()
        self.log("debug", f"配置数据库，参数: {masked_params}")
        self.pool = None

    async def get_tables(self) -> list[types.Resource]:
        """获取所有表资源"""
        try:
            conn_params = self.config.get_connection_params()
            conn = psycopg2.connect(**conn_params)
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
                        uri=f"postgres://{self.database}/{table[0]}/schema",
                        name=f"{table[0]} schema",
                        description=table[1] if table[1] else None,
                        mimeType="application/json"
                    ) for table in tables
                ]
        except psycopg2.Error as e:
            error_msg = f"获取表列表失败: [Code: {e.pgcode}] {e.pgerror or str(e)}"
            self.log("error", error_msg)
            raise
        finally:
            if conn:
                conn.close()

    async def get_schema(self, table_name: str) -> str:
        """获取表结构信息"""
        try:
            conn_params = self.config.get_connection_params()
            conn = psycopg2.connect(**conn_params)
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
            error_msg = f"读取表结构失败: [Code: {e.pgcode}] {e.pgerror or str(e)}"
            self.log("error", error_msg)
            raise
        finally:
            if conn:
                conn.close()

    async def execute_query(self, sql: str) -> str:
        """执行SQL查询"""
        try:
            conn_params = self.config.get_connection_params()
            conn = psycopg2.connect(**conn_params)
            self.log("info", f"执行查询: {sql}")

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
                    return result_text
                finally:
                    cur.execute("ROLLBACK")
        except psycopg2.Error as e:
            error_msg = f"查询执行失败: [Code: {e.pgcode}] {e.pgerror or str(e)}"
            self.log("error", error_msg)
            raise
        finally:
            if conn:
                conn.close()

    async def cleanup(self):
        """清理资源"""
        # 由于不再使用连接池，cleanup 不需要特别的清理操作
        pass
