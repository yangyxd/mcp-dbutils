"""MCP Database Utilities Service"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
import yaml

from .log import create_logger
# 创建全局logger
log = create_logger("mcp-dbutils")

def get_database_type(yaml_path: str, db_name: str) -> str:
    """从配置文件中获取数据库类型"""
    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
            if not config or 'databases' not in config:
                raise ValueError("配置文件必须包含 databases 配置")
            if db_name not in config['databases']:
                available_dbs = list(config['databases'].keys())
                raise ValueError(f"未找到数据库配置: {db_name}。可用的数据库配置: {available_dbs}")

            db_config = config['databases'][db_name]

            # 如果存在 db_path，认为是 SQLite
            if 'db_path' in db_config:
                return 'sqlite'
            # 如果存在 dbname 或 host，认为是 PostgreSQL
            elif 'dbname' in db_config or 'host' in db_config:
                return 'postgres'
            else:
                raise ValueError(f"无法确定数据库类型，配置中缺少必要参数")
    except Exception as e:
        raise ValueError(f"读取配置文件失败: {str(e)}")

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

async def check_database_connection(db_name: str, yaml_path: str, local_host: str = None, debug: bool = False):
    """检查数据库连接状态

    Args:
        db_name: 数据库配置名称
        yaml_path: 配置文件路径
        local_host: 本地主机地址

    Returns:
        tuple: (是否连接成功, 错误信息)
    """
    try:
        db_type = get_database_type(yaml_path, db_name)
        server_kwargs = {}

        if db_type == 'postgres':
            from .postgres.config import PostgresConfig
            config = PostgresConfig.from_yaml(yaml_path, db_name, local_host)
            server_kwargs['config'] = config
            server_kwargs['config_path'] = yaml_path
        else:  # sqlite
            from .sqlite.config import SqliteConfig
            config = SqliteConfig.from_yaml(yaml_path, db_name)
            server_kwargs['config'] = config

        server = get_database_server(db_type, **server_kwargs)
        return True, None
    except Exception as e:
        return False, str(e)

async def run_server():
    """服务器运行逻辑"""
    parser = argparse.ArgumentParser(description='MCP Database Server')
    parser.add_argument('--config', required=True, help='YAML配置文件路径')
    parser.add_argument('--local-host', help='本地主机地址')

    # 获取重试间隔，默认1800秒(30分钟)
    retry_interval = int(os.getenv('MCP_DB_RETRY_INTERVAL', '1800'))

    args = parser.parse_args()

    # 检查是否开启debug模式
    debug = os.getenv('MCP_DEBUG', '').lower() in ('1', 'true', 'yes')

    # 更新logger的debug状态
    global log
    log = create_logger("mcp-dbutils", debug)

    if debug:
        log("debug", "Debug模式已开启")

    # 读取配置文件中的所有数据库
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
        if not config or 'databases' not in config:
            log("error", "配置文件必须包含 databases 配置")
            sys.exit(1)

        databases = config['databases'].keys()

    # 初始连接检查
    connection_status = {}
    for db_name in databases:
        success, error = await check_database_connection(db_name, args.config, args.local_host, debug)
        connection_status[db_name] = success
        status_msg = "成功" if success else f"失败: {error}"
        log("info", f"数据库 {db_name} 连接检测: {status_msg}")

    # 启动自动重试任务
    async def retry_connections():
        while True:
            await asyncio.sleep(retry_interval)
            for db_name in databases:
                if not connection_status[db_name]:
                    success, error = await check_database_connection(
                        db_name, args.config, args.local_host, debug
                    )
                    if success:
                        connection_status[db_name] = True
                        log("info", f"数据库 {db_name} 重新连接成功")
                    else:
                        log("error", f"数据库 {db_name} 重试失败: {error}")

    # 启动重试任务
    asyncio.create_task(retry_connections())

    try:
        # 选择第一个连接成功的数据库
        available_db = next((db for db, status in connection_status.items() if status), None)
        if not available_db:
            log("warning", "没有可用的数据库连接")
            available_db = list(databases)[0]  # 使用第一个数据库作为默认值

        # 从配置文件确定数据库类型
        db_type = get_database_type(args.config, available_db)
        log("info", f"使用数据库: {available_db} (类型: {db_type})")

        # 根据类型创建相应的配置和服务器
        server_kwargs = {}
        if db_type == 'postgres':
            from .postgres.config import PostgresConfig
            config = PostgresConfig.from_yaml(args.config, available_db, args.local_host)
            server_kwargs['config'] = config
            server_kwargs['config_path'] = args.config
        else:  # sqlite
            from .sqlite.config import SqliteConfig
            config = SqliteConfig.from_yaml(args.config, available_db)
            server_kwargs['config'] = config

        server = get_database_server(db_type, **server_kwargs)
        await server.run()

    except KeyboardInterrupt:
        log("info", "服务器已停止")
    except Exception as e:
        log("error", str(e))
        sys.exit(1)

def main():
    """命令行入口函数"""
    asyncio.run(run_server())

__all__ = ['main']
