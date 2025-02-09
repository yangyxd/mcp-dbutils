"""PostgreSQL configuration module"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal
from ..config import DatabaseConfig

@dataclass
class PostgresConfig(DatabaseConfig):
    dbname: str
    user: str
    password: str
    host: str = 'localhost'
    port: str = '5432'
    local_host: Optional[str] = None
    type: Literal['postgres'] = 'postgres'

    @classmethod
    def from_yaml(cls, yaml_path: str, db_name: str, local_host: Optional[str] = None) -> 'PostgresConfig':
        """Create configuration from YAML file

        Args:
            yaml_path: Path to YAML configuration file
            db_name: Database configuration name to use
            local_host: Optional local host address
        """
        configs = cls.load_yaml_config(yaml_path)
        if not db_name:
            raise ValueError("Database name must be specified")
        if db_name not in configs:
            available_dbs = list(configs.keys())
            raise ValueError(f"Database configuration not found: {db_name}. Available configurations: {available_dbs}")

        db_config = configs[db_name]
        if 'type' not in db_config:
            raise ValueError("Database configuration must include 'type' field")
        if db_config['type'] != 'postgres':
            raise ValueError(f"Configuration is not PostgreSQL type: {db_config['type']}")

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
        """Get psycopg2 connection parameters"""
        params = {
            'dbname': self.dbname,
            'user': self.user,
            'password': self.password,
            'host': self.local_host or self.host,
            'port': self.port
        }
        return {k: v for k, v in params.items() if v}

    def get_masked_connection_info(self) -> Dict[str, Any]:
        """Return masked connection information for logging"""
        return {
            'dbname': self.dbname,
            'host': self.local_host or self.host,
            'port': self.port
        }
