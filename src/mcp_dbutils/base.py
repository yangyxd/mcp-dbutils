"""Database server base class"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, AsyncContextManager
from contextlib import asynccontextmanager
import yaml
from mcp.server import Server, NotificationOptions
import mcp.server.stdio
import mcp.types as types
from .log import create_logger

class DatabaseHandler(ABC):
    """抽象基类,定义数据库处理器通用接口"""

    def __init__(self, config_path: str, database: str, debug: bool = False):
        """初始化数据库处理器

        Args:
            config_path: 配置文件路径
            database: 数据库配置名称
            debug: 是否开启调试模式
        """
        self.config_path = config_path
        self.database = database
        self.debug = debug
        self.log = create_logger(f"db-handler-{database}", debug)

    @abstractmethod
    async def get_tables(self) -> list[types.Resource]:
        """获取数据库中的表资源列表"""
        pass

    @abstractmethod
    async def get_schema(self, table_name: str) -> str:
        """获取指定表的结构信息"""
        pass

    @abstractmethod
    async def execute_query(self, sql: str) -> str:
        """执行SQL查询"""
        pass

    @abstractmethod
    async def cleanup(self):
        """清理资源"""
        pass

class DatabaseServer:
    """统一的数据库服务器类"""

    def __init__(self, config_path: str, debug: bool = False):
        """初始化数据库服务器

        Args:
            config_path: 配置文件路径
            debug: 是否开启调试模式
        """
        self.config_path = config_path
        self.debug = debug
        self.log = create_logger("db-server", debug)
        self.server = Server("database-server")
        self._setup_handlers()

    @asynccontextmanager
    async def get_handler(self, database: str) -> AsyncContextManager[DatabaseHandler]:
        """获取数据库处理器

        根据配置名称获取相应类型的数据库处理器

        Args:
            database: 数据库配置名称

        Returns:
            AsyncContextManager[DatabaseHandler]: 数据库处理器的上下文管理器
        """
        # 读取配置文件确定数据库类型
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            if not config or 'databases' not in config:
                raise ValueError("配置文件必须包含 databases 配置")
            if database not in config['databases']:
                available_dbs = list(config['databases'].keys())
                raise ValueError(f"未找到数据库配置: {database}。可用的数据库配置: {available_dbs}")

            db_config = config['databases'][database]

            handler = None
            try:
                # 根据配置确定数据库类型并创建相应的处理器
                if 'db_path' in db_config:
                    from .sqlite.handler import SqliteHandler
                    handler = SqliteHandler(self.config_path, database, self.debug)
                elif 'dbname' in db_config or 'host' in db_config:
                    from .postgres.handler import PostgresHandler
                    handler = PostgresHandler(self.config_path, database, self.debug)
                else:
                    raise ValueError(f"无法确定数据库类型，配置中缺少必要参数")

                yield handler
            finally:
                if handler:
                    await handler.cleanup()

    def _setup_handlers(self):
        """设置 MCP 处理器"""
        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            # 读取默认配置
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                if not config or 'databases' not in config:
                    return []
                default_db = next(iter(config['databases'].keys()))

            # 使用默认数据库获取资源列表
            async with self.get_handler(default_db) as handler:
                return await handler.get_tables()

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            # 解析 URI 获取数据库名称和表名
            parts = uri.split('/')
            if len(parts) < 3:
                raise ValueError("无效的资源 URI")

            # 默认使用第一个配置
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                if not config or 'databases' not in config:
                    raise ValueError("无效的配置文件")
                default_db = next(iter(config['databases'].keys()))

            table_name = parts[-2]  # URI 格式: xxx/table_name/schema
            async with self.get_handler(default_db) as handler:
                return await handler.get_schema(table_name)

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="query",
                    description="执行只读SQL查询",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "database": {
                                "type": "string",
                                "description": "数据库配置名称"
                            },
                            "sql": {
                                "type": "string",
                                "description": "SQL查询语句（仅支持SELECT）"
                            }
                        },
                        "required": ["database", "sql"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            if name != "query":
                raise ValueError(f"未知工具: {name}")

            if "database" not in arguments:
                raise ValueError("必须指定数据库配置名称")

            sql = arguments.get("sql", "").strip()
            if not sql:
                raise ValueError("SQL查询不能为空")

            # 仅允许SELECT语句
            if not sql.lower().startswith("select"):
                raise ValueError("仅支持SELECT查询")

            database = arguments["database"]
            async with self.get_handler(database) as handler:
                result = await handler.execute_query(sql)
                return [types.TextContent(type="text", text=result)]

    async def run(self):
        """运行服务器"""
        async with mcp.server.stdio.stdio_server() as streams:
            await self.server.run(
                streams[0],
                streams[1],
                self.server.create_initialization_options()
            )
