"""Tests for easycord.tools — ToolRegistry, permissions, execution."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from easycord.tools import ToolCall, ToolDef, ToolRegistry, ToolResult, ToolSafety


# ============================================================================
# Tool Registration
# ============================================================================


def test_register_tool():
    """Register a tool."""
    registry = ToolRegistry()

    async def dummy_tool(ctx):
        return "result"

    registry.register(
        name="test",
        func=dummy_tool,
        description="Test tool",
        safety=ToolSafety.SAFE,
    )

    assert "test" in registry._tools
    assert registry._tools["test"].name == "test"


def test_register_duplicate_raises():
    """Registering same name twice raises."""
    registry = ToolRegistry()

    async def dummy(ctx):
        pass

    registry.register("test", dummy, "Test", ToolSafety.SAFE)

    with pytest.raises(ValueError, match="already registered"):
        registry.register("test", dummy, "Test", ToolSafety.SAFE)


def test_enable_disable():
    """Enable/disable tools."""
    registry = ToolRegistry()

    async def dummy(ctx):
        pass

    registry.register("test", dummy, "Test", ToolSafety.SAFE)
    assert "test" in registry._allowlist

    registry.disable("test")
    assert "test" in registry._denylist
    assert "test" not in registry._allowlist

    registry.enable("test")
    assert "test" in registry._allowlist


# ============================================================================
# Permission Checks
# ============================================================================


def test_can_execute_unknown_tool():
    """Unknown tool returns False."""
    registry = ToolRegistry()
    ctx = MagicMock()

    allowed, reason = registry.can_execute(ctx, "unknown")
    assert not allowed
    assert "not found" in reason.lower()


def test_can_execute_disabled_tool():
    """Disabled tool returns False."""
    registry = ToolRegistry()

    async def dummy(ctx):
        pass

    registry.register("test", dummy, "Test", ToolSafety.SAFE)
    registry.disable("test")

    ctx = MagicMock()
    allowed, reason = registry.can_execute(ctx, "test")
    assert not allowed


def test_can_execute_guild_only():
    """Guild-only tool fails in DM."""
    registry = ToolRegistry()

    async def dummy(ctx):
        pass

    registry.register(
        "test",
        dummy,
        "Test",
        ToolSafety.SAFE,
        require_guild=True,
    )

    ctx = MagicMock()
    ctx.guild = None

    allowed, reason = registry.can_execute(ctx, "test")
    assert not allowed
    assert "guild" in reason.lower()


def test_can_execute_admin_only():
    """Admin-only tool fails for non-admin."""
    registry = ToolRegistry()

    async def dummy(ctx):
        pass

    registry.register(
        "test",
        dummy,
        "Test",
        ToolSafety.SAFE,
        require_admin=True,
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.is_admin = MagicMock(return_value=False)

    allowed, reason = registry.can_execute(ctx, "test")
    assert not allowed
    assert "admin" in reason.lower()


def test_can_execute_admin_passes():
    """Admin-only tool passes for admin."""
    registry = ToolRegistry()

    async def dummy(ctx):
        pass

    registry.register(
        "test",
        dummy,
        "Test",
        ToolSafety.SAFE,
        require_admin=True,
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.is_admin = MagicMock(return_value=True)

    allowed, reason = registry.can_execute(ctx, "test")
    assert allowed


def test_can_execute_role_check():
    """Role allowlist checked."""
    registry = ToolRegistry()

    async def dummy(ctx):
        pass

    ROLE_ID = 12345
    registry.register(
        "test",
        dummy,
        "Test",
        ToolSafety.SAFE,
        allowed_roles=[ROLE_ID],
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.member.roles = []

    allowed, reason = registry.can_execute(ctx, "test")
    assert not allowed
    assert "role" in reason.lower()

    # User has role
    role_mock = MagicMock()
    role_mock.id = ROLE_ID
    ctx.member.roles = [role_mock]

    allowed, reason = registry.can_execute(ctx, "test")
    assert allowed


def test_can_execute_user_check():
    """User allowlist checked."""
    registry = ToolRegistry()

    async def dummy(ctx):
        pass

    USER_ID = 99999
    registry.register(
        "test",
        dummy,
        "Test",
        ToolSafety.SAFE,
        allowed_users=[USER_ID],
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.user.id = 11111

    allowed, reason = registry.can_execute(ctx, "test")
    assert not allowed
    assert "not allowed" in reason.lower()

    ctx.user.id = USER_ID
    allowed, reason = registry.can_execute(ctx, "test")
    assert allowed


# ============================================================================
# Tool Execution
# ============================================================================


@pytest.mark.asyncio
async def test_execute_sync_tool():
    """Execute synchronous tool."""
    registry = ToolRegistry()

    def sync_tool(ctx):
        return "sync result"

    registry.register(
        "sync",
        sync_tool,
        "Sync tool",
        ToolSafety.SAFE,
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()

    result = await registry.execute(ctx, ToolCall(name="sync"))

    assert result.success
    assert "sync result" in result.output


@pytest.mark.asyncio
async def test_execute_async_tool():
    """Execute asynchronous tool."""
    registry = ToolRegistry()

    async def async_tool(ctx):
        return "async result"

    registry.register(
        "async",
        async_tool,
        "Async tool",
        ToolSafety.SAFE,
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()

    result = await registry.execute(ctx, ToolCall(name="async"))

    assert result.success
    assert "async result" in result.output


@pytest.mark.asyncio
async def test_execute_tool_with_args():
    """Execute tool with arguments."""
    registry = ToolRegistry()

    async def tool_with_args(ctx, name: str, count: int):
        return f"{name} × {count}"

    registry.register(
        "repeat",
        tool_with_args,
        "Repeat",
        ToolSafety.SAFE,
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            },
        },
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()

    result = await registry.execute(
        ctx,
        ToolCall(name="repeat", args={"name": "hello", "count": 3}),
    )

    assert result.success
    assert "hello × 3" in result.output


@pytest.mark.asyncio
async def test_execute_permission_denied():
    """Execution blocked if permission denied."""
    registry = ToolRegistry()

    async def admin_tool(ctx):
        return "admin secret"

    registry.register(
        "secret",
        admin_tool,
        "Secret",
        ToolSafety.SAFE,
        require_admin=True,
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.is_admin = MagicMock(return_value=False)

    result = await registry.execute(ctx, ToolCall(name="secret"))

    assert not result.success
    assert "admin" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_timeout():
    """Tool execution timeout."""
    import asyncio

    registry = ToolRegistry()

    async def slow_tool(ctx):
        await asyncio.sleep(10)
        return "done"

    registry.register(
        "slow",
        slow_tool,
        "Slow",
        ToolSafety.SAFE,
        timeout_ms=100,
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()

    result = await registry.execute(ctx, ToolCall(name="slow"))

    assert not result.success
    assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_exception():
    """Tool execution exception."""
    registry = ToolRegistry()

    async def broken_tool(ctx):
        raise ValueError("tool broke")

    registry.register(
        "broken",
        broken_tool,
        "Broken",
        ToolSafety.SAFE,
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()

    result = await registry.execute(ctx, ToolCall(name="broken"))

    assert not result.success
    assert "Error" in result.error


# ============================================================================
# Tool Listing & Schema
# ============================================================================


def test_list_available():
    """List tools executable by context."""
    registry = ToolRegistry()

    async def safe_tool(ctx):
        pass

    async def admin_tool(ctx):
        pass

    registry.register("safe", safe_tool, "Safe", ToolSafety.SAFE)
    registry.register(
        "admin",
        admin_tool,
        "Admin",
        ToolSafety.SAFE,
        require_admin=True,
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.is_admin = MagicMock(return_value=False)

    available = registry.list_available(ctx)
    names = {t.name for t in available}

    assert "safe" in names
    assert "admin" not in names


def test_to_provider_schema():
    """Convert to OpenAI function schema."""
    registry = ToolRegistry()

    async def tool(ctx):
        pass

    registry.register(
        "test",
        tool,
        "Test tool",
        ToolSafety.SAFE,
        parameters={
            "type": "object",
            "properties": {"arg": {"type": "string"}},
        },
    )

    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.is_admin = MagicMock(return_value=True)

    schema = registry.to_provider_schema(ctx)

    assert len(schema) == 1
    assert schema[0]["type"] == "function"
    assert schema[0]["function"]["name"] == "test"
    assert schema[0]["function"]["description"] == "Test tool"
