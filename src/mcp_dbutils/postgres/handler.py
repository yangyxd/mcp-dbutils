"""PostgreSQL database handler implementation"""

import psycopg2
from psycopg2.pool import SimpleConnectionPool
import mcp.types as types

from ..base import DatabaseHandler, DatabaseError
from .config import PostgresConfig

class PostgresHandler(DatabaseHandler):
    @property
    def db_type(self) -> str:
        return 'postgres'

    def __init__(self, config_path: str, database: str, debug: bool = False):
        """Initialize PostgreSQL handler

        Args:
            config_path: Path to configuration file
            database: Database configuration name
            debug: Enable debug mode
        """
        super().__init__(config_path, database, debug)
        self.config = PostgresConfig.from_yaml(config_path, database)

        # No connection pool creation during initialization
        masked_params = self.config.get_masked_connection_info()
        self.log("debug", f"Configuring database with parameters: {masked_params}")
        self.pool = None

    async def get_tables(self) -> list[types.Resource]:
        """Get all table resources"""
        try:
            conn_params = self.config.get_connection_params()
            conn = psycopg2.connect(**conn_params)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        table_name,
                        obj_description(
                            (quote_ident(table_schema) || '.' || quote_ident(table_name))::regclass,
                            'pg_class'
                        ) as description
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """)
                tables = cur.fetchall()
                return [
                    types.Resource(
                        uri=f"postgres://{self.database}/{table[0]}/schema",
                        name=f"{table[0]} schema",
                        description=table[1] if table[1] else None,
                        mimeType="application/json"
                    ) for table in tables
                ]
        except psycopg2.Error as e:
            error_msg = f"Failed to get table list: [Code: {e.pgcode}] {e.pgerror or str(e)}"
            self.stats.record_error(e.__class__.__name__)
            raise DatabaseError(error_msg)
        finally:
            if conn:
                conn.close()

    async def get_schema(self, table_name: str) -> str:
        """Get table schema information"""
        try:
            conn_params = self.config.get_connection_params()
            conn = psycopg2.connect(**conn_params)
            with conn.cursor() as cur:
                # Get column information
                cur.execute("""
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        col_description(
                            (quote_ident(table_schema) || '.' || quote_ident(table_name))::regclass,
                            ordinal_position
                        ) as description
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                columns = cur.fetchall()

                # Get constraint information
                cur.execute("""
                    SELECT
                        conname as constraint_name,
                        contype as constraint_type
                    FROM pg_constraint c
                    JOIN pg_class t ON c.conrelid = t.oid
                    WHERE t.relname = %s
                """, (table_name,))
                constraints = cur.fetchall()

                return str({
                    'columns': [{
                        'name': col[0],
                        'type': col[1],
                        'nullable': col[2] == 'YES',
                        'description': col[3]
                    } for col in columns],
                    'constraints': [{
                        'name': con[0],
                        'type': con[1]
                    } for con in constraints]
                })
        except psycopg2.Error as e:
            error_msg = f"Failed to read table schema: [Code: {e.pgcode}] {e.pgerror or str(e)}"
            self.stats.record_error(e.__class__.__name__)
            raise DatabaseError(error_msg)
        finally:
            if conn:
                conn.close()

    async def _execute_query(self, sql: str) -> str:
        """Execute SQL query"""
        conn = None
        try:
            conn_params = self.config.get_connection_params()
            conn = psycopg2.connect(**conn_params)
            self.log("debug", f"Executing query: {sql}")

            with conn.cursor() as cur:
                # Start read-only transaction
                cur.execute("BEGIN TRANSACTION READ ONLY")
                try:
                    cur.execute(sql)
                    results = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    formatted_results = [dict(zip(columns, row)) for row in results]

                    result_text = str({
                        'type': self.db_type,
                        'columns': columns,
                        'rows': formatted_results,
                        'row_count': len(results)
                    })

                    self.log("debug", f"Query completed, returned {len(results)} rows")
                    return result_text
                finally:
                    cur.execute("ROLLBACK")
        except psycopg2.Error as e:
            error_msg = f"[{self.db_type}] Query execution failed: [Code: {e.pgcode}] {e.pgerror or str(e)}"
            raise DatabaseError(error_msg)
        finally:
            if conn:
                conn.close()

    async def cleanup(self):
        """Cleanup resources"""
        # Log final stats before cleanup
        self.log("info", f"Final PostgreSQL handler stats: {self.stats.to_dict()}")
