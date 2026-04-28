import discord
import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from easycord.plugins.base import GuildPlugin, JsonConfigPlugin


def test_require_guild_returns_guild():
    plugin = GuildPlugin()
    ctx = MagicMock()
    guild = MagicMock(spec=discord.Guild)
    ctx.guild = guild

    assert plugin.require_guild(ctx) is guild


def test_require_guild_raises_in_dm():
    plugin = GuildPlugin()
    ctx = MagicMock()
    ctx.guild = None

    with pytest.raises(RuntimeError, match="only works in a server"):
        plugin.require_guild(ctx)


@pytest.fixture
def plugin_data_dir():
    path = Path(".plugin-test-data") / f"base-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_json_config_plugin_reads_and_writes(plugin_data_dir):
    plugin = JsonConfigPlugin(data_dir=str(plugin_data_dir))
    plugin._update_config(1, lambda cfg: cfg.update({"alpha": 1}))

    assert plugin._read_config(1)["alpha"] == 1
