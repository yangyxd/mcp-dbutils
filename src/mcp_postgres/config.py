"""PostgreSQL配置模块"""

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

@dataclass
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: str = 'prefer'
    local_host: Optional[str] = None
    connect_timeout: int = 10
    application_name: str = 'mcp-postgres'
    debug: bool = False

    @classmethod
    def from_url(cls, url: str, local_host: Optional[str] = None) -> 'PostgresConfig':
        """从URL创建配置
        Args:
            url: 数据库URL
            local_host: 本地主机地址(可选)
        """
        parsed = urlparse(url)
        return cls(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            database=parsed.path[1:],
            user=parsed.username or '',
            password=parsed.password or '',
            local_host=local_host,
            debug=os.environ.get('MCP_DEBUG', '').lower() in ('1', 'true')
        )

    def get_connection_params(self) -> dict:
        """获取psycopg2连接参数"""
        params = {
            'host': self.local_host or self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'sslmode': self.sslmode,
            'connect_timeout': self.connect_timeout,
            'application_name': self.application_name
        }
        return {k: v for k, v in params.items() if v}