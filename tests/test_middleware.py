import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from easycord.context import Context
from easycord.middleware import (
    logging_middleware,
    guild_only_middleware,
    rate_limit_middleware,
    error_handler_middleware,
)


@pytest.fixture
def interaction():
    m = MagicMock()
    m.response.send_message = AsyncMock()
    m.followup.send = AsyncMock()
    m.command.name = "test"
    m.user.id = 1
    return m


@pytest.fixture
def ctx(interaction):
    return Context(interaction)


# --- logging_middleware ---

async def test_logging_middleware_calls_next(ctx):
    next_fn = AsyncMock()
    mw = logging_middleware()
    await mw(ctx, next_fn)
    next_fn.assert_called_once()


async def test_logging_middleware_logs(ctx, caplog):
    with caplog.at_level(logging.INFO, logger="easycord"):
        mw = logging_middleware()
        await mw(ctx, AsyncMock())
    assert "test" in caplog.text


async def test_logging_middleware_custom_level(ctx, caplog):
    with caplog.at_level(logging.DEBUG, logger="easycord"):
        mw = logging_middleware(level=logging.DEBUG)
        await mw(ctx, AsyncMock())
    assert caplog.records[0].levelno == logging.DEBUG


# --- guild_only_middleware ---

async def test_guild_only_allows_guild_command(ctx, interaction):
    interaction.guild = MagicMock()
    next_fn = AsyncMock()
    mw = guild_only_middleware()
    await mw(ctx, next_fn)
    next_fn.assert_called_once()


async def test_guild_only_blocks_dm(ctx, interaction):
    interaction.guild = None
    next_fn = AsyncMock()
    mw = guild_only_middleware()
    await mw(ctx, next_fn)
    next_fn.assert_not_called()
    interaction.response.send_message.assert_called_once()
    args = interaction.response.send_message.call_args
    assert args.kwargs.get("ephemeral") is True


# --- rate_limit_middleware ---

async def test_rate_limit_allows_within_limit(interaction):
    mw = rate_limit_middleware(max_calls=3, window_seconds=10.0)
    next_fn = AsyncMock()
    for _ in range(3):
        c = Context(interaction)
        await mw(c, next_fn)
    assert next_fn.call_count == 3


async def test_rate_limit_blocks_when_exceeded(interaction):
    mw = rate_limit_middleware(max_calls=2, window_seconds=10.0)
    next_fn = AsyncMock()
    for _ in range(2):
        await mw(Context(interaction), next_fn)

    blocked = Context(interaction)
    await mw(blocked, next_fn)

    assert next_fn.call_count == 2
    interaction.response.send_message.assert_called_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "rate limit" in msg.lower()


async def test_rate_limit_independent_per_user(interaction):
    mw = rate_limit_middleware(max_calls=1, window_seconds=10.0)

    user_a = MagicMock()
    user_a.id = 10
    user_b = MagicMock()
    user_b.id = 20

    next_fn = AsyncMock()
    interaction.user = user_a
    await mw(Context(interaction), next_fn)

    interaction.user = user_b
    await mw(Context(interaction), next_fn)

    assert next_fn.call_count == 2


# --- error_handler_middleware ---

async def test_error_handler_passes_through_on_success(ctx):
    next_fn = AsyncMock()
    mw = error_handler_middleware()
    await mw(ctx, next_fn)
    next_fn.assert_called_once()


async def test_error_handler_catches_exception(ctx, interaction):
    async def boom():
        raise ValueError("kaboom")

    mw = error_handler_middleware()
    await mw(ctx, boom)
    interaction.response.send_message.assert_called_once()
    msg = interaction.response.send_message.call_args[0][0]
    assert "wrong" in msg.lower() or "error" in msg.lower()


async def test_error_handler_logs_exception(ctx, caplog):
    async def boom():
        raise RuntimeError("oops")

    with caplog.at_level(logging.ERROR, logger="easycord"):
        mw = error_handler_middleware()
        await mw(ctx, boom)
    assert "oops" in caplog.text


async def test_error_handler_custom_message(ctx, interaction):
    async def boom():
        raise ValueError("x")

    mw = error_handler_middleware(message="Custom error.")
    await mw(ctx, boom)
    msg = interaction.response.send_message.call_args[0][0]
    assert msg == "Custom error."


async def test_error_handler_survives_failed_response(ctx, interaction):
    async def boom():
        raise ValueError("x")

    interaction.response.send_message.side_effect = RuntimeError("send failed")
    mw = error_handler_middleware()
    # Should not raise even if sending the error reply itself fails
    await mw(ctx, boom)
