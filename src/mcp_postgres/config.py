"""PostgreSQL配置模块"""

import os
import yaml
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

@dataclass
class PostgresConfig:
    dbname: str
    user: str
    password: str
    host: str = 'localhost'
    port: str = '5432'
    local_host: Optional[str] = None
    debug: bool = False

    @classmethod
    def from_yaml(cls, yaml_path: str, local_host: Optional[str] = None) -> 'PostgresConfig':
        """从YAML文件创建配置"""
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
            db_config = config.get('database', {})
            return cls(
                dbname=db_config.get('dbname', ''),
                user=db_config.get('user', ''),
                password=db_config.get('password', ''),
                host=db_config.get('host', 'localhost'),
                port=str(db_config.get('port', 5432)),
                local_host=local_host,
                debug=os.environ.get('MCP_DEBUG', '').lower() in ('1', 'true')
            )

    @classmethod
    def from_url(cls, url: str, local_host: Optional[str] = None) -> 'PostgresConfig':
        """从URL创建配置"""
        parsed = urlparse(url)
        return cls(
            dbname=parsed.path[1:],
            user=parsed.username or '',
            password=parsed.password or '',
            host=parsed.hostname or 'localhost',
            port=str(parsed.port or 5432),
            local_host=local_host,
            debug=os.environ.get('MCP_DEBUG', '').lower() in ('1', 'true')
        )

    def get_connection_params(self) -> dict:
        """获取psycopg2连接参数"""
        params = {
            'dbname': self.dbname,
            'user': self.user,
            'password': self.password,
            'host': self.local_host or self.host,
            'port': self.port
        }
        return {k: v for k, v in params.items() if v}