"""Resource monitoring statistics module"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import sys

@dataclass
class ResourceStats:
    """Resource statistics tracking"""
    # Connection stats
    active_connections: int = 0
    total_connections: int = 0
    connection_start_time: Optional[datetime] = None

    # Query stats
    query_count: int = 0
    last_query_time: Optional[datetime] = None

    # Error stats
    error_count: int = 0
    last_error_time: Optional[datetime] = None
    error_types: dict[str, int] = None

    # Resource stats
    estimated_memory: int = 0

    def __post_init__(self):
        """Initialize mutable defaults"""
        if self.error_types is None:
            self.error_types = {}

    def record_connection_start(self):
        """Record new connection start"""
        self.active_connections += 1
        self.total_connections += 1
        self.connection_start_time = datetime.now()

    def record_connection_end(self):
        """Record connection end"""
        self.active_connections = max(0, self.active_connections - 1)

    def record_query(self):
        """Record query execution"""
        self.query_count += 1
        self.last_query_time = datetime.now()

    def record_error(self, error_type: str):
        """Record error occurrence

        Args:
            error_type: Type/class name of the error
        """
        self.error_count += 1
        self.last_error_time = datetime.now()
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1

    def update_memory_usage(self, obj: object):
        """Update estimated memory usage

        Args:
            obj: Object to estimate size for
        """
        self.estimated_memory = sys.getsizeof(obj)

    def to_dict(self) -> dict:
        """Convert stats to dictionary for logging

        Returns:
            Dictionary of current statistics
        """
        now = datetime.now()
        connection_duration = None
        if self.connection_start_time:
            connection_duration = (now - self.connection_start_time).total_seconds()

        return {
            "active_connections": self.active_connections,
            "total_connections": self.total_connections,
            "connection_duration": connection_duration,
            "query_count": self.query_count,
            "error_count": self.error_count,
            "error_types": self.error_types,
            "estimated_memory_bytes": self.estimated_memory
        }
