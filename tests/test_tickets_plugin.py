"""Tests for easycord.plugins.tickets — TicketPlugin."""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from easycord.plugins.tickets import TicketPlugin


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def plugin(tmp_path):
    return TicketPlugin(data_dir=str(tmp_path / "tickets"))


def _make_guild(guild_id: int = 1) -> MagicMock:
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = "Test Server"
    guild.default_role = MagicMock()
    guild.get_role = MagicMock(return_value=None)
    guild.get_channel = MagicMock(return_value=None)
    guild.create_text_channel = AsyncMock()
    return guild


def _make_member(user_id: int = 42, manage_channels: bool = False) -> MagicMock:
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.name = f"user{user_id}"
    member.mention = f"<@{user_id}>"
    member.roles = []
    member.guild_permissions = MagicMock()
    member.guild_permissions.manage_channels = manage_channels
    return member


def _make_ctx(
    guild_id: int = 1,
    user_id: int = 42,
    channel_topic: str | None = None,
    has_manage_channels: bool = False,
) -> MagicMock:
    ctx = MagicMock()
    ctx.respond = AsyncMock()
    ctx.guild = _make_guild(guild_id)
    ctx.user = MagicMock()
    ctx.user.id = user_id
    ctx.user.name = f"user{user_id}"
    ctx.user.mention = f"<@{user_id}>"
    ctx.member = _make_member(user_id, has_manage_channels)
    if channel_topic is not None:
        ctx.channel = MagicMock(spec=discord.TextChannel)
        ctx.channel.topic = channel_topic
        ctx.channel.delete = AsyncMock()
        ctx.channel.send = AsyncMock()
        ctx.channel.set_permissions = AsyncMock()
    else:
        ctx.channel = None
    return ctx


# ── Config helpers ────────────────────────────────────────────────────────────

def test_read_config_returns_defaults_for_new_guild(plugin):
    cfg = plugin._read_config(99)
    assert cfg == {"category_id": None, "support_role_id": None, "ticket_count": 0}


def test_update_config_persists(plugin):
    plugin._update_config(1, category_id=555)
    assert plugin._read_config(1)["category_id"] == 555


def test_update_config_merges(plugin):
    plugin._update_config(1, category_id=1)
    plugin._update_config(1, support_role_id=2)
    cfg = plugin._read_config(1)
    assert cfg["category_id"] == 1
    assert cfg["support_role_id"] == 2


def test_update_config_increments_ticket_count(plugin):
    plugin._update_config(1, ticket_count=5)
    assert plugin._read_config(1)["ticket_count"] == 5


# ── _is_ticket_channel ────────────────────────────────────────────────────────

def test_is_ticket_channel_true_for_valid_topic(plugin):
    channel = MagicMock()
    channel.topic = "Ticket #1 | opener:42"
    assert plugin._is_ticket_channel(channel) is True


def test_is_ticket_channel_false_for_none_topic(plugin):
    channel = MagicMock()
    channel.topic = None
    assert plugin._is_ticket_channel(channel) is False


def test_is_ticket_channel_false_for_other_topic(plugin):
    channel = MagicMock()
    channel.topic = "General chat"
    assert plugin._is_ticket_channel(channel) is False


# ── _parse_opener_id ──────────────────────────────────────────────────────────

def test_parse_opener_id_returns_user_id(plugin):
    channel = MagicMock()
    channel.topic = "Ticket #3 | opener:99"
    assert plugin._parse_opener_id(channel) == 99


def test_parse_opener_id_returns_none_for_invalid(plugin):
    channel = MagicMock()
    channel.topic = "not a ticket"
    assert plugin._parse_opener_id(channel) is None


# ── open_ticket ───────────────────────────────────────────────────────────────

async def test_open_ticket_fails_in_dm(plugin):
    ctx = _make_ctx()
    ctx.guild = None
    await plugin.open_ticket(ctx)
    ctx.respond.assert_called_once()
    assert ctx.respond.call_args.kwargs.get("ephemeral") is True


async def test_open_ticket_creates_channel(plugin):
    ctx = _make_ctx()
    new_channel = MagicMock(spec=discord.TextChannel)
    new_channel.send = AsyncMock()
    ctx.guild.create_text_channel = AsyncMock(return_value=new_channel)
    await plugin.open_ticket(ctx)
    ctx.guild.create_text_channel.assert_called_once()
    name = ctx.guild.create_text_channel.call_args[0][0]
    assert "ticket-" in name


async def test_open_ticket_increments_ticket_count(plugin):
    ctx = _make_ctx()
    new_channel = MagicMock(spec=discord.TextChannel)
    new_channel.send = AsyncMock()
    ctx.guild.create_text_channel = AsyncMock(return_value=new_channel)
    await plugin.open_ticket(ctx)
    await plugin.open_ticket(ctx)
    assert plugin._read_config(1)["ticket_count"] == 2


