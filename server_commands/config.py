"""
server_commands/config.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Per-guild configuration store for EasyCord bots.

Usage:
    from server_commands.config import ServerConfigStore

    store = ServerConfigStore()

    cfg = await store.load(guild_id)
    cfg.set_role("moderator", 1234567890)
    cfg.set_channel("logs", 9876543210)
    cfg.set_other("prefix", "!")
    await store.save(cfg)
"""

import json
import os
from pathlib import Path


class ServerConfig:
    """Holds configuration for a single guild."""

    def __init__(self, guild_id: int, data: dict | None = None):
        self.guild_id = guild_id
        self._data: dict = data or {"roles": {}, "channels": {}, "other": {}}

    # ── Roles ────────────────────────────────────────────────

    def set_role(self, key: str, role_id: int) -> None:
        self._data["roles"][key] = role_id

    def get_role(self, key: str) -> int | None:
        return self._data["roles"].get(key)

    def remove_role(self, key: str) -> None:
        self._data["roles"].pop(key, None)

    # ── Channels ─────────────────────────────────────────────

    def set_channel(self, key: str, channel_id: int) -> None:
        self._data["channels"][key] = channel_id

    def get_channel(self, key: str) -> int | None:
        return self._data["channels"].get(key)

    def remove_channel(self, key: str) -> None:
        self._data["channels"].pop(key, None)

    # ── Other / feature flags ────────────────────────────────

    def set_other(self, key: str, value) -> None:
        self._data["other"][key] = value

    def get_other(self, key: str, default=None):
        return self._data["other"].get(key, default)

    def remove_other(self, key: str) -> None:
        self._data["other"].pop(key, None)

    def to_dict(self) -> dict:
        return self._data


class ServerConfigStore:
    """
    Loads and saves per-guild config as JSON files under .easycord/server-config/.

    Files are named <guild_id>.json.
    """

    def __init__(self, base_dir: str = ".easycord/server-config"):
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, guild_id: int) -> Path:
        return self._base / f"{guild_id}.json"

    async def load(self, guild_id: int) -> ServerConfig:
        """Load config for a guild, returning an empty config if none exists."""
        path = self._path(guild_id)
        if not path.exists():
            return ServerConfig(guild_id)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ServerConfig(guild_id, data)
        except (json.JSONDecodeError, OSError) as e:
            raise RuntimeError(f"Failed to load config for guild {guild_id}: {e}") from e

    async def save(self, config: ServerConfig) -> None:
        """Persist a guild's config to disk."""
        path = self._path(config.guild_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config.to_dict(), f, indent=2)
        except OSError as e:
            raise RuntimeError(f"Failed to save config for guild {config.guild_id}: {e}") from e

    async def delete(self, guild_id: int) -> None:
        """Remove a guild's config file entirely."""
        path = self._path(guild_id)
        if path.exists():
            os.remove(path)

    async def exists(self, guild_id: int) -> bool:
        return self._path(guild_id).exists()
