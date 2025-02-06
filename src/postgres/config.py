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
    local_host: Optional[str] = None  # 用于本地连接的主机地址

    @classmethod
    def from_url(cls, url: str, local_host: Optional[str] = None) -> 'PostgresConfig':
        parsed = urlparse(url)
        return cls(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            database=parsed.path[1:],  # 去掉开头的 /
            user=parsed.username or '',
            password=parsed.password or '',
            local_host=local_host
        )

    def get_connection_params(self) -> dict:
        """返回连接参数，根据是否有本地主机配置来调整"""
        params = {
            'host': self.local_host or self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'sslmode': self.sslmode
        }
        return {k: v for k, v in params.items() if v}