async def test_open_ticket_posts_opening_embed(plugin):
    ctx = _make_ctx()
    new_channel = MagicMock(spec=discord.TextChannel)
    new_channel.send = AsyncMock()
    ctx.guild.create_text_channel = AsyncMock(return_value=new_channel)
    await plugin.open_ticket(ctx, reason="Need help")
    new_channel.send.assert_called_once()
    embed = new_channel.send.call_args.kwargs["embed"]
    assert embed is not None


async def test_open_ticket_sets_channel_in_category(plugin):
    ctx = _make_ctx()
    plugin._update_config(1, category_id=777)
    category = MagicMock(spec=discord.CategoryChannel)
    ctx.guild.get_channel = MagicMock(return_value=category)
    new_channel = MagicMock(spec=discord.TextChannel)
    new_channel.send = AsyncMock()
    ctx.guild.create_text_channel = AsyncMock(return_value=new_channel)
    await plugin.open_ticket(ctx)
    call_kwargs = ctx.guild.create_text_channel.call_args[1]
    assert call_kwargs.get("category") == category


# ── close_ticket ──────────────────────────────────────────────────────────────

async def test_close_ticket_fails_outside_ticket_channel(plugin):
    ctx = _make_ctx(channel_topic="General chat")
    await plugin.close_ticket(ctx)
    ctx.respond.assert_called_once()
    assert "not a ticket" in ctx.respond.call_args[0][0].lower()


async def test_close_ticket_fails_when_not_opener_and_no_manage_channels(plugin):
    ctx = _make_ctx(channel_topic="Ticket #1 | opener:99", user_id=42)
    await plugin.close_ticket(ctx)
    ctx.respond.assert_called_once()
    assert ctx.respond.call_args.kwargs.get("ephemeral") is True
    ctx.channel.delete.assert_not_called()


async def test_close_ticket_succeeds_for_opener(plugin):
    ctx = _make_ctx(channel_topic="Ticket #1 | opener:42", user_id=42)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await plugin.close_ticket(ctx)
    ctx.channel.send.assert_called_once()
    ctx.channel.delete.assert_called_once()


async def test_close_ticket_succeeds_for_manage_channels(plugin):
    ctx = _make_ctx(
        channel_topic="Ticket #1 | opener:99",
        user_id=1,
        has_manage_channels=True,
    )
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await plugin.close_ticket(ctx)
    ctx.channel.send.assert_called_once()
    ctx.channel.delete.assert_called_once()


# ── add_to_ticket / remove_from_ticket ───────────────────────────────────────

async def test_add_to_ticket_fails_outside_ticket(plugin):
    ctx = _make_ctx(channel_topic="not a ticket")
    member = _make_member(55)
    await plugin.add_to_ticket(ctx, member)
    ctx.respond.assert_called_once()
    assert "not a ticket" in ctx.respond.call_args[0][0].lower()


async def test_add_to_ticket_fails_without_permission(plugin):
    ctx = _make_ctx(channel_topic="Ticket #1 | opener:42", has_manage_channels=False)
    member = _make_member(55)
    await plugin.add_to_ticket(ctx, member)
    ctx.respond.assert_called_once()
    assert ctx.respond.call_args.kwargs.get("ephemeral") is True
    ctx.channel.set_permissions.assert_not_called()


async def test_add_to_ticket_succeeds_with_manage_channels(plugin):
    ctx = _make_ctx(channel_topic="Ticket #1 | opener:42", has_manage_channels=True)
    member = _make_member(55)
    await plugin.add_to_ticket(ctx, member)
    ctx.channel.set_permissions.assert_called_once_with(
        member, view_channel=True, send_messages=True
    )
    ctx.respond.assert_called_once()
    assert ctx.respond.call_args.kwargs.get("ephemeral") is True


async def test_remove_from_ticket_succeeds_with_manage_channels(plugin):
    ctx = _make_ctx(channel_topic="Ticket #1 | opener:42", has_manage_channels=True)
    member = _make_member(55)
    await plugin.remove_from_ticket(ctx, member)
    ctx.channel.set_permissions.assert_called_once_with(
        member, view_channel=False, send_messages=False
    )


# ── set_ticket_category / set_support_role / ticket_config ───────────────────

async def test_set_ticket_category_saves_id(plugin):
    ctx = _make_ctx()
    category = MagicMock(spec=discord.CategoryChannel)
    category.id = 777
    category.mention = "<#777>"
    await plugin.set_ticket_category(ctx, category)
    assert plugin._read_config(1)["category_id"] == 777
    ctx.respond.assert_called_once()


async def test_set_support_role_saves_id(plugin):
    ctx = _make_ctx()
    role = MagicMock(spec=discord.Role)
    role.id = 888
    role.mention = "@Support"
    await plugin.set_support_role(ctx, role)
    assert plugin._read_config(1)["support_role_id"] == 888
    ctx.respond.assert_called_once()


async def test_ticket_config_shows_embed(plugin):
    ctx = _make_ctx()
    ctx.guild.get_channel = MagicMock(return_value=None)
    ctx.guild.get_role = MagicMock(return_value=None)
    await plugin.ticket_config(ctx)
    ctx.respond.assert_called_once()
    embed = ctx.respond.call_args.kwargs.get("embed")
    assert embed is not None
