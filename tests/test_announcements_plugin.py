import pytest
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import discord

from easycord.plugins.announcements import AnnouncementsPlugin


@pytest.fixture
def plugin():
    path = Path(".plugin-test-data") / f"ann-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    plugin = AnnouncementsPlugin(data_dir=str(path))
    yield plugin
    shutil.rmtree(path, ignore_errors=True)


def _make_ctx(guild_id=1):
    ctx = MagicMock()
    ctx.respond = AsyncMock()
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = guild_id
    ctx.guild.name = "Test Server"
    ctx.bot = MagicMock()
    ctx.bot.get_channel = MagicMock(return_value=None)
    ctx.bot.fetch_channel = AsyncMock(return_value=None)
    return ctx


async def test_set_announcement_channel_saves(plugin):
    ctx = _make_ctx()
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 55
    channel.mention = "#announcements"

    await plugin.set_announcement_channel(ctx, channel)

    assert plugin._read_config(1)["announcement_channel"] == 55
    ctx.respond.assert_called_once()


async def test_announce_posts_to_configured_channel(plugin):
    ctx = _make_ctx()
    channel = MagicMock(spec=discord.TextChannel)
    channel.mention = "#announcements"
    channel.send = AsyncMock()
    ctx.bot.get_channel.return_value = channel
    plugin._update_config(1, lambda cfg: cfg.update({"announcement_channel": 55}))

    await plugin.announce(ctx, "Update", "Hello, world!")

    channel.send.assert_called_once()
    embed = channel.send.call_args.kwargs["embed"]
    assert embed.title == "Update"
    assert "Hello, world!" in embed.description


async def test_announce_falls_back_to_current_channel(plugin):
    ctx = _make_ctx()
    channel = MagicMock(spec=discord.TextChannel)
    channel.mention = "#current"
    channel.send = AsyncMock()
    ctx.channel = channel

    await plugin.announce(ctx, "Update", "Hello")

    channel.send.assert_called_once()
