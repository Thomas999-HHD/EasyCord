import logging
from dataclasses import dataclass, field
from typing import Callable, Any

logger = logging.getLogger("easycord")


@dataclass
class CommandEntry:
    """Metadata for a registered slash command."""
    name: str
    description: str
    plugin: str | None
    guild_id: int | None
    is_alias: bool = False


class InteractionRegistry:
    """Central registry for slash commands, persistent components, and modals."""

    def __init__(self):
        self.commands: dict[str, CommandEntry] = {}
        self.components: dict[str, dict[str, Any]] = {}
        self.modals: dict[str, dict[str, Any]] = {}

    # ── Commands ──────────────────────────────────────────────

    def register_command(
        self,
        name: str,
        description: str,
        *,
        plugin: str | None = None,
        guild_id: int | None = None,
        is_alias: bool = False,
    ) -> None:
        """Record a slash command registration."""
        if name in self.commands:
            existing = self.commands[name]
            raise ValueError(
                f"Slash command {name!r} already registered by "
                f"{existing.plugin or 'Bot'!r}"
            )
        self.commands[name] = CommandEntry(
            name=name,
            description=description,
            plugin=plugin,
            guild_id=guild_id,
            is_alias=is_alias,
        )
        logger.debug(
            "Registered COMMAND /%s%s  → %s",
            name,
            f" (alias)" if is_alias else "",
            plugin or "Bot",
        )

    def unregister_command(self, name: str) -> None:
        """Remove a slash command from the registry."""
        self.commands.pop(name, None)

    def commands_for_plugin(self, plugin_name: str) -> list[CommandEntry]:
        """Return all commands registered by a given plugin.

        Intended for runtime inspection and diagnostics (e.g., health checks,
        admin introspection commands). Plugins should NOT call this method
        against other plugins — doing so creates implicit coupling between
        plugins that the framework cannot track or enforce.
        """
        return [e for e in self.commands.values() if e.plugin == plugin_name]

    def list_commands(self) -> list[CommandEntry]:
        """Return all registered commands sorted by name."""
        return sorted(self.commands.values(), key=lambda e: e.name)

    def register_component(self, custom_id: str, func: Callable, source_plugin: str | None = None) -> None:
        if custom_id in self.components:
            existing = self.components[custom_id]
            raise ValueError(
                f"Component ID {custom_id!r} already registered by:\n"
                f"- Plugin: {existing.get('plugin') or 'Bot'}\n"
                f"- Method: {existing['func'].__name__}"
            )
        self.components[custom_id] = {"func": func, "plugin": source_plugin}
        logger.debug(
            "Registered COMPONENT %r\n  → Plugin: %s\n  → Method: %s",
            custom_id,
            source_plugin or "Bot",
            func.__name__,
        )

    def register_modal(self, custom_id: str, func: Callable, source_plugin: str | None = None) -> None:
        if custom_id in self.modals:
            existing = self.modals[custom_id]
            raise ValueError(
                f"Modal ID {custom_id!r} already registered by:\n"
                f"- Plugin: {existing.get('plugin') or 'Bot'}\n"
                f"- Method: {existing['func'].__name__}"
            )
        self.modals[custom_id] = {"func": func, "plugin": source_plugin}
        logger.debug(
            "Registered MODAL %r\n  → Plugin: %s\n  → Method: %s",
            custom_id,
            source_plugin or "Bot",
            func.__name__,
        )
