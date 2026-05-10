"""Tests for the easycord.testing helpers."""
from __future__ import annotations

from easycord import Bot, Plugin, message_command, slash, user_command
from easycord.testing import (
    FakeContext,
    invoke,
    invoke_component,
    invoke_message_command,
    invoke_modal,
    invoke_user_command,
)


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


async def test_invoke_component_and_modal_helpers() -> None:
    bot = Bot(auto_sync=False, db_backend="memory")
    try:
        @bot.component("confirm:{item_id:int}")
        async def confirm(ctx, item_id: int):
            await ctx.respond(str(item_id))

        @bot.modal("feedback")
        async def feedback(ctx, data):
            await ctx.respond(data["message"])

        component_ctx = await invoke_component(bot, "confirm:7")
        modal_ctx = await invoke_modal(bot, "feedback", message="great")

        assert component_ctx.last_response == "7"
        assert modal_ctx.last_response == "great"
    finally:
        await bot.close()


async def test_invoke_context_menu_helpers() -> None:
    bot = Bot(auto_sync=False, db_backend="memory")
    seen: list[object] = []
    try:
        @bot.user_command(name="Profile")
        async def profile(ctx, member):
            seen.append(member.display_name)
            await ctx.respond(f"profile {member.id}")

        @bot.message_command(name="Quote")
        async def quote(ctx, message):
            seen.append(message.content)
            await ctx.respond(message.content)

        user_ctx = await invoke_user_command(bot, "Profile", target_id=99)
        message_ctx = await invoke_message_command(bot, "Quote", content="ship it")

        assert user_ctx.last_response == "profile 99"
        assert message_ctx.last_response == "ship it"
        assert seen == ["Target 99", "ship it"]
    finally:
        await bot.close()


async def test_invoke_context_menu_helpers_run_plugin_commands() -> None:
    class MenuPlugin(Plugin):
        @user_command(name="Inspect User")
        async def inspect_user(self, ctx, member):
            await ctx.respond(member.display_name)

        @message_command(name="Inspect Message")
        async def inspect_message(self, ctx, message):
            await ctx.respond(message.content.upper())

    bot = Bot(auto_sync=False, db_backend="memory")
    try:
        bot.add_plugin(MenuPlugin())

        user_ctx = await invoke_user_command(bot, "Inspect User", target_id=7)
        message_ctx = await invoke_message_command(
            bot,
            "Inspect Message",
            content="hello",
        )

        assert user_ctx.last_response == "Target 7"
        assert message_ctx.last_response == "HELLO"
    finally:
        await bot.close()
