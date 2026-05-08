"""Tests for the easycord.testing helpers."""
from __future__ import annotations

from easycord import Bot, Plugin, slash
from easycord.testing import FakeContext, invoke


def test_fake_context_captures_responses() -> None:
    ctx = FakeContext.make(user_id=42, guild_id=None)
    assert ctx.user.id == 42
    assert ctx.guild is None
    assert ctx.responses == []

    guild_ctx = FakeContext.make(guild_id=123)
    assert guild_ctx.guild is not None
    assert guild_ctx.guild.id == 123


async def test_fake_context_assertions() -> None:
    ctx = FakeContext.make()
    await ctx.respond("hello", ephemeral=True)
    ctx.assert_content("hello")
    ctx.assert_contains("ell")
    assert ctx.was_ephemeral is True
    assert ctx.response_count == 1


async def test_invoke_runs_registered_bot_command() -> None:
    bot = Bot(auto_sync=False, db_backend="memory")
    try:
        @bot.slash(description="Ping")
        async def ping(ctx):
            await ctx.respond("Pong!")

        ctx = await invoke(bot, "ping")
        assert ctx.last_response == "Pong!"
    finally:
        await bot.close()


async def test_invoke_runs_registered_plugin_command() -> None:
    class MathPlugin(Plugin):
        @slash(description="Add")
        async def add(self, ctx, a: int, b: int):
            await ctx.respond(str(a + b))

    bot = Bot(auto_sync=False, db_backend="memory")
    try:
        bot.add_plugin(MathPlugin())
        ctx = await invoke(bot, "add", a=2, b=5)
        assert ctx.last_response == "7"
    finally:
        await bot.close()
