"""Integration tests for prompts functionality"""

import asyncio
import pytest
import tempfile
import yaml
import mcp.types as types
from mcp import ClientSession
import mcp.server.stdio
from mcp_dbutils.base import DatabaseServer

@pytest.mark.asyncio
async def test_prompts_capability(sqlite_db, mcp_config):
    """Test that prompts capability is properly set"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as tmp:
        yaml.dump(mcp_config, tmp)
        tmp.flush()
        server = DatabaseServer(config_path=tmp.name)

        # Get initialization options and verify prompts capability
        init_options = server.server.create_initialization_options()
        assert init_options.capabilities is not None
        assert init_options.capabilities.prompts is not None

@pytest.mark.asyncio
async def test_list_prompts(sqlite_db, mcp_config):
    """Test that list_prompts returns an empty list"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as tmp:
        yaml.dump(mcp_config, tmp)
        tmp.flush()
        server = DatabaseServer(config_path=tmp.name)

        # Test prompts list through server handler
        result = await server.server.list_prompts()()

        # Verify empty list is returned
        assert isinstance(result, list)
        assert len(result) == 0
