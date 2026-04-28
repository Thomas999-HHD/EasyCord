"""Developer-focused base classes for bundled and custom plugins."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar

import discord

from ..plugin import Plugin
from ._shared import read_json_file, write_json_file

TPlugin = TypeVar("TPlugin", bound=Plugin)


class IntegrationPlugin(Plugin):
    """Plugin base with helpers for consuming other plugins and endpoints.

    This is the easiest base class to use when your plugin needs to talk to
    another plugin or call a named endpoint registered elsewhere in the bot.
    """

    def get_plugin(self, target: str | type[TPlugin]) -> TPlugin | None:
        """Return a loaded plugin by class, configured name, or qualified name."""
        bot = self.bot
        for plugin in bot._plugins:
            if isinstance(target, str):
                if (
                    type(plugin).__name__ == target
                    or getattr(plugin, "name", None) == target
                    or getattr(plugin, "qualified_name", None) == target
                ):
                    return plugin  # type: ignore[return-value]
            elif isinstance(plugin, target):
                return plugin  # type: ignore[return-value]
        return None

    def require_plugin(self, target: str | type[TPlugin]) -> TPlugin:
        """Return a plugin or raise if it is not currently loaded."""
        plugin = self.get_plugin(target)
        if plugin is None:
            target_name = target if isinstance(target, str) else target.__name__
            raise RuntimeError(f"Required plugin {target_name!r} is not loaded")
        return plugin

    def get_endpoint(self, name: str) -> Callable[..., Any] | None:
        """Return a named endpoint if one has been registered on the bot."""
        return self.bot.get_endpoint(name)

    def require_endpoint(self, name: str) -> Callable[..., Any]:
        """Return a named endpoint or raise if it is not registered."""
        endpoint = self.get_endpoint(name)
        if endpoint is None:
            raise RuntimeError(f"Required endpoint {name!r} is not registered")
        return endpoint

    async def call_endpoint(self, name: str, /, *args: Any, **kwargs: Any) -> Any:
        """Invoke a named endpoint and await it if needed."""
        return await self.bot.call_endpoint(name, *args, **kwargs)


class GuildPlugin(IntegrationPlugin):
    """Plugin base with helpers for server-only command flows.

    Subclass this when a plugin is only meaningful inside guilds. The helper
    methods reduce repeated guild checks and keep command handlers compact.
    """

    def require_guild(
        self,
        ctx: object,
        *,
        message: str = "This command only works in a server.",
    ) -> discord.Guild:
        guild = getattr(ctx, "guild", None)
        if guild is None:
            raise RuntimeError(message)
        return guild

    def require_text_channel(
        self,
        ctx: object,
        *,
        message: str = "This command requires a text channel.",
    ) -> discord.TextChannel:
        channel = getattr(ctx, "channel", None)
        if not isinstance(channel, discord.TextChannel):
            raise RuntimeError(message)
        return channel


class JsonConfigPlugin(GuildPlugin):
    """Plugin base that stores one JSON config file per guild.

    Use this for plugins that need a small amount of persistent server config
    without introducing a database dependency.
    """

    def __init__(self, *, data_dir: str = ".easycord/plugins") -> None:
        super().__init__()
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def _config_path(self, guild_id: int) -> Path:
        return self._data_dir / f"{guild_id}.json"

    def _read_config(self, guild_id: int) -> dict[str, Any]:
        return read_json_file(self._config_path(guild_id))

    def _write_config(self, guild_id: int, config: dict[str, Any]) -> None:
        write_json_file(self._config_path(guild_id), config)

    def _update_config(
        self,
        guild_id: int,
        updater: Callable[[dict[str, Any]], Any],
    ) -> Any:
        config = self._read_config(guild_id)
        result = updater(config)
        self._write_config(guild_id, config)
        return result
