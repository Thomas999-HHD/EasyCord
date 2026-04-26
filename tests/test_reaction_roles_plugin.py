"""Tests for reaction roles plugin."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from easycord import ServerConfig
from easycord.plugins.reaction_roles import ReactionRolesPlugin


@pytest.fixture
def plugin():
    """Create ReactionRolesPlugin instance."""
    plugin_inst = ReactionRolesPlugin()
    return plugin_inst


@pytest.fixture
def mock_guild():
    """Create mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 12345
    guild.name = "Test Server"
    return guild


@pytest.fixture
def mock_member(mock_guild):
    """Create mock Discord member."""
    member = AsyncMock(spec=discord.Member)
    member.id = 999
    member.guild = mock_guild
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    return member


@pytest.fixture
def mock_role(mock_guild):
    """Create mock Discord role."""
    role = MagicMock(spec=discord.Role)
    role.id = 777
    role.name = "Member"
    role.guild = mock_guild
    return role


@pytest.fixture
def mock_payload():
    """Create mock RawReactionActionEvent."""
    payload = MagicMock(spec=discord.RawReactionActionEvent)
    payload.guild_id = 12345
    payload.message_id = 54321
    payload.user_id = 999
    payload.emoji = MagicMock()
    payload.emoji.__str__ = MagicMock(return_value="✅")
    return payload


@pytest.mark.asyncio
async def test_plugin_initializes(plugin):
    """Plugin can be initialized."""
    assert plugin is not None
    assert plugin.config_store is not None


@pytest.mark.asyncio
async def test_set_mapping(plugin, mock_guild):
    """Can set emoji->role mapping."""
    config_data = {}

    def get_other_side_effect(key, default=None):
        return config_data.get(key, default)

    def set_other_side_effect(key, value):
        config_data[key] = value

    mock_server_cfg = MagicMock(spec=ServerConfig)
    mock_server_cfg.get_other = MagicMock(side_effect=get_other_side_effect)
    mock_server_cfg.set_other = MagicMock(side_effect=set_other_side_effect)

    with patch.object(plugin.config_store, "load", new_callable=AsyncMock, return_value=mock_server_cfg):
        with patch.object(plugin.config_store, "save", new_callable=AsyncMock):
            await plugin._set_mapping(mock_guild.id, 54321, "✅", 777)

            mappings = await plugin._get_mappings(mock_guild.id, 54321)
            assert mappings["✅"] == 777


@pytest.mark.asyncio
async def test_remove_mapping(plugin, mock_guild):
    """Can remove emoji->role mapping."""
    config_data = {"54321": {"✅": 777}}

    def get_other_side_effect(key, default=None):
        return config_data.get(key, default)

    def set_other_side_effect(key, value):
        config_data[key] = value

    mock_server_cfg = MagicMock(spec=ServerConfig)
    mock_server_cfg.get_other = MagicMock(side_effect=get_other_side_effect)
    mock_server_cfg.set_other = MagicMock(side_effect=set_other_side_effect)

    with patch.object(plugin.config_store, "load", new_callable=AsyncMock, return_value=mock_server_cfg):
        with patch.object(plugin.config_store, "save", new_callable=AsyncMock):
            # First set
            await plugin._set_mapping(mock_guild.id, 54321, "✅", 777)
            # Then remove
            await plugin._remove_mapping(mock_guild.id, 54321, "✅")

            mappings = await plugin._get_mappings(mock_guild.id, 54321)
            assert "✅" not in mappings


@pytest.mark.asyncio
async def test_get_mappings_empty(plugin, mock_guild):
    """Returns empty dict when no mappings exist."""
    mock_server_cfg = MagicMock(spec=ServerConfig)
    mock_server_cfg.get_other = MagicMock(return_value={})

    with patch.object(plugin.config_store, "load", new_callable=AsyncMock, return_value=mock_server_cfg):
        mappings = await plugin._get_mappings(mock_guild.id, 54321)
        assert mappings == {}


@pytest.mark.asyncio
async def test_on_reaction_add(plugin, mock_guild, mock_member, mock_role, mock_payload):
    """Adds role when member reacts."""
    mock_server_cfg = MagicMock(spec=ServerConfig)
    mock_server_cfg.get_other = MagicMock(return_value={"54321": {"✅": 777}})

    mock_bot = MagicMock()
    mock_bot.user.id = 1111
    mock_bot.get_guild = MagicMock(return_value=mock_guild)
    mock_guild.get_member = MagicMock(return_value=mock_member)
    mock_guild.get_role = MagicMock(return_value=mock_role)

    with patch.object(plugin, "_bot", mock_bot):
        with patch.object(plugin.config_store, "load", new_callable=AsyncMock, return_value=mock_server_cfg):
            await plugin._on_reaction_add(mock_payload)
            mock_member.add_roles.assert_called_once()


