import asyncio
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from mcp.server import Server
import mcp.types as types
from mcp.server.stdio import stdio_server

from .config import PostgresConfig

class PostgresServer:
    def __init__(self, config: PostgresConfig):
        self.config = config
        self.pool = SimpleConnectionPool(1, 5, **config.get_connection_params())
        self.server = Server("postgres-server")
        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            """列出所有表及其模式信息"""
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                    )
                    tables = cur.fetchall()
                    return [
                        types.Resource(
                            uri=f"postgres://{self.config.host}/{table[0]}/schema",
                            name=f"{table[0]} schema",
                            mimeType="application/json"
                        ) for table in tables
                    ]
            finally:
                self.pool.putconn(conn)

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """读取表模式信息"""
            table_name = uri.split('/')[-2]  # 获取表名
            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT column_name, data_type, is_nullable 
                        FROM information_schema.columns 
                        WHERE table_name = %s
                        """,
                        (table_name,)
                    )
                    columns = cur.fetchall()
                    return str([{
                        'column': col[0],
                        'type': col[1],
                        'nullable': col[2]
                    } for col in columns])
            finally:
                self.pool.putconn(conn)

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """列出可用工具"""
            return [
                types.Tool(
                    name="query",
                    description="执行只读SQL查询",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string"}
                        },
                        "required": ["sql"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """处理工具调用"""
            if name != "query":
                raise ValueError(f"Unknown tool: {name}")
            
            sql = arguments.get("sql")
            if not sql:
                raise ValueError("SQL query is required")

            conn = self.pool.getconn()
            try:
                with conn.cursor() as cur:
                    # 启动只读事务
                    cur.execute("BEGIN TRANSACTION READ ONLY")
                    try:
                        cur.execute(sql)
                        results = cur.fetchall()
                        # 获取列名
                        columns = [desc[0] for desc in cur.description]
                        # 格式化结果
                        formatted_results = [dict(zip(columns, row)) for row in results]
                        return [types.TextContent(
                            type="text",
                            text=str(formatted_results)
                        )]
                    finally:
                        cur.execute("ROLLBACK")
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"Error executing query: {str(e)}"
                )]
            finally:
                self.pool.putconn(conn)

    async def run(self):
        """运行服务器"""
        async with stdio_server() as streams:
            await self.server.run(
                streams[0],
                streams[1],
                self.server.create_initialization_options()
            )

    def cleanup(self):
        """清理资源"""
        if self.pool:
            self.pool.closeall()

async def main():
    """主入口函数"""
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m postgres.server <database_url> [local_host]")
        sys.exit(1)

    database_url = sys.argv[1]
    local_host = sys.argv[2] if len(sys.argv) > 2 else None
    
    config = PostgresConfig.from_url(database_url, local_host)
    server = PostgresServer(config)
    
    try:
        await server.run()
    finally:
        server.cleanup()

if __name__ == "__main__":
    asyncio.run(main())