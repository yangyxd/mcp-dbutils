"""Database server base class"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from mcp.server import Server, NotificationOptions
import mcp.server.stdio
import mcp.types as types

class DatabaseServer(ABC):
    """抽象基类,定义数据库服务器通用接口"""

    def __init__(self, server_name: str, debug: bool = False):
        """初始化数据库服务器

        Args:
            server_name: 服务器名称
            debug: 是否开启调试模式
        """
        self.debug = debug
        self.server = Server(server_name)
        self._setup_handlers()

    def _setup_handlers(self):
        """设置 MCP 处理器"""
        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            return await self.list_resources()

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            return await self.read_resource(uri)

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return self.get_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            return await self.call_tool(name, arguments)

    @abstractmethod
    async def list_resources(self) -> list[types.Resource]:
        """列出所有表资源"""
        pass

    @abstractmethod
    async def read_resource(self, uri: str) -> str:
        """读取表结构信息"""
        pass

    @abstractmethod
    def get_tools(self) -> list[types.Tool]:
        """获取可用工具列表"""
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict) -> list[types.TextContent]:
        """执行工具调用"""
        pass

    @abstractmethod
    async def cleanup(self):
        """清理资源"""
        pass

    async def run(self):
        """运行服务器"""
        try:
            async with mcp.server.stdio.stdio_server() as streams:
                await self.server.run(
                    streams[0],
                    streams[1],
                    self.server.create_initialization_options()
                )
        finally:
            await self.cleanup()
