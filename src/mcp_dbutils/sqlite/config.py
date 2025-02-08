"""SQLite configuration module"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any
from ..config import DatabaseConfig

@dataclass
class SqliteConfig(DatabaseConfig):
    db_path: str

    @property
    def absolute_path(self) -> str:
        """返回数据库文件的绝对路径"""
        return str(Path(self.db_path).expanduser().resolve())

    def get_connection_params(self) -> Dict[str, Any]:
        """获取 sqlite3 连接参数"""
        return {
            'database': self.absolute_path
        }

    def get_masked_connection_info(self) -> Dict[str, Any]:
        """返回用于日志的连接信息"""
        return {
            'database': self.absolute_path
        }
