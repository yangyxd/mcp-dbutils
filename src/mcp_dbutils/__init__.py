"""MCP Database Utilities Service"""

import asyncio
import argparse
import sys
from pathlib import Path

def get_database_server(db_type: str, **kwargs):
    """根据数据库类型返回相应的服务器实例"""
    if db_type == 'postgres':
        from .postgres.server import PostgresServer
        return PostgresServer(**kwargs)
    elif db_type == 'sqlite':
        from .sqlite.server import SqliteServer
        return SqliteServer(**kwargs)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

async def run_server():
    """服务器运行逻辑"""
    parser = argparse.ArgumentParser(description='MCP Database Server')
    parser.add_argument('--type', choices=['postgres', 'sqlite'], required=True,
                       help='Database type')

    # PostgreSQL specific arguments
    postgres_group = parser.add_argument_group('PostgreSQL options')
    postgres_group.add_argument('--config', required=True, help='YAML配置文件路径')
    postgres_group.add_argument('--local-host', help='本地主机地址')
    postgres_group.add_argument('--database', help='要使用的数据库配置名称')

    # SQLite specific arguments
    sqlite_group = parser.add_argument_group('SQLite options')
    sqlite_group.add_argument('--db-path', help='SQLite数据库文件路径')

    args = parser.parse_args()

    try:
        server_kwargs = {}
        if args.type == 'postgres':
            from .postgres.config import PostgresConfig
            config = PostgresConfig.from_yaml(args.config, args.database, args.local_host)
            server_kwargs['config'] = config
            server_kwargs['config_path'] = args.config
        else:  # sqlite
            if not args.db_path:
                parser.error('SQLite requires --db-path')
            server_kwargs['db_path'] = args.db_path

        server = get_database_server(args.type, **server_kwargs)
        await server.run()

    except KeyboardInterrupt:
        print("\n服务器已停止", file=sys.stderr)
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

def main():
    """命令行入口函数"""
    asyncio.run(run_server())

__all__ = ['main']