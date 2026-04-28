"""
EasyCord Discord Framework for building Discord bots.

Quick start::

    from easycord import Bot
    from easycord.middleware import log_middleware

    bot = Bot()
    bot.use(log_middleware())

    @bot.slash(description="Ping the bot")
    async def ping(ctx):
        await ctx.respond("Pong!")

    bot.run("YOUR_TOKEN")
"""

from .audit import AuditLog
from .bot import Bot
from .cog import Cog, GroupCog
from .builders import ButtonRowBuilder, EmbedBuilder, ModalBuilder, SelectMenuBuilder
from .composer import Composer
from .context import Context
from .decorators import component, endpoint, message_command, modal, on, slash, task, user_command
from .i18n import LocalizationManager
from .group import SlashGroup
from .plugin import Plugin
from .server_config import ServerConfig, ServerConfigStore
from .plugins import AnnouncementsPlugin, AutoReplyPlugin, GuildPlugin, IntegrationPlugin, JsonConfigPlugin

__all__ = [
    "AuditLog",
    "AnnouncementsPlugin",
    "Bot",
    "ButtonRowBuilder",
    "Cog",
    "AutoReplyPlugin",
    "Composer",
    "Context",
    "EmbedBuilder",
    "component",
    "endpoint",
    "LocalizationManager",
    "GuildPlugin",
    "IntegrationPlugin",
    "GroupCog",
    "ModalBuilder",
    "message_command",
    "modal",
    "Plugin",
    "JsonConfigPlugin",
    "SelectMenuBuilder",
    "SlashGroup",
    "slash",
    "on",
    "user_command",
    "task",
    "ServerConfig",
    "ServerConfigStore",
]
