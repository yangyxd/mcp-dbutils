"""MCP Connection Utilities Service"""

import argparse
import asyncio
import os
import sys
from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path

import yaml

from .base import LOG_NAME, ConnectionServer
from .log import create_logger

# 获取包信息
try:
    pkg_meta = metadata("mcp-dbutils")
except PackageNotFoundError:
    pkg_meta = {"Version": "dev"}

# 创建全局logger
log = create_logger(LOG_NAME)

async def run_server():
    """服务器运行逻辑"""
    parser = argparse.ArgumentParser(description='MCP Connection Server')
    parser.add_argument('--config', required=True, help='YAML配置文件路径')
    parser.add_argument('--local-host', help='本地主机地址')

    args = parser.parse_args()

    # 检查是否开启debug模式
    debug = os.getenv('MCP_DEBUG', '').lower() in ('1', 'true', 'yes')

    # 更新logger的debug状态
    global log
    log = create_logger(LOG_NAME, debug)

    log("info", f"MCP Connection Utilities Service v{pkg_meta['Version']}")
    if debug:
        log("debug", "Debug模式已开启")
        
    model = os.getenv('MCP_MODEL', '').lower()
    log("info", f"服务模式: {model}")

    # 验证配置文件
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
            if not config or 'connections' not in config:
                log("error", "配置文件必须包含 connections 配置")
                sys.exit(1)
            if not config['connections']:
                log("error", "配置文件必须包含至少一个连接配置")
                sys.exit(1)
    except Exception as e:
        log("error", f"读取配置文件失败: {str(e)}")
        sys.exit(1)

    # 创建并运行服务器
    try:
        server = ConnectionServer(args.config, debug)
        await server.run(model)
    except KeyboardInterrupt:
        log("info", "服务器已停止")
    except Exception as e:
        log("error", str(e))
        sys.exit(1)

def main():
    """命令行入口函数"""
    asyncio.run(run_server())

__all__ = ['main']

if __name__ == '__main__':
    main()