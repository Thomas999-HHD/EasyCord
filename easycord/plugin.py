from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bot import EasyCord


class Plugin:
    """Base class for EasyCord plugins.

    Subclass this to group related slash commands and event handlers
    into a self-contained, reloadable unit.
    """

    def __init__(self) -> None:
        self._bot: EasyCord | None = None

    @property
    def bot(self) -> EasyCord:
        if self._bot is None:
            raise RuntimeError("Plugin has not been loaded into a bot yet.")
        return self._bot

    async def on_load(self) -> None:
        """Called once when the plugin is loaded into a bot."""

    async def on_unload(self) -> None:
        """Called once when the plugin is unloaded from a bot."""
