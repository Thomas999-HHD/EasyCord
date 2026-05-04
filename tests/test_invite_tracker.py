from unittest.mock import AsyncMock, MagicMock

from easycord.plugins.invite_tracker import InviteTrackerPlugin


async def test_invite_tracker_detects_increased_invite_use():
    plugin = InviteTrackerPlugin()
    guild = MagicMock()
    guild.id = 123
    invite = MagicMock()
    invite.code = "abc"
    invite.uses = 2
    guild.invites = AsyncMock(return_value=[invite])
    bot = MagicMock()
    bot.get_guild.return_value = guild
    plugin._bot = bot
    plugin._invite_cache[guild.id] = {"abc": 1}
    plugin._log_invite = AsyncMock()

    member = MagicMock()
    member.guild = guild

    await plugin._on_member_join(member)

    plugin._log_invite.assert_awaited_once_with(member, "abc")
