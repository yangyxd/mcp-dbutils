"""PostgreSQL configuration module"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from ..config import DatabaseConfig
@dataclass
class PostgresConfig(DatabaseConfig):
    dbname: str
    user: str
    password: str
    host: str = 'localhost'
    port: str = '5432'
    local_host: Optional[str] = None
    @classmethod
    def from_yaml(cls, yaml_path: str, db_name: str, local_host: Optional[str] = None) -> 'PostgresConfig':
        """从YAML文件创建配置
        Args:
            yaml_path: YAML配置文件路径
            db_name: 要使用的数据库配置名称
            local_host: 可选的本地主机地址
        """
        configs = cls.load_yaml_config(yaml_path)
        if not db_name:
            raise ValueError("必须指定数据库名称")
        if db_name not in configs:
            available_dbs = list(configs.keys())
            raise ValueError(f"未找到数据库配置: {db_name}。可用的数据库配置: {available_dbs}")
        db_config = configs[db_name]
        config = cls(
            dbname=db_config.get('dbname', ''),
            user=db_config.get('user', ''),
            password=db_config.get('password', ''),
            host=db_config.get('host', 'localhost'),
            port=str(db_config.get('port', 5432)),
            local_host=local_host,
        )
        config.debug = cls.get_debug_mode()
        return config
    def get_connection_params(self) -> Dict[str, Any]:
        """获取psycopg2连接参数"""
        params = {
            'dbname': self.dbname,
            'user': self.user,
            'password': self.password,
            'host': self.local_host or self.host,
            'port': self.port
        }
        return {k: v for k, v in params.items() if v}
    def get_masked_connection_info(self) -> Dict[str, Any]:
        """返回脱敏的连接信息，用于日志输出"""
        return {
            'dbname': self.dbname,
            'host': self.local_host or self.host,
            'port': self.port
        }
