"""RolesPlugin — flagship role orchestration system."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from easycord.api.v1 import Context, Plugin, slash
from easycord.kernel import Event
from easycord.server_config import ServerConfigStore

from .api import RolesAPI
from .commands import RoleCommands
from .diff import DiffEngine
from .policy import PolicyConfig, PolicyEngine
from .reconcile import ReconciliationEngine
from .storage import RoleStorage

if TYPE_CHECKING:
    from easycord.api.v1 import Bot

logger = logging.getLogger("easycord.roles")


class RolesPlugin(Plugin):
    """
    Role orchestration plugin.

    Provides:
    - Declarative role blueprint system
    - Idempotent diff + reconciliation
    - Safety policy enforcement
    - Cross-plugin role API
    - Full audit trail via EventBus

    Example::

        bot = Bot()
        bot.add_plugin(RolesPlugin())

        # Users can then:
        # /roles setup       — initialize default roles
        # /roles sync        — apply blueprint to guild
        # /roles debug       — inspect current state
        # /roles simulate    — dry-run preview

        # Other plugins can:
        # from easycord.plugins.roles import RolesPlugin
        # roles_plugin = bot.get_plugin(RolesPlugin)
        # await roles_plugin.api.assign(user_id, guild_id, "moderator")
    """

    def __init__(self, config_dir: str = ".easycord/server-config", policy: PolicyConfig | None = None):
        super().__init__()
        self.name = "roles"

        # Initialize subsystems
        self.config_store = ServerConfigStore(config_dir)
        self.storage = RoleStorage(self.config_store)
        self.diff_engine = DiffEngine()
        self.policy_engine = PolicyEngine(policy or PolicyConfig())
        self.reconcile_engine = ReconciliationEngine()

        # Public API for cross-plugin use
        self.api = RolesAPI(self)

        # Command handlers
        self.commands = RoleCommands(self)

        # Define capabilities
        self._capabilities = [
            "roles.manage",   # Sync blueprints
            "roles.create",   # Create new roles
            "roles.assign",   # Assign roles to members
            "roles.simulate", # Dry-run
            "roles.debug",    # View state
        ]

    def _event(self, action: str, data: dict) -> Event:
        """Create a namespaced EventBus event."""
        return Event(f"roles.{action}", data)

    async def on_load(self) -> None:
        """Register capabilities on load."""
        logger.info("RolesPlugin loaded")

        # Define capabilities
        for cap in self._capabilities:
            self.bot.capability_registry.define(
                name=cap,
                description=f"Role management: {cap}",
            )

        # Emit load event
        await self.bot.events.emit(self._event("plugin_loaded", {}))

    async def on_ready(self) -> None:
        """Validate blueprints on ready."""
        logger.debug("RolesPlugin ready")
        await self.bot.events.emit(self._event("plugin_ready", {}))

    async def on_unload(self) -> None:
        """Cleanup on removal."""
        logger.info("RolesPlugin unloaded")
        await self.bot.events.emit(self._event("plugin_unloaded", {}))

    @slash(
        description="Initialize default role blueprints",
        capabilities=["roles.manage"],
        guild_only=True,
    )
    async def roles_setup(self, ctx: Context) -> None:
        """Setup default roles."""
        await self.commands.setup(ctx)

    @slash(
        description="Apply role blueprints to this guild",
        capabilities=["roles.manage"],
        guild_only=True,
    )
    async def roles_sync(self, ctx: Context) -> None:
        """Sync roles."""
        await self.commands.sync(ctx)

    @slash(
        description="Preview role changes (dry-run)",
        capabilities=["roles.simulate"],
        guild_only=True,
    )
    async def roles_simulate(self, ctx: Context) -> None:
        """Simulate changes."""
        await self.commands.simulate(ctx)

    @slash(
        description="Inspect current role state",
        capabilities=["roles.debug"],
        guild_only=True,
    )
    async def roles_debug(self, ctx: Context) -> None:
        """Debug role state."""
        await self.commands.debug(ctx)

    @slash(
        description="Export role blueprints as JSON",
        capabilities=["roles.manage"],
        guild_only=True,
    )
    async def roles_export(self, ctx: Context) -> None:
        """Export blueprints."""
        await self.commands.export(ctx)

    @slash(
        description="Reset all role blueprints",
        capabilities=["roles.manage"],
        guild_only=True,
    )
    async def roles_reset(self, ctx: Context) -> None:
        """Reset blueprints."""
        await self.commands.reset(ctx)

    def get_api(self) -> RolesAPI:
        """Get public API for cross-plugin use."""
        return self.api
