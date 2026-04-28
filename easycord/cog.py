from __future__ import annotations

import inspect
from typing import Callable, Iterable

from .group import SlashGroup
from .plugin import Plugin


def _infer_listener_name(func: Callable) -> str:
    name = func.__name__
    return name[3:] if name.startswith("on_") else name


class _CogInspectionMixin:
    """Shared inspection helpers for Cog-like classes."""

    @staticmethod
    def listener(name: str | None = None) -> Callable:
        """Mark a method as a cog listener.

        Supports both ``@Cog.listener("message")`` and bare ``@Cog.listener``.
        Bare usage infers the event name from the method name and strips ``on_``
        when present, matching the common discord.py style.
        """
        if callable(name):
            func = name
            func._is_event = True
            func._event_name = _infer_listener_name(func)
            return func

        def decorator(func: Callable) -> Callable:
            func._is_event = True
            func._event_name = name or _infer_listener_name(func)
            return func

        return decorator

    @property
    def qualified_name(self) -> str:
        return getattr(self, "name", self.__class__.__name__)

    def _iter_methods(self) -> Iterable[tuple[str, Callable]]:
        for name, func in inspect.getmembers(type(self), predicate=inspect.isfunction):
            yield name, getattr(self, name)

    def get_commands(self) -> list[Callable]:
        """Return slash-command methods defined on the cog."""
        return [method for _, method in self._iter_methods() if getattr(method, "_is_slash", False)]

    def walk_commands(self):
        """Yield slash-command methods defined on the cog."""
        yield from self.get_commands()

    def get_app_commands(self) -> list[Callable]:
        """Return slash and context-menu methods defined on the cog."""
        return [
            method
            for _, method in self._iter_methods()
            if getattr(method, "_is_slash", False)
            or getattr(method, "_is_user_command", False)
            or getattr(method, "_is_message_command", False)
        ]

    def walk_app_commands(self):
        """Yield slash and context-menu methods defined on the cog."""
        yield from self.get_app_commands()

    def get_listeners(self) -> list[tuple[str, Callable]]:
        """Return ``(event_name, method)`` pairs for registered listeners."""
        return [
            (method._event_name, method)
            for _, method in self._iter_methods()
            if getattr(method, "_is_event", False)
        ]

    async def cog_load(self) -> None:  # pragma: no cover - default hook
        """Lifecycle hook that runs after the cog is added."""

    async def cog_unload(self) -> None:  # pragma: no cover - default hook
        """Lifecycle hook that runs before the cog is removed."""


class Cog(_CogInspectionMixin, Plugin):
    """discord.py-style grouping for commands, listeners, and state.

    Cogs are the parity-friendly layer over :class:`~easycord.plugin.Plugin`.
    Use them when you want a class-based container for commands plus listeners.
    """

    def __init__(self) -> None:
        super().__init__()
        if self.name == self.__class__.__name__.lower():
            self.name = self.__class__.__name__


class GroupCog(Cog, SlashGroup):
    """A cog that also acts as a slash command group namespace."""
