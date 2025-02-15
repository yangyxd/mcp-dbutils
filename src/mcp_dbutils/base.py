"""Database server base class"""

class DatabaseError(Exception):
    """Base exception for database errors"""
    pass

class ConfigurationError(DatabaseError):
    """Configuration related errors"""
    pass

class ConnectionError(DatabaseError):
    """Connection related errors"""
    pass

from abc import ABC, abstractmethod
from typing import Any, List, Optional, AsyncContextManager
from contextlib import asynccontextmanager
import yaml
from mcp.server import Server, NotificationOptions
import mcp.server.stdio
import mcp.types as types
from .log import create_logger

class DatabaseHandler(ABC):
    """Abstract base class defining common interface for database handlers"""

    def __init__(self, config_path: str, database: str, debug: bool = False):
        """Initialize database handler

        Args:
            config_path: Path to configuration file
            database: Database configuration name
            debug: Enable debug mode
        """
        self.config_path = config_path
        self.database = database
        self.debug = debug
        self.log = create_logger(f"db-handler-{database}", debug)

    @abstractmethod
    async def get_tables(self) -> list[types.Resource]:
        """Get list of table resources from database"""
        pass

    @abstractmethod
    async def get_schema(self, table_name: str) -> str:
        """Get schema information for specified table"""
        pass

    @abstractmethod
    async def execute_query(self, sql: str) -> str:
        """Execute SQL query"""
        pass

    @abstractmethod
    async def cleanup(self):
        """Cleanup resources"""
        pass

class DatabaseServer:
    """Unified database server class"""

    def __init__(self, config_path: str, debug: bool = False):
        """Initialize database server

        Args:
            config_path: Path to configuration file
            debug: Enable debug mode
        """
        self.config_path = config_path
        self.debug = debug
        self.logger = create_logger("db-server", debug)
        self.server = Server("database-server")
        self._setup_handlers()

    @asynccontextmanager
    async def get_handler(self, database: str) -> AsyncContextManager[DatabaseHandler]:
        """Get database handler

        Get appropriate database handler based on configuration name

        Args:
            database: Database configuration name

        Returns:
            AsyncContextManager[DatabaseHandler]: Context manager for database handler
        """
        # Read configuration file to determine database type
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            if not config or 'databases' not in config:
                raise ConfigurationError("Configuration file must contain 'databases' section")
            if database not in config['databases']:
                available_dbs = list(config['databases'].keys())
                raise ConfigurationError(f"Database configuration not found: {database}. Available configurations: {available_dbs}")

            db_config = config['databases'][database]

            handler = None
            try:
                if 'type' not in db_config:
                    raise ConfigurationError("Database configuration must include 'type' field")

                db_type = db_config['type']
                self.logger.debug(f"Creating handler for database type: {db_type}")
                if db_type == 'sqlite':
                    from .sqlite.handler import SqliteHandler
                    handler = SqliteHandler(self.config_path, database, self.debug)
                elif db_type == 'postgres':
                    from .postgres.handler import PostgresHandler
                    handler = PostgresHandler(self.config_path, database, self.debug)
                else:
                    raise ConfigurationError(f"Unsupported database type: {db_type}")

                self.logger.debug(f"Handler created successfully for {database}")
                yield handler
            except yaml.YAMLError as e:
                raise ConfigurationError(f"Invalid YAML configuration: {str(e)}")
            except ImportError as e:
                raise ConfigurationError(f"Failed to import handler for {db_type}: {str(e)}")
            finally:
                if handler:
                    self.logger.debug(f"Cleaning up handler for {database}")
                    await handler.cleanup()

    def _setup_handlers(self):
        """Setup MCP handlers"""
        @self.server.list_resources()
        async def handle_list_resources(arguments: dict | None = None) -> list[types.Resource]:
            if not arguments or 'database' not in arguments:
                # Return empty list when no database specified
                return []

            database = arguments['database']
            async with self.get_handler(database) as handler:
                return await handler.get_tables()

        @self.server.read_resource()
        async def handle_read_resource(uri: str, arguments: dict | None = None) -> str:
            if not arguments or 'database' not in arguments:
                raise ConfigurationError("Database configuration name must be specified")

            parts = uri.split('/')
            if len(parts) < 3:
                raise ConfigurationError("Invalid resource URI format")

            database = arguments['database']
            table_name = parts[-2]  # URI format: xxx/table_name/schema

            async with self.get_handler(database) as handler:
                return await handler.get_schema(table_name)

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="query",
                    description="Execute read-only SQL query",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "database": {
                                "type": "string",
                                "description": "Database configuration name"
                            },
                            "sql": {
                                "type": "string",
                                "description": "SQL query (SELECT only)"
                            }
                        },
                        "required": ["database", "sql"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            if name != "query":
                raise ConfigurationError(f"Unknown tool: {name}")

            if "database" not in arguments:
                raise ConfigurationError("Database configuration name must be specified")

            sql = arguments.get("sql", "").strip()
            if not sql:
                raise ConfigurationError("SQL query cannot be empty")

            # Only allow SELECT statements
            if not sql.lower().startswith("select"):
                raise ConfigurationError("Only SELECT queries are supported for security reasons")

            database = arguments["database"]
            async with self.get_handler(database) as handler:
                result = await handler.execute_query(sql)
                return [types.TextContent(type="text", text=result)]

    async def run(self):
        """Run server"""
        async with mcp.server.stdio.stdio_server() as streams:
            await self.server.run(
                streams[0],
                streams[1],
                self.server.create_initialization_options()
            )
