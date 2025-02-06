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
    def from_yaml(cls, yaml_path: str, db_name: Optional[str] = None, local_host: Optional[str] = None) -> 'PostgresConfig':
        """从YAML文件创建配置

        Args:
            yaml_path: YAML配置文件路径
            db_name: 要使用的数据库配置名称
            local_host: 可选的本地主机地址
        """
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        if not db_name:
            # 如果未指定数据库名称，检查是否有默认值
            db_name = config.get('default')
            if not db_name:
                raise ValueError("必须指定数据库名称或在配置中设置默认值")

        if db_name not in config['databases']:
            raise ValueError(f"未找到数据库配置: {db_name}")

        db_config = config['databases'][db_name]
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

    def get_masked_connection_info(self) -> dict:
        """返回脱敏的连接信息，用于日志输出"""
        return {
            'dbname': self.dbname,
            'host': self.local_host or self.host,
            'port': self.port
            # 完全移除 user 和 password
        }
