"""Plugin lifecycle, cogs, extensions, task management, and shared method-scanner."""
from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
from typing import Callable
from types import ModuleType

import discord

from .plugin import Plugin

logger = logging.getLogger("easycord")


class _PluginsMixin:
    """Mixin: plugin add/remove, background tasks, and method scanning."""

    def _track_extension_addition(self, item: Plugin) -> None:
        current = getattr(self, "_active_extension", None)
        if current is not None:
            self._extension_additions.setdefault(current, []).append(item)

    def _track_extension_endpoint(self, name: str) -> None:
        current = getattr(self, "_active_extension", None)
        if current is not None:
            self._extension_endpoints.setdefault(current, []).append(name)

    @property
    def extensions(self) -> dict[str, ModuleType]:
        """Mapping of loaded extension names to imported modules."""
        return dict(self._extensions)

    @property
    def endpoints(self) -> dict[str, dict[str, Callable]]:
        """Mapping of endpoint names to registered callables and metadata."""
        return dict(self._endpoints)

    # ── Shared scanner ────────────────────────────────────────

    def _scan_methods(self, plugin: Plugin, *, parent=None) -> None:
        """Register all @slash and @on methods on *plugin*.

        parent: an ``app_commands.Group`` — when supplied, slash commands are
        added to the group instead of the command tree (used by add_group).
        """
        for _, method in inspect.getmembers(plugin, predicate=inspect.ismethod):
            if getattr(method, "_is_slash", False):
                self._register_slash(
                    method,
                    name=method._slash_name,
                    description=method._slash_desc,
                    guild_id=method._slash_guild,
                    guild_only=getattr(method, "_slash_guild_only", False),
                    ephemeral=getattr(method, "_slash_ephemeral", False),
                    permissions=getattr(method, "_slash_permissions", None),
                    cooldown=getattr(method, "_slash_cooldown", None),
                    autocomplete=getattr(method, "_slash_autocomplete", None),
                    choices=getattr(method, "_slash_choices", None),
                    parent=parent,
                )
                for alias in getattr(method, "_slash_aliases", []):
                    self._register_slash(
                        method,
                        name=alias,
                        description=method._slash_desc,
                        guild_id=method._slash_guild,
                        guild_only=getattr(method, "_slash_guild_only", False),
                        ephemeral=getattr(method, "_slash_ephemeral", False),
                        permissions=getattr(method, "_slash_permissions", None),
                        cooldown=getattr(method, "_slash_cooldown", None),
                        autocomplete=getattr(method, "_slash_autocomplete", None),
                        choices=getattr(method, "_slash_choices", None),
                        parent=parent,
                    )
            if getattr(method, "_is_event", False):
                self._event_handlers.setdefault(
                    method._event_name, []
                ).append(method)
            if getattr(method, "_is_user_command", False):
                self._register_context_menu(
                    method,
                    name=method._context_menu_name,
                    menu_type=discord.AppCommandType.user,
                    guild_id=method._context_menu_guild,
                )
            if getattr(method, "_is_message_command", False):
                self._register_context_menu(
                    method,
                    name=method._context_menu_name,
                    menu_type=discord.AppCommandType.message,
                    guild_id=method._context_menu_guild,
                )
            if getattr(method, "_is_component", False):
                custom_id = method._component_id
                if getattr(method, "_component_scoped", True):
                    custom_id = plugin.id(custom_id)
                self._register_component_handler(custom_id, method, source_plugin=type(plugin).__name__)
            if getattr(method, "_is_modal", False):
                custom_id = method._modal_id
                if getattr(method, "_modal_scoped", True):
                    custom_id = plugin.id(custom_id)
                self._register_modal_handler(custom_id, method, source_plugin=type(plugin).__name__)
            if getattr(method, "_is_endpoint", False):
                self.register_endpoint(
                    method._endpoint_name,
                    method,
                    source_plugin=type(plugin).__name__,
                )

    # ── Plugins ───────────────────────────────────────────────

    def add_plugin(self, plugin: Plugin) -> None:
        """Add a plugin, registering all of its slash commands and event handlers.

        Raises ``TypeError`` if ``plugin`` is not a :class:`Plugin` instance.
        Raises ``ValueError`` if the same plugin instance has already been added.
        """
        if not isinstance(plugin, Plugin):
            raise TypeError(
                f"expected a Plugin instance, got {type(plugin).__name__!r}"
            )
        if plugin in self._plugins:
            raise ValueError(
                f"{type(plugin).__name__} is already added to this bot. "
                "Create a new instance if you need a second copy."
            )
        plugin._bot = self
        self._plugins.append(plugin)
        self._track_extension_addition(plugin)
        self._scan_methods(plugin)
        if self.is_ready():
            asyncio.create_task(plugin.on_load())
            self._start_plugin_tasks(plugin)

    def add_plugins(self, *plugins: Plugin) -> None:
        """Add several plugins in one call."""
        for plugin in plugins:
            self.add_plugin(plugin)

    def load_builtin_plugins(self) -> None:
        """Load the bundled first-party plugin set once."""
        if getattr(self, "_builtin_plugins_loaded", False):
            return

        from .plugins import (
            AnnouncementsPlugin,
            AutoReplyPlugin,
            LevelsPlugin,
            PollsPlugin,
            TagsPlugin,
            WelcomePlugin,
        )

        self.add_plugins(
            WelcomePlugin(),
            LevelsPlugin(),
            PollsPlugin(),
            TagsPlugin(),
            AnnouncementsPlugin(),
            AutoReplyPlugin(),
        )
        self._builtin_plugins_loaded = True

    def add_cog(self, cog: "Cog") -> None:  # type: ignore[name-defined]
        """Register a Cog-like object using the same plugin plumbing."""
        from .cog import Cog

        if not isinstance(cog, Cog):
            raise TypeError(
                f"expected a Cog instance, got {type(cog).__name__!r}"
            )
        self.add_plugin(cog)

    def get_cog(self, name: str) -> "Cog | None":  # type: ignore[name-defined]
        """Return the first loaded cog whose class name or configured name matches."""
        from .cog import Cog

        for plugin in self._plugins:
            if isinstance(plugin, Cog) and (
                type(plugin).__name__ == name or getattr(plugin, "name", None) == name
            ):
                return plugin
        return None

    @property
    def cogs(self) -> dict[str, "Cog"]:  # type: ignore[name-defined]
        """Mapping of loaded cog names to instances."""
        from .cog import Cog

        return {
            getattr(cog, "qualified_name", type(cog).__name__): cog
            for cog in self._plugins
            if isinstance(cog, Cog)
        }

    async def remove_cog(self, cog: str | "Cog") -> None:  # type: ignore[name-defined]
        """Remove a loaded cog by name or instance."""
        from .cog import Cog

        if isinstance(cog, str):
            target = self.get_cog(cog)
            if target is None:
                raise ValueError(f"No cog named {cog!r} is loaded")
            await self.remove_plugin(target)
            return
        if not isinstance(cog, Cog):
            raise TypeError(f"expected a Cog instance or cog name, got {type(cog).__name__!r}")
        await self.remove_plugin(cog)

    def register_endpoint(
        self,
        name: str,
        func: Callable,
        *,
        source_plugin: str | None = None,
    ) -> None:
        """Register a reusable named endpoint callable."""
        if not callable(func):
            raise TypeError(
                f"endpoint must be callable, got {type(func).__name__!r}"
            )
        if name in self._endpoints:
            existing = self._endpoints[name]
            raise ValueError(
                f"Endpoint {name!r} already registered by "
                f"{existing.get('plugin') or 'Bot'}"
            )
        self._endpoints[name] = {"func": func, "plugin": source_plugin}
        self._track_extension_endpoint(name)

    def endpoint(self, name: str | Callable | None = None) -> Callable:
        """Decorator that registers a reusable named endpoint."""
        if callable(name):
            func = name
            self.register_endpoint(func.__name__, func)
            return func

        def decorator(func: Callable) -> Callable:
            self.register_endpoint(name or func.__name__, func)
            return func

        return decorator

    def get_endpoint(self, name: str) -> Callable | None:
        """Return a named endpoint callable if one is registered."""
        entry = self._endpoints.get(name)
        return entry["func"] if entry else None

    def require_endpoint(self, name: str) -> Callable:
        """Return a named endpoint or raise if it is missing."""
        endpoint = self.get_endpoint(name)
        if endpoint is None:
            raise ValueError(f"No endpoint named {name!r} is registered")
        return endpoint

    async def call_endpoint(self, name: str, /, *args, **kwargs):
        """Call a registered endpoint and await the result if needed."""
        endpoint = self.require_endpoint(name)
        result = endpoint(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def remove_plugin(self, plugin: Plugin) -> None:
        """Remove a plugin, deregistering its commands and event handlers.

        Raises ``ValueError`` if the plugin was never added.
        """
        if plugin not in self._plugins:
            raise ValueError(
                f"{type(plugin).__name__} has not been added to this bot. "
                "Call bot.add_plugin() before trying to remove it."
            )
        self._plugins.remove(plugin)
        for _, method in inspect.getmembers(plugin, predicate=inspect.ismethod):
            if getattr(method, "_is_slash", False):
                guild = (
                    discord.Object(id=method._slash_guild)
                    if method._slash_guild
                    else None
                )
                for cmd_name in [method._slash_name] + list(getattr(method, "_slash_aliases", [])):
                    try:
                        self.tree.remove_command(cmd_name, guild=guild)
                    except Exception:  # noqa: BLE001
                        logger.debug(
                            "Could not remove command %r during unload",
                            cmd_name,
                        )
            if getattr(method, "_is_event", False):
                try:
                    self._event_handlers[method._event_name].remove(method)
                except (KeyError, ValueError):
                    pass
            if getattr(method, "_is_user_command", False):
                guild = discord.Object(id=method._context_menu_guild) if method._context_menu_guild else None
                try:
                    self.tree.remove_command(method._context_menu_name, type=discord.AppCommandType.user, guild=guild)
                except Exception:
                    pass
            if getattr(method, "_is_message_command", False):
                guild = discord.Object(id=method._context_menu_guild) if method._context_menu_guild else None
                try:
                    self.tree.remove_command(method._context_menu_name, type=discord.AppCommandType.message, guild=guild)
                except Exception:
                    pass
            if getattr(method, "_is_component", False):
                custom_id = method._component_id
                if getattr(method, "_component_scoped", True):
                    custom_id = plugin.id(custom_id)
                self.registry.components.pop(custom_id, None)
            if getattr(method, "_is_modal", False):
                custom_id = method._modal_id
                if getattr(method, "_modal_scoped", True):
                    custom_id = plugin.id(custom_id)
                self.registry.modals.pop(custom_id, None)
            if getattr(method, "_is_endpoint", False):
                self._endpoints.pop(method._endpoint_name, None)
        for handle in self._task_handles.pop(id(plugin), []):
            handle.cancel()
            try:
                await handle
            except asyncio.CancelledError:
                pass
        await plugin.on_unload()

    def _pop_extension_items(self, name: str) -> list[Plugin]:
        return list(self._extension_additions.pop(name, []))

    async def load_extension(self, name: str) -> ModuleType:
        """Import an extension module and run its async ``setup(bot)`` hook."""
        if name in self._extensions:
            raise ValueError(f"Extension {name!r} is already loaded")
        module = importlib.import_module(name)
        setup = getattr(module, "setup", None)
        if setup is None:
            raise ValueError(f"Extension {name!r} does not define setup(bot)")

        self._active_extension = name
        self._extension_additions.setdefault(name, [])
        try:
            result = setup(self)
            if inspect.isawaitable(result):
                await result
        except Exception:
            await self._unload_extension_items(name)
            raise
        finally:
            self._active_extension = None

        self._extensions[name] = module
        return module

    async def unload_extension(self, name: str) -> None:
        """Unload an extension and remove anything it registered through bot helpers."""
        module = self._extensions.pop(name, None)
        if module is None:
            raise ValueError(f"Extension {name!r} is not loaded")
        await self._unload_extension_items(name)
        teardown = getattr(module, "teardown", None)
        if teardown is not None:
            result = teardown(self)
            if inspect.isawaitable(result):
                await result

    async def reload_extension(self, name: str) -> ModuleType:
        """Reload an extension in place."""
        await self.unload_extension(name)
        return await self.load_extension(name)

    async def _unload_extension_items(self, name: str) -> None:
        for item in reversed(self._pop_extension_items(name)):
            if item in self._plugins:
                await self.remove_plugin(item)
        for endpoint_name in self._extension_endpoints.pop(name, []):
            self._endpoints.pop(endpoint_name, None)

    async def reload_plugin(self, name: str) -> None:
        """Reload a plugin by class name — calls ``on_unload`` then ``on_load`` in-place.

        The same instance is kept, so constructor arguments and in-memory state
        are preserved. Raises ``ValueError`` if no loaded plugin has that class name.
        """
        for plugin in self._plugins:
            if type(plugin).__name__ == name:
                await plugin.on_unload()
                await plugin.on_load()
                return
        raise ValueError(f"No plugin named {name!r} is loaded")

    # ── Background tasks ──────────────────────────────────────

    def _start_plugin_tasks(self, plugin: Plugin) -> None:
        """Start all @task-decorated methods for a plugin."""
        handles = []
        for _, method in inspect.getmembers(plugin, predicate=inspect.ismethod):
            if getattr(method, "_is_task", False):
                handle = asyncio.create_task(
                    self._run_task(method, method._task_interval)
                )
                handles.append(handle)
        if handles:
            self._task_handles[id(plugin)] = handles

    @staticmethod
    async def _run_task(method: Callable, interval: float) -> None:
        """Run a plugin task method in a loop, sleeping between calls."""
        while True:
            try:
                await method()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Error in task %r", getattr(method, "__name__", method)
                )
            await asyncio.sleep(interval)
