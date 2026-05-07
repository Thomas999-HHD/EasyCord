"""Tests for require_admin, @command_error, and describe() features."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import time

import discord
import pytest

from easycord.decorators import slash, command_error, describe
from easycord.context import Context


# ---------------------------------------------------------------------------
# describe() decorator
# ---------------------------------------------------------------------------

class TestDescribe:
    def test_sets_description_attribute(self):
        @describe(member="The member to kick", reason="Why")
        async def kick(ctx, member, reason=""):
            pass

        assert kick.__discord_app_commands_param_description__["member"] == "The member to kick"
        assert kick.__discord_app_commands_param_description__["reason"] == "Why"

    def test_stacks_with_slash(self):
        @slash(description="Kick a member")
        @describe(member="The member")
        async def kick(ctx, member):
            pass

        assert kick._is_slash
        assert kick.__discord_app_commands_param_description__["member"] == "The member"

    def test_multiple_calls_merge(self):
        @describe(a="desc_a")
        @describe(b="desc_b")
        async def cmd(ctx, a, b):
            pass

        assert cmd.__discord_app_commands_param_description__["a"] == "desc_a"
        assert cmd.__discord_app_commands_param_description__["b"] == "desc_b"


# ---------------------------------------------------------------------------
# command_error() decorator
# ---------------------------------------------------------------------------

class TestCommandError:
    def test_marks_handler(self):
        @command_error("divide")
        async def divide_error(self, ctx, exc):
            pass

        assert divide_error._is_command_error is True
        assert divide_error._command_error_for == "divide"

    def test_handler_registered_on_plugin(self):
        """_scan_methods should populate _command_error_handlers."""
        from easycord import Bot, Plugin
        import discord

        class MathPlugin(Plugin):
            @slash(description="Divide")
            async def divide(self, ctx, a: int, b: int):
                await ctx.respond(str(a // b))

            @command_error("divide")
            async def divide_error(self, ctx, exc):
                await ctx.respond("error", ephemeral=True)

        bot = MagicMock()
        bot._plugins = []
        bot._event_handlers = {}
        bot._command_error_handlers = {}
        bot.ai_tools = {}
        bot.tool_registry = MagicMock()
        bot.tool_registry._tools = {}
        bot.tree = MagicMock()
        bot.is_ready = MagicMock(return_value=False)

        # Patch _register_slash so we can isolate the handler scanning
        bot._register_slash = MagicMock()
        bot._register_context_menu = MagicMock()
        bot._register_component_handler = MagicMock()
        bot._register_modal_handler = MagicMock()

        from easycord._bot_plugins import _PluginsMixin
        plugin = MathPlugin()
        plugin._bot = bot
        _PluginsMixin._scan_methods(bot, plugin)

        assert "divide" in bot._command_error_handlers


# ---------------------------------------------------------------------------
# require_admin in slash decorator
# ---------------------------------------------------------------------------

class TestRequireAdmin:
    def test_slash_stores_require_admin(self):
        @slash(description="Admin cmd", require_admin=True)
        async def reset(ctx):
            pass

        assert reset._slash_require_admin is True

    def test_slash_default_require_admin_false(self):
        @slash(description="Normal cmd")
        async def ping(ctx):
            pass

        assert reset_cmd._slash_require_admin is False if False else ping._slash_require_admin is False

    @pytest.mark.asyncio
    async def test_require_admin_blocks_non_admin(self):
        """_build_slash_callback should reject members without administrator."""
        from easycord._bot_commands import _CommandsMixin

        called = []

        async def handler(ctx):
            called.append(True)

        bot = MagicMock()
        bot._middleware = []
        bot._error_handler = None
        bot._command_error_handlers = {}

        callback = _CommandsMixin._build_slash_callback(
            bot,
            handler,
            require_admin=True,
            ephemeral=False,
            guild_only=False,
            permissions=None,
            cooldown=None,
            command_name="reset",
        )

        interaction = MagicMock(spec=discord.Interaction)
        interaction.response = AsyncMock()
        interaction.response.is_done = MagicMock(return_value=False)
        interaction.followup = AsyncMock()

        guild = MagicMock()
        member = MagicMock()
        perms = MagicMock()
        perms.administrator = False
        member.guild_permissions = perms
        guild.get_member.return_value = member
        interaction.guild = guild
        interaction.user = MagicMock()
        interaction.user.id = 42
        interaction.locale = discord.Locale.american_english

        ctx = Context(interaction)
        ctx.respond = AsyncMock()

        # Patch Context construction inside the callback
        with patch("easycord._bot_commands.Context", return_value=ctx):
            with patch("easycord._bot_commands.build_chain") as mock_chain:
                # build_chain(ctx, invoke_fn, middleware) must return a callable
                mock_chain.side_effect = lambda c, invoke_fn, mw: invoke_fn
                await callback(interaction)

        assert not called
        ctx.respond.assert_called_once()
        msg = ctx.respond.call_args[0][0]
        assert "permission" in msg.lower() or "administrator" in msg.lower()

    @pytest.mark.asyncio
    async def test_require_admin_allows_admin(self):
        from easycord._bot_commands import _CommandsMixin

        called = []

        async def handler(ctx):
            called.append(True)

        bot = MagicMock()
        bot._middleware = []
        bot._error_handler = None
        bot._command_error_handlers = {}

        callback = _CommandsMixin._build_slash_callback(
            bot,
            handler,
            require_admin=True,
            ephemeral=False,
            guild_only=False,
            permissions=None,
            cooldown=None,
            command_name="reset",
        )

        interaction = MagicMock(spec=discord.Interaction)
        interaction.response = AsyncMock()
        interaction.response.is_done = MagicMock(return_value=False)
        interaction.followup = AsyncMock()

        guild = MagicMock()
        member = MagicMock()
        perms = MagicMock()
        perms.administrator = True
        member.guild_permissions = perms
        guild.get_member.return_value = member
        interaction.guild = guild
        interaction.user = MagicMock()
        interaction.user.id = 42
        interaction.locale = discord.Locale.american_english

        ctx = Context(interaction)
        ctx.respond = AsyncMock()

        with patch("easycord._bot_commands.Context", return_value=ctx):
            with patch("easycord._bot_commands.build_chain") as mock_chain:
                mock_chain.side_effect = lambda c, invoke_fn, mw: invoke_fn
                await callback(interaction)

        assert called
