"""日志处理模块"""

import sys
from datetime import datetime
from typing import Callable, Optional

def create_logger(name: str, is_debug: bool = False) -> Callable:
    """创建日志函数
    Args:
        name: 服务名称
        is_debug: 是否输出debug级别日志
    """
    def log(level: str, message: str, notify: Optional[Callable] = None):
        """输出日志
        Args:
            level: 日志级别 (debug/info/warning/error)
            message: 日志内容
            notify: MCP通知函数(可选)
        """
        if level == "debug" and not is_debug:
            return

        timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
        log_message = f"{timestamp} [{name}] [{level}] {message}"

        # 始终输出到stderr
        print(log_message, file=sys.stderr, flush=True)

        # 如果提供了notify函数，同时发送MCP通知
        if notify:
            notify(level=level, data=message)

    return log
