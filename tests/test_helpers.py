"""Tests for helper utilities."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from easycord.helpers import ConfigHelpers, ContextHelpers, EmbedBuilder, RateLimitHelpers, ToolHelpers
from easycord.tools import ToolDef, ToolRegistry, ToolSafety
from easycord.tool_limits import RateLimit, ToolLimiter


class TestEmbedBuilder:
    """Test EmbedBuilder convenience methods."""

    def test_success_embed(self):
        """Test success embed creation."""
        embed = EmbedBuilder.success("Done", "Task completed")
        assert embed.title == "Done"
        assert embed.description == "Task completed"
        assert embed.color == discord.Color.green()

    def test_error_embed(self):
        """Test error embed creation."""
        embed = EmbedBuilder.error("Failed", "Something went wrong")
        assert embed.title == "Failed"
        assert embed.description == "Something went wrong"
        assert embed.color == discord.Color.red()

    def test_info_embed(self):
        """Test info embed creation."""
        embed = EmbedBuilder.info("Info", "Here's some info")
        assert embed.color == discord.Color.blue()

    def test_warning_embed(self):
        """Test warning embed creation."""
        embed = EmbedBuilder.warning("Warning", "Be careful")
        assert embed.color == discord.Color.orange()

    def test_fluent_builder(self):
        """Test fluent API."""
        embed = (
            EmbedBuilder("Title")
            .add_field("Field1", "Value1")
            .set_color(0xFF5733)
            .set_footer("Footer text")
            .build()
        )
        assert embed.title == "Title"
        assert len(embed.fields) == 1
        assert embed.fields[0].name == "Field1"


class TestConfigHelpers:
    """Test ConfigHelpers."""

    @pytest.mark.asyncio
    async def test_load_or_default(self):
        """Test load_or_default returns defaults when missing."""
        with patch("easycord.helpers.config.ServerConfigStore") as MockStore:
            mock_store = AsyncMock()
            mock_cfg_obj = MagicMock()
            mock_cfg_obj.get_other.return_value = None
            mock_store.load = AsyncMock(return_value=mock_cfg_obj)
            MockStore.return_value = mock_store

            defaults = {"enabled": True, "count": 5}
            result = await ConfigHelpers.load_or_default(123, ".path", defaults)

            assert result == defaults
            mock_cfg_obj.set_other.assert_called_once()
            mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_atomic(self):
        """Test atomic config updates."""
        with patch("easycord.helpers.config.ServerConfigStore") as MockStore:
            mock_store = AsyncMock()
            mock_cfg_obj = MagicMock()
            mock_cfg_obj.get_other.return_value = {"count": 3}
            mock_store.load = AsyncMock(return_value=mock_cfg_obj)
            MockStore.return_value = mock_store

            updates = {"count": 5}
            result = await ConfigHelpers.update_atomic(123, ".path", updates)

            assert result["count"] == 5
            mock_store.save.assert_called_once()


class TestContextHelpers:
    """Test ContextHelpers."""

    def test_list_members_empty_guild(self):
        """Test list_members with no guild."""
        ctx = MagicMock()
        ctx.guild = None
        result = ContextHelpers.list_members(ctx)
        assert result == []

    def test_paginate_list(self):
        """Test list pagination."""
        items = list(range(25))
        pages = ContextHelpers.paginate_list(items, per_page=10)
        assert len(pages) == 3
        assert len(pages[0]) == 10
        assert len(pages[2]) == 5

    def test_paginate_empty_list(self):
        """Test pagination with empty list."""
        pages = ContextHelpers.paginate_list([], per_page=10)
        assert pages == []


class TestToolHelpers:
    """Test ToolHelpers."""

    def test_list_all_tools(self):
        """Test listing all tools."""
        registry = ToolRegistry()

        async def dummy_func(): pass

        registry.register(
            name="tool1",
            func=dummy_func,
            description="Tool 1",
            safety=ToolSafety.SAFE
        )
        registry.register(
            name="tool2",
            func=dummy_func,
            description="Tool 2",
            safety=ToolSafety.CONTROLLED
        )

        tools = ToolHelpers.list_all_tools(registry)
        assert len(tools) == 2
        assert "tool1" in tools
        assert "tool2" in tools

    def test_get_tool_info(self):
        """Test getting tool metadata."""
        registry = ToolRegistry()

        async def dummy_func(): pass

        registry.register(
            name="test_tool",
            func=dummy_func,
            description="Test tool",
            safety=ToolSafety.CONTROLLED,
            require_admin=True
        )

        info = ToolHelpers.get_tool_info(registry, "test_tool")
        assert info is not None
        assert info["name"] == "test_tool"
        assert info["safety"] == "CONTROLLED"
        assert info["require_admin"] is True


class TestRateLimitHelpers:
    """Test RateLimitHelpers."""

    def test_create_limit(self):
        """Test creating a rate limit."""
        limit = RateLimitHelpers.create_limit("test", max_calls=5, window_minutes=60)
        assert isinstance(limit, RateLimit)
        assert limit.max_calls == 5
        assert limit.window_minutes == 60

    def test_check_under_limit(self):
        """Test checking when under limit."""
        limiter = ToolLimiter()
        limit = RateLimit(max_calls=3, window_minutes=60)
        allowed = RateLimitHelpers.check(limiter, 123, "tool", limit)
        assert allowed is True

    def test_reset_user(self):
        """Test resetting limits for user."""
        limiter = ToolLimiter()
        limit = RateLimit(max_calls=1, window_minutes=60)
        # Make a call to create a limit entry
        limiter.check_limit(123, "tool1", limit)
        limiter.check_limit(123, "tool2", limit)

        # Verify entries exist
        assert len([k for k in limiter._usage.keys() if k[0] == 123]) == 2

        # Reset user
        RateLimitHelpers.reset_user(limiter, 123)

        # Verify entries cleared
        assert len([k for k in limiter._usage.keys() if k[0] == 123]) == 0

    def test_reset_tool(self):
        """Test resetting limits for tool."""
        limiter = ToolLimiter()
        limit = RateLimit(max_calls=1, window_minutes=60)

        # Create entries for multiple users/tools
        limiter.check_limit(123, "tool1", limit)
        limiter.check_limit(456, "tool1", limit)
        limiter.check_limit(123, "tool2", limit)

        # Reset tool1
        RateLimitHelpers.reset_tool(limiter, "tool1")

        # Verify tool1 cleared but tool2 remains
        assert len([k for k in limiter._usage.keys() if k[1] == "tool1"]) == 0
        assert len([k for k in limiter._usage.keys() if k[1] == "tool2"]) == 1
