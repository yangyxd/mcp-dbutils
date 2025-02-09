"""Common configuration utilities"""

import os
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal
from pathlib import Path

# 支持的数据库类型
DBType = Literal['sqlite', 'postgres']

class DatabaseConfig(ABC):
    """数据库配置基类"""

    debug: bool = False
    type: DBType  # 数据库类型

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

        # 验证每个数据库配置中的type字段
        databases = config['databases']
        for db_name, db_config in databases.items():
            if 'type' not in db_config:
                raise ValueError(f"数据库配置 {db_name} 缺少必需的 type 字段")
            db_type = db_config['type']
            if db_type not in ('sqlite', 'postgres'):
                raise ValueError(f"数据库配置 {db_name} 的 type 字段值无效: {db_type}")

        return databases

    @classmethod
    def get_debug_mode(cls) -> bool:
        """获取调试模式状态"""
        return os.environ.get('MCP_DEBUG', '').lower() in ('1', 'true')
