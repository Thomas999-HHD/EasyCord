"""Tests for easycord.plugins.welcome — WelcomePlugin."""
import json
import discord
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from easycord.plugins.welcome import WelcomePlugin


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def plugin(tmp_path):
    return WelcomePlugin(data_dir=str(tmp_path / "welcome"))


def _make_guild(guild_id: int = 1) -> MagicMock:
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = "Test Server"
    guild.member_count = 10
    return guild


def _make_member(user_id: int = 42, guild_id: int = 1) -> MagicMock:
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.name = f"User{user_id}"
    member.mention = f"<@{user_id}>"
    member.display_avatar = MagicMock()
    member.display_avatar.url = "https://example.com/avatar.png"
    member.add_roles = AsyncMock()
    guild = _make_guild(guild_id)
    guild.get_channel = MagicMock(return_value=None)
    guild.get_role = MagicMock(return_value=None)
    member.guild = guild
    return member


def _make_ctx(guild_id: int = 1, user_id: int = 1) -> MagicMock:
    ctx = MagicMock()
    ctx.respond = AsyncMock()
    ctx.guild = _make_guild(guild_id)
    ctx.user = MagicMock()
    ctx.user.id = user_id
    ctx.user.mention = f"<@{user_id}>"
    ctx.user.bot = False
    return ctx


# ── Config helpers ────────────────────────────────────────────────────────────

def test_read_config_returns_empty_for_new_guild(plugin):
    assert plugin._read_config(99) == {}


def test_update_writes_config(plugin, tmp_path):
    plugin._update(1, welcome_channel=555)
    cfg = plugin._read_config(1)
    assert cfg["welcome_channel"] == 555


def test_update_merges_with_existing(plugin):
    plugin._update(1, welcome_channel=1)
    plugin._update(1, auto_role=2)
    cfg = plugin._read_config(1)
    assert cfg["welcome_channel"] == 1
    assert cfg["auto_role"] == 2


# ── on_member_join ────────────────────────────────────────────────────────────

async def test_member_join_no_config_does_nothing(plugin):
    member = _make_member()
    await plugin._on_member_join(member)
    member.add_roles.assert_not_called()


async def test_member_join_assigns_auto_role(plugin):
    role = MagicMock(spec=discord.Role)
    member = _make_member()
    member.guild.get_role = MagicMock(return_value=role)
    plugin._update(1, auto_role=999)
    await plugin._on_member_join(member)
    member.add_roles.assert_called_once_with(role, reason="WelcomePlugin auto-role")


async def test_member_join_skips_missing_role(plugin):
    member = _make_member()
    member.guild.get_role = MagicMock(return_value=None)
    plugin._update(1, auto_role=999)
    await plugin._on_member_join(member)
    member.add_roles.assert_not_called()


async def test_member_join_posts_welcome_embed(plugin):
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    member = _make_member()
    member.guild.get_channel = MagicMock(return_value=channel)
    plugin._update(1, welcome_channel=123)
    await plugin._on_member_join(member)
    channel.send.assert_called_once()
    embed = channel.send.call_args.kwargs["embed"]
    assert member.mention in embed.description


async def test_member_join_uses_custom_welcome_message(plugin):
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    member = _make_member()
    member.guild.get_channel = MagicMock(return_value=channel)
    plugin._update(1, welcome_channel=123, welcome_message="Yo {user}, welcome to {server}!")
    await plugin._on_member_join(member)
    embed = channel.send.call_args.kwargs["embed"]
    assert member.mention in embed.description
    assert "Test Server" in embed.description


# ── on_member_remove ──────────────────────────────────────────────────────────

async def test_member_remove_no_config_does_nothing(plugin):
    member = _make_member()
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    member.guild.get_channel = MagicMock(return_value=channel)
    await plugin._on_member_remove(member)
    channel.send.assert_not_called()


async def test_member_remove_posts_goodbye_embed(plugin):
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    member = _make_member()
    member.guild.get_channel = MagicMock(return_value=channel)
    plugin._update(1, goodbye_channel=456)
    await plugin._on_member_remove(member)
    channel.send.assert_called_once()
    embed = channel.send.call_args.kwargs["embed"]
    assert "Test Server" in embed.description


# ── Slash commands ────────────────────────────────────────────────────────────

async def test_set_welcome_channel_saves_id(plugin):
    ctx = _make_ctx()
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 77
    channel.mention = "#welcome"
    await plugin.set_welcome_channel(ctx, channel)
    assert plugin._read_config(1)["welcome_channel"] == 77
    ctx.respond.assert_called_once()


async def test_set_welcome_channel_fails_in_dm(plugin):
    ctx = _make_ctx()
    ctx.guild = None
    channel = MagicMock(spec=discord.TextChannel)
    await plugin.set_welcome_channel(ctx, channel)
    assert ctx.respond.call_args.kwargs.get("ephemeral") is True


async def test_set_auto_role_saves_id(plugin):
    ctx = _make_ctx()
    role = MagicMock(spec=discord.Role)
    role.id = 88
    role.mention = "@Member"
    await plugin.set_auto_role(ctx, role)
    assert plugin._read_config(1)["auto_role"] == 88


async def test_set_welcome_message_saves_and_previews(plugin):
    ctx = _make_ctx()
    await plugin.set_welcome_message(ctx, "Hi {user}, welcome to {server}!")
    assert plugin._read_config(1)["welcome_message"] == "Hi {user}, welcome to {server}!"
    response = ctx.respond.call_args[1]["ephemeral"]
    assert response is True


async def test_welcome_config_shows_embed(plugin):
    ctx = _make_ctx()
    ctx.guild.get_channel = MagicMock(return_value=None)
    ctx.guild.get_role = MagicMock(return_value=None)
    await plugin.welcome_config(ctx)
    ctx.respond.assert_called_once()
    embed = ctx.respond.call_args.kwargs["embed"]
    assert embed is not None
