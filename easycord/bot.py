"""Bot shell wiring together the mixin modules."""
from __future__ import annotations

import asyncio
import os
import logging
from typing import Callable, Any

import discord
from discord import app_commands

from .builtin_plugins import build_builtin_plugins
from .database import DatabaseConfig, EasyCordDatabase, MemoryDatabase, SQLiteDatabase
from .i18n import LocalizationManager
from .conversation_memory import ConversationMemory
from .middleware import MiddlewareFn
from .plugin import Plugin
from ._bot_commands import _CommandsMixin
from ._bot_events import _EventsMixin
from ._bot_guild import _GuildMixin
from ._bot_plugins import _PluginsMixin
from .registry import InteractionRegistry
from .tools import ToolRegistry
from .builtin_tools import register_builtin_tools

logger = logging.getLogger("easycord")


class Bot(_EventsMixin, _GuildMixin, _PluginsMixin, _CommandsMixin, discord.Client):
    """
    The main bot — a discord.Client with slash commands,
    middleware, event listeners, and plugins built in.

    Quick start::

        import os
        from easycord import Bot
        from easycord.middleware import log_middleware, catch_errors

        bot = Bot()
        bot.use(log_middleware())
        bot.use(catch_errors())

        @bot.slash(description="Ping the bot")
        async def ping(ctx):
            await ctx.respond("Pong!")

        bot.run(os.environ["DISCORD_TOKEN"])

    Parameters
    ----------
    intents:
        Discord gateway intents. Defaults to ``discord.Intents.default()``.
    auto_sync:
        Automatically sync slash commands with Discord on startup (default ``True``).
        Set to ``False`` during development to avoid hitting Discord's sync rate limit.
    sync_guild_id:
        Optional development guild ID. When set, auto-sync copies global
        commands into that guild and syncs the guild command set instead of
        publishing commands globally.
    """

    def __init__(
        self,
        *,
        intents: discord.Intents | None = None,
        auto_sync: bool = True,
        sync_guild_id: int | None = None,
        load_builtin_plugins: bool = False,
        database: EasyCordDatabase | None = None,
        db_backend: str | None = None,
        db_path: str | None = None,
        db_auto_sync_guilds: bool | None = None,
        localization: LocalizationManager | None = None,
        default_locale: str = "en-US",
        translations: dict | None = None,
        auto_translator: Callable[[str, str, str], str | None] | None = None,
        ai_provider=None,
        enable_conversation_memory: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(intents=intents or discord.Intents.default(), **kwargs)
        self.tree = app_commands.CommandTree(self)
        self._auto_sync = auto_sync
        self._sync_guild_id = sync_guild_id
        self._middleware: list[MiddlewareFn] = []
        self._event_handlers: dict[str, list[Callable]] = {}
        self._plugins: list[Plugin] = []
        self._task_handles: dict[int, list[asyncio.Task]] = {}
        self._task_statuses: dict[str, dict[str, Any]] = {}
        self._background_tasks: set[asyncio.Task] = set()
        self._webhooks: dict[int, discord.Webhook] = {}
        self.registry = InteractionRegistry()
        self.ai_provider = ai_provider
        self.conversation_memory = (
            ConversationMemory() if enable_conversation_memory else None
        )
        self.ai_tools: dict[str, dict] = {}
        self.tool_registry = ToolRegistry()
        try:
            register_builtin_tools(self.tool_registry)
        except Exception as e:
            logger.debug(f"Failed to register builtin AI tools: {e}")
        self._error_handler = None
        self._command_error_handlers: dict[str, object] = {}
        self.db = database or self._create_database(
            db_backend=db_backend,
            db_path=db_path,
            db_auto_sync_guilds=db_auto_sync_guilds,
        )
        self.localization: LocalizationManager | None = localization or (
            LocalizationManager(
                default_locale=default_locale,
                translations=translations,
                auto_translator=auto_translator,
            )
            if translations or auto_translator
            else None
        )
        if load_builtin_plugins:
            self.load_builtin_plugins()

    # ── Interaction inspection and command sync planning ──────

    def inspect_interactions(self) -> dict[str, list[dict[str, Any]]]:
        """Return registered interactions grouped by EasyCord interaction type."""
        return self.registry.grouped()

    def plan_command_sync(
        self,
        *,
        guild_id: int | None = None,
        remote_commands: list[str] | None = None,
    ) -> dict[str, list[str]]:
        """Build a command sync diff without contacting Discord by default.

        Pass ``remote_commands`` in tests or after your own fetch to compare the
        current EasyCord inventory with Discord's current command names.
        """
        local_entries = self.registry.iter_syncable(guild_id=guild_id)
        local_names = [entry.name for entry in local_entries if entry.enabled]
        remote_names = list(remote_commands or [])

        warnings: list[str] = []
        duplicates = sorted({name for name in local_names if local_names.count(name) > 1})
        for name in duplicates:
            warnings.append(f"Duplicate local command name: {name}")

        local_set = set(local_names)
        remote_set = set(remote_names)
        return {
            "added": sorted(local_set - remote_set),
            "changed": [],
            "removed": sorted(remote_set - local_set),
            "unchanged": sorted(local_set & remote_set),
            "warnings": warnings,
        }

    async def sync_commands(
        self,
        *,
        guild_id: int | None = None,
        dry_run: bool = False,
        remote_commands: list[str] | None = None,
        confirm_removals: bool = False,
    ) -> dict[str, list[str]]:
        """Plan or execute command sync through ``discord.py``'s CommandTree.

        If the plan detects removals, pass ``confirm_removals=True`` before a
        non-dry-run sync. This keeps EasyCord from applying a destructive sync
        without an explicit caller decision.
        """
        plan = self.plan_command_sync(
            guild_id=guild_id,
            remote_commands=remote_commands,
        )
        if dry_run:
            return plan
        if plan["removed"] and not confirm_removals:
            raise RuntimeError(
                "Command sync would remove remote commands. Re-run with "
                "confirm_removals=True after reviewing plan_command_sync()."
            )
        guild = discord.Object(id=guild_id) if guild_id is not None else None
        if guild is not None:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        for entry in self.registry.iter_syncable(guild_id=guild_id):
            entry.sync_state = "synced"
        return plan

    def enable_interaction_inspector(self, *, owner_ids: set[int] | None = None) -> None:
        """Register the optional ``/easycord interactions`` developer command."""
        group = app_commands.Group(
            name="easycord",
            description="EasyCord developer diagnostics",
        )

        @group.command(name="interactions", description="Show registered EasyCord interactions")
        async def interactions(interaction: discord.Interaction) -> None:
            if owner_ids is not None and interaction.user.id not in owner_ids:
                await interaction.response.send_message("Not authorized.", ephemeral=True)
                return
            grouped = self.inspect_interactions()
            lines = [
                f"{kind}: {len(entries)}"
                for kind, entries in grouped.items()
            ]
            await interaction.response.send_message("\n".join(lines), ephemeral=True)

        self.tree.add_command(group)

    def _create_database(
        self,
        *,
        db_backend: str | None,
        db_path: str | None,
        db_auto_sync_guilds: bool | None,
    ) -> EasyCordDatabase:
        config = DatabaseConfig.from_env()
        backend = db_backend or config.backend
        path = db_path or os.getenv("EASYCORD_DB_PATH") or config.path
        auto_sync = config.auto_sync_guilds if db_auto_sync_guilds is None else db_auto_sync_guilds

        if backend == "memory":
            return MemoryDatabase(auto_sync_guilds=auto_sync)
        if backend == "sqlite":
            return SQLiteDatabase(path=path, auto_sync_guilds=auto_sync)
        raise ValueError(
            f"Unknown database backend {backend!r}. Must be 'sqlite' or 'memory'."
        )

    def load_builtin_plugins(self) -> None:
        """Load the framework's bundled first-party plugins."""
        loaded_types = {type(plugin) for plugin in self._plugins}
        for plugin in build_builtin_plugins():
            if type(plugin) in loaded_types:
                continue
            self.add_plugin(plugin)
            loaded_types.add(type(plugin))

    async def setup_hook(self) -> None:
        await self.db.ensure_schema()
        if self.db.auto_sync_guilds:
            await self.db.sync_guilds([guild.id for guild in getattr(self, "guilds", [])])
        if self._auto_sync:
            if self._sync_guild_id is not None:
                guild = discord.Object(id=self._sync_guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            else:
                await self.tree.sync()
        for plugin in self._plugins:
            await plugin.on_load()
            self._start_plugin_tasks(plugin)

    async def on_ready(self) -> None:
        if self.db.auto_sync_guilds:
            await self.db.sync_guilds([guild.id for guild in getattr(self, "guilds", [])])
        for plugin in self._plugins:
            try:
                await plugin.on_ready()
            except Exception:
                logger.exception("Error calling on_ready for %s", plugin.__class__.__name__)
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)  # type: ignore[union-attr]

    async def close(self) -> None:  # type: ignore[override]
        """Close the bot and release framework-owned resources.

        Cancels plugin background loops and one-shot framework tasks before
        closing Discord and database resources. This prevents lingering task
        references from keeping plugin/bot state alive after shutdown.
        """
        pending: list[asyncio.Task] = []
        for handles in self._task_handles.values():
            pending.extend(handles)
        pending.extend(getattr(self, "_background_tasks", set()))

        for task in pending:
            if not task.done():
                task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        self._task_handles.clear()
        getattr(self, "_background_tasks", set()).clear()

        try:
            await self.db.close()
        finally:
            await super().close()

    def run(self, token: str, **kwargs) -> None:  # type: ignore[override]
        """Configure basic logging and start the bot."""
        logging.basicConfig(level=logging.INFO)
        super().run(token, **kwargs)


# Imported here to avoid a circular import at module level while still allowing
# the type annotation in add_group to resolve at runtime.
from .group import SlashGroup  # noqa: E402
