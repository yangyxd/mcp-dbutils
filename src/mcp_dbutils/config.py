"""Common configuration utilities"""

import os
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path

class DatabaseConfig(ABC):
    """数据库配置基类"""

    debug: bool = False

    @abstractmethod
    def get_connection_params(self) -> Dict[str, Any]:
        """获取连接参数"""
        pass

    @abstractmethod
    def get_masked_connection_info(self) -> Dict[str, Any]:
        """获取用于日志的脱敏连接信息"""
        pass

    @classmethod
    def load_yaml_config(cls, yaml_path: str) -> Dict[str, Any]:
        """加载YAML配置文件

        Args:
            yaml_path: YAML文件路径

        Returns:
            解析后的配置字典
        """
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if not config or 'databases' not in config:
            raise ValueError("配置文件必须包含 databases 配置")

        return config['databases']

    @classmethod
    def get_debug_mode(cls) -> bool:
        """获取调试模式状态"""
        return os.environ.get('MCP_DEBUG', '').lower() in ('1', 'true')
