"""Tests for the AI orchestrator compatibility layer."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from easycord.orchestrator import FallbackStrategy, Orchestrator, RunContext
from easycord.tools import ToolRegistry


def _make_ctx():
    ctx = MagicMock()
    ctx.user.id = 123
    ctx.guild = None
    return ctx


@pytest.mark.asyncio
async def test_orchestrator_supports_legacy_string_providers():
    """Legacy providers returning plain strings should still work."""

    async def legacy_query(prompt: str) -> str:
        assert prompt == "USER: hello world"
        return "legacy response"

    provider = MagicMock()
    provider.query = AsyncMock(side_effect=legacy_query)
    orchestrator = Orchestrator(
        strategy=FallbackStrategy([provider]),
        tools=ToolRegistry(),
    )

    result = await orchestrator.run(
        RunContext(
            messages=[{"role": "user", "content": "hello world"}],
            ctx=_make_ctx(),
        )
    )

    assert result.text == "legacy response"
    assert provider.query.await_count == 2
    first_call, second_call = provider.query.await_args_list
    assert first_call.kwargs == {"prompt": "USER: hello world", "tools": None}
    assert second_call.args == ("USER: hello world",)
    assert second_call.kwargs == {}


@pytest.mark.asyncio
async def test_orchestrator_uses_tool_aware_provider_signature_when_available():
    """Tool-aware providers should receive the richer query signature."""
    provider = MagicMock()
    provider.query = AsyncMock(return_value=SimpleNamespace(text="tool aware", tool_call=None))
    orchestrator = Orchestrator(
        strategy=FallbackStrategy([provider]),
        tools=ToolRegistry(),
    )

    result = await orchestrator.run(
        RunContext(
            messages=[{"role": "user", "content": "hello world"}],
            ctx=_make_ctx(),
        )
    )

    assert result.text == "tool aware"
    provider.query.assert_awaited_once_with(prompt="USER: hello world", tools=None)
