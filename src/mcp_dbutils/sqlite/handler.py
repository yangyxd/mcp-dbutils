"""SQLite database handler implementation"""

import sqlite3
from pathlib import Path
from contextlib import closing
import mcp.types as types

from ..base import DatabaseHandler
from .config import SqliteConfig

class SqliteHandler(DatabaseHandler):
    def __init__(self, config_path: str, database: str, debug: bool = False):
        """初始化 SQLite 处理器

        Args:
            config_path: 配置文件路径
            database: 数据库配置名称
            debug: 是否开启调试模式
        """
        super().__init__(config_path, database, debug)
        self.config = SqliteConfig.from_yaml(config_path, database)

        # 确保数据库目录存在
        db_file = Path(self.config.absolute_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # 初始化时不再测试连接
        self.log("debug", f"配置数据库: {self.config.get_masked_connection_info()}")

    def _get_connection(self):
        """获取数据库连接"""
        connection_params = self.config.get_connection_params()
        conn = sqlite3.connect(**connection_params)
        conn.row_factory = sqlite3.Row
        return conn

    async def get_tables(self) -> list[types.Resource]:
        """获取所有表资源"""
        try:
            with closing(self._get_connection()) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = cursor.fetchall()

                return [
                    types.Resource(
                        uri=f"sqlite://{self.database}/{table[0]}/schema",
                        name=f"{table[0]} schema",
                        mimeType="application/json"
                    ) for table in tables
                ]
        except sqlite3.Error as e:
            error_msg = f"获取表列表失败: {str(e)}"
            self.log("error", error_msg)
            raise

    async def get_schema(self, table_name: str) -> str:
        """获取表结构信息"""
        try:
            with closing(self._get_connection()) as conn:
                # 获取表结构
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()

                # 获取索引信息
                cursor = conn.execute(f"PRAGMA index_list({table_name})")
                indexes = cursor.fetchall()

                schema_info = {
                    'columns': [{
                        'name': col['name'],
                        'type': col['type'],
                        'nullable': not col['notnull'],
                        'primary_key': bool(col['pk'])
                    } for col in columns],
                    'indexes': [{
                        'name': idx['name'],
                        'unique': bool(idx['unique'])
                    } for idx in indexes]
                }

                return str(schema_info)
        except sqlite3.Error as e:
            error_msg = f"读取表结构失败: {str(e)}"
            self.log("error", error_msg)
            raise

    async def execute_query(self, sql: str) -> str:
        """执行SQL查询"""
        try:
            with closing(self._get_connection()) as conn:
                self.log("info", f"执行查询: {sql}")
                cursor = conn.execute(sql)
                results = cursor.fetchall()

                columns = [desc[0] for desc in cursor.description]
                formatted_results = [dict(zip(columns, row)) for row in results]

                result_text = str({
                    'columns': columns,
                    'rows': formatted_results,
                    'row_count': len(results)
                })

                self.log("info", f"查询完成，返回{len(results)}行结果")
                return result_text

        except sqlite3.Error as e:
            error_msg = f"查询执行失败: {str(e)}"
            self.log("error", error_msg)
            raise

    async def cleanup(self):
        """清理资源"""
        # SQLite不需要特别的清理操作
        pass
