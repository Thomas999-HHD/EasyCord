import pytest
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import discord

from easycord.plugins.autoreply import AutoReplyPlugin


@pytest.fixture
def plugin():
    path = Path(".plugin-test-data") / f"reply-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    plugin = AutoReplyPlugin(data_dir=str(path))
    yield plugin
    shutil.rmtree(path, ignore_errors=True)


def _make_ctx(guild_id=1):
    ctx = MagicMock()
    ctx.respond = AsyncMock()
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = guild_id
    return ctx


def _make_message(content="hello there", guild_id=1):
    message = MagicMock(spec=discord.Message)
    message.content = content
    message.guild = MagicMock(spec=discord.Guild)
    message.guild.id = guild_id
    message.author = MagicMock()
    message.author.bot = False
    message.channel = MagicMock()
    message.channel.send = AsyncMock()
    return message


async def test_autoreply_add_saves_rule(plugin):
    ctx = _make_ctx()
    await plugin.autoreply_add(ctx, "Hello there", "General Kenobi!")
    assert plugin._read_config(1)["rules"]["hello there"] == "General Kenobi!"


async def test_autoreply_remove_deletes_rule(plugin):
    plugin._update_config(1, lambda cfg: cfg.setdefault("rules", {}).update({"hello there": "General Kenobi!"}))
    ctx = _make_ctx()

    await plugin.autoreply_remove(ctx, "Hello there")

    assert "hello there" not in plugin._read_config(1).get("rules", {})


async def test_autoreply_list_shows_rules(plugin):
    plugin._update_config(1, lambda cfg: cfg.setdefault("rules", {}).update({"hello": "world"}))
    ctx = _make_ctx()

    await plugin.autoreply_list(ctx)

    embed = ctx.respond.call_args.kwargs["embed"]
    assert "hello" in embed.description


async def test_autoreply_message_triggers_reply(plugin):
    plugin._update_config(1, lambda cfg: cfg.setdefault("rules", {}).update({"hello there": "General Kenobi!"}))
    message = _make_message("  Hello   there  ")

    await plugin._on_message(message)

    message.channel.send.assert_called_once_with("General Kenobi!")
