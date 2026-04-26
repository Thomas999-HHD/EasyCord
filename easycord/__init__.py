"""
A developer-friendly framework for building Discord bots.

Quick start::

    from easycord.api.v1 import Bot
    from easycord.middleware import log_middleware

    bot = Bot()
    bot.use(log_middleware())

    @bot.slash(description="Ping the bot")
    async def ping(ctx):
        await ctx.respond("Pong!")

    bot.run("YOUR_TOKEN")

v4.0+: Import from easycord.api.v1 for stability guarantees.
This module (easycord.__init__) re-exports for convenience but v1 is canonical.

Escape hatches (always available):
- ctx.raw_interaction → discord.Interaction
- ctx.client → discord.Client
- bot.client → discord.Client
"""

# Re-export from stable v1 API
from .api.v1 import *  # noqa: F401,F403

# Legacy imports (backwards compat, v3.x style)
from .audit import AuditLog
from .bot import Bot
from .embed_cards import EmbedCard, ErrorEmbed, InfoEmbed, SuccessEmbed, WarningEmbed
from .builders import ButtonRowBuilder, EmbedBuilder, ModalBuilder, SelectMenuBuilder
from .composer import Composer
from .context import Context
from .context_builder import ContextBuilder
from .database import DatabaseConfig, EasyCordDatabase, GuildRecord, MemoryDatabase, SQLiteDatabase
from .decorators import ai_tool, component, message_command, modal, on, slash, task, user_command
from .i18n import LocalizationManager
from .group import SlashGroup
from .plugin import Plugin
from .server_config import ServerConfig, ServerConfigStore
from .tools import ToolCall, ToolDef, ToolRegistry, ToolResult, ToolSafety
from .orchestrator import FallbackStrategy, Orchestrator, ProviderStrategy, RunContext
from .tool_limits import RateLimit, ToolLimiter
from .conversation_memory import Conversation, ConversationMemory, ConversationTurn
from .helpers import ConfigHelpers, ContextHelpers, RateLimitHelpers, ToolHelpers

__all__ = [
    "AuditLog",
    "ai_tool",
    "Bot",
    "ButtonRowBuilder",
    "Composer",
    "ConfigHelpers",
    "Conversation",
    "ConversationMemory",
    "ConversationTurn",
    "Context",
    "ContextBuilder",
    "ContextHelpers",
    "EmbedBuilder",
    "EmbedCard",
    "DatabaseConfig",
    "EasyCordDatabase",
    "FallbackStrategy",
    "component",
    "ErrorEmbed",
    "GuildRecord",
    "InfoEmbed",
    "ModalBuilder",
    "message_command",
    "modal",
    "MemoryDatabase",
    "LocalizationManager",
    "Orchestrator",
    "Plugin",
    "ProviderStrategy",
    "RateLimit",
    "RateLimitHelpers",
    "RunContext",
    "SelectMenuBuilder",
    "SlashGroup",
    "SuccessEmbed",
    "ToolCall",
    "ToolDef",
    "ToolHelpers",
    "ToolLimiter",
    "ToolRegistry",
    "ToolResult",
    "ToolSafety",
    "slash",
    "on",
    "SQLiteDatabase",
    "WarningEmbed",
    "user_command",
    "task",
    "ServerConfig",
    "ServerConfigStore",
]
