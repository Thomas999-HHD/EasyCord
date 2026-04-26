"""
EasyCord v4.0 Stable Public API

This namespace guarantees API stability through v4.x.
All exports here follow semantic versioning and deprecation policy.

For escape hatches (raw Discord access), see:
- ctx.raw_interaction → discord.Interaction
- ctx.client → discord.Client
- bot.client → discord.Client

For internal/experimental: see easycord._* modules (no stability guarantees).
"""

from ...audit import AuditLog
from ...bot import Bot
from ...builders import ButtonRowBuilder, EmbedBuilder, ModalBuilder, SelectMenuBuilder
from ...composer import Composer
from ...context import Context
from ...context_builder import ContextBuilder
from ...database import DatabaseConfig, EasyCordDatabase, GuildRecord, MemoryDatabase, SQLiteDatabase
from ...decorators import ai_tool, component, message_command, modal, on, slash, task, user_command
from ...embed_cards import EmbedCard, ErrorEmbed, InfoEmbed, SuccessEmbed, WarningEmbed
from ...group import SlashGroup
from ...i18n import LocalizationManager
from ...plugin import Plugin
from ...server_config import ServerConfig, ServerConfigStore
from ...tools import ToolCall, ToolDef, ToolRegistry, ToolResult, ToolSafety
from ...orchestrator import FallbackStrategy, Orchestrator, ProviderStrategy, RunContext
from ...tool_limits import RateLimit, ToolLimiter
from ...conversation_memory import Conversation, ConversationMemory, ConversationTurn
from ...helpers import ConfigHelpers, ContextHelpers, RateLimitHelpers, ToolHelpers

__all__ = [
    # Core
    "Bot",
    "Context",
    "Plugin",
    "Composer",

    # Decorators
    "slash",
    "on",
    "task",
    "ai_tool",
    "component",
    "message_command",
    "user_command",
    "modal",

    # Groups & Registry
    "SlashGroup",
    "ToolRegistry",
    "ToolDef",
    "ToolCall",
    "ToolResult",
    "ToolSafety",

    # Builders
    "EmbedBuilder",
    "ButtonRowBuilder",
    "SelectMenuBuilder",
    "ModalBuilder",

    # Embeds
    "EmbedCard",
    "SuccessEmbed",
    "ErrorEmbed",
    "InfoEmbed",
    "WarningEmbed",

    # Config & Storage
    "ServerConfig",
    "ServerConfigStore",
    "DatabaseConfig",
    "EasyCordDatabase",
    "MemoryDatabase",
    "SQLiteDatabase",
    "GuildRecord",

    # AI (optional)
    "Orchestrator",
    "ProviderStrategy",
    "FallbackStrategy",
    "RunContext",

    # Conversation (optional)
    "Conversation",
    "ConversationMemory",
    "ConversationTurn",

    # Helpers
    "ContextHelpers",
    "ConfigHelpers",
    "ToolHelpers",
    "RateLimitHelpers",
    "RateLimit",
    "ToolLimiter",

    # Misc
    "ContextBuilder",
    "AuditLog",
    "LocalizationManager",
]