@pytest.mark.asyncio
async def test_on_reaction_add_ignores_bot(plugin, mock_payload):
    """Ignores reactions from bot itself."""
    mock_bot = MagicMock()
    mock_bot.user.id = 999  # Same as payload user
    mock_payload.user_id = 999

    with patch.object(plugin, "_bot", mock_bot):
        with patch.object(plugin, "_get_mappings") as mock_get:
            await plugin._on_reaction_add(mock_payload)
            mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_on_reaction_add_no_mapping(plugin, mock_guild, mock_payload):
    """Ignores reactions with no mapping."""
    mock_server_cfg = MagicMock(spec=ServerConfig)
    mock_server_cfg.get_other = MagicMock(return_value={})

    mock_bot = MagicMock()
    mock_bot.user.id = 1111
    mock_bot.get_guild = MagicMock(return_value=mock_guild)

    with patch.object(plugin, "_bot", mock_bot):
        with patch.object(plugin.config_store, "load", new_callable=AsyncMock, return_value=mock_server_cfg):
            await plugin._on_reaction_add(mock_payload)
            # Should not attempt to add role


@pytest.mark.asyncio
async def test_on_reaction_remove(plugin, mock_guild, mock_member, mock_role, mock_payload):
    """Removes role when member removes reaction."""
    mock_server_cfg = MagicMock(spec=ServerConfig)
    mock_server_cfg.get_other = MagicMock(return_value={"54321": {"✅": 777}})

    mock_bot = MagicMock()
    mock_bot.user.id = 1111
    mock_bot.get_guild = MagicMock(return_value=mock_guild)
    mock_guild.get_member = MagicMock(return_value=mock_member)
    mock_guild.get_role = MagicMock(return_value=mock_role)

    with patch.object(plugin, "_bot", mock_bot):
        with patch.object(plugin.config_store, "load", new_callable=AsyncMock, return_value=mock_server_cfg):
            await plugin._on_reaction_remove(mock_payload)
            mock_member.remove_roles.assert_called_once()


@pytest.mark.asyncio
async def test_on_message_delete_cleanup(plugin, mock_guild):
    """Cleans up mappings when message deleted."""
    config_data = {"reaction_roles": {"54321": {"✅": 777}, "54322": {"❌": 888}}}

    def get_other_side_effect(key, default=None):
        return config_data.get(key, default)

    def set_other_side_effect(key, value):
        config_data[key] = value

    mock_server_cfg = MagicMock(spec=ServerConfig)
    mock_server_cfg.get_other = MagicMock(side_effect=get_other_side_effect)
    mock_server_cfg.set_other = MagicMock(side_effect=set_other_side_effect)

    payload = MagicMock()
    payload.guild_id = mock_guild.id
    payload.message_id = 54321

    with patch.object(plugin.config_store, "load", new_callable=AsyncMock, return_value=mock_server_cfg):
        with patch.object(plugin.config_store, "save", new_callable=AsyncMock):
            await plugin._on_message_delete(payload)

            # Verify mapping was removed
            assert "54321" not in config_data["reaction_roles"]
            assert "54322" in config_data["reaction_roles"]  # Other message mappings stay


@pytest.mark.asyncio
async def test_on_role_delete_cleanup(plugin, mock_guild, mock_role):
    """Cleans up deleted role from all mappings."""
    config_data = {
        "reaction_roles": {
            "54321": {"✅": 777, "❌": 888},
            "54322": {"✅": 777},
        }
    }

    def get_other_side_effect(key, default=None):
        return config_data.get(key, default)

    def set_other_side_effect(key, value):
        config_data[key] = value

    mock_server_cfg = MagicMock(spec=ServerConfig)
    mock_server_cfg.get_other = MagicMock(side_effect=get_other_side_effect)
    mock_server_cfg.set_other = MagicMock(side_effect=set_other_side_effect)

    with patch.object(plugin.config_store, "load", new_callable=AsyncMock, return_value=mock_server_cfg):
        with patch.object(plugin.config_store, "save", new_callable=AsyncMock):
            await plugin._on_role_delete(mock_role)

            # Verify role 777 was removed from all mappings
            # 888 should still be there
            mappings = config_data.get("reaction_roles", {})
            assert "54321" in mappings  # Message still exists
            assert "✅" not in mappings["54321"]  # But emoji for role 777 removed
            assert "❌" in mappings["54321"]  # Other emoji still there
            assert mappings["54321"]["❌"] == 888  # Verify it's the right role
            assert "54322" not in mappings  # This message had only role 777, so removed entirely
