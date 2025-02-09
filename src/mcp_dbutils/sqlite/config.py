"""SQLite configuration module"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, Literal
from ..config import DatabaseConfig

@dataclass
class SqliteConfig(DatabaseConfig):
    path: str
    password: Optional[str] = None
    uri: bool = True  # 启用 URI 模式以支持密码等参数
    type: Literal['sqlite'] = 'sqlite'

    @property
    def absolute_path(self) -> str:
        """返回数据库文件的绝对路径"""
        return str(Path(self.path).expanduser().resolve())

    def get_connection_params(self) -> Dict[str, Any]:
        """获取 sqlite3 连接参数"""
        if not self.password:
            return {'database': self.absolute_path, 'uri': self.uri}

        # 如果有密码,使用 URI 格式
        uri = f"file:{self.absolute_path}?mode=rw"
        if self.password:
            uri += f"&password={self.password}"

        return {
            'database': uri,
            'uri': True
        }

    def get_masked_connection_info(self) -> Dict[str, Any]:
        """返回用于日志的连接信息"""
        info = {
            'database': self.absolute_path,
            'uri': self.uri
        }
        if self.password:
            info['password'] = '******'
        return info

    @classmethod
    def from_yaml(cls, yaml_path: str, db_name: str, **kwargs) -> 'SqliteConfig':
        """从YAML配置创建SQLite配置

        Args:
            yaml_path: YAML配置文件路径
            db_name: 数据库配置名称
        """
        configs = cls.load_yaml_config(yaml_path)

        if db_name not in configs:
            available_dbs = list(configs.keys())
            raise ValueError(f"未找到数据库配置: {db_name}。可用的数据库配置: {available_dbs}")

        db_config = configs[db_name]

        if 'type' not in db_config:
            raise ValueError(f"数据库配置必须包含 type 字段")
        if db_config['type'] != 'sqlite':
            raise ValueError(f"该配置不是SQLite数据库类型: {db_config['type']}")
        if 'path' not in db_config:
            raise ValueError(f"SQLite配置必须包含 path 字段")

        config = cls(
            path=db_config['path'],
            password=db_config.get('password'),
            uri=True
        )
        config.debug = cls.get_debug_mode()
        return config
