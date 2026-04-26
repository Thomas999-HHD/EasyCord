"""Typed storage for role blueprints using ServerConfigStore."""
from __future__ import annotations

import json
import logging

from easycord.server_config import ServerConfig, ServerConfigStore

from .blueprint import BlueprintSet

logger = logging.getLogger("easycord.roles")


class RoleStorage:
    """Wrapper around ServerConfigStore for role blueprint persistence."""

    def __init__(self, config_store: ServerConfigStore):
        self.store = config_store

    async def load_blueprints(self, guild_id: int) -> BlueprintSet | None:
        """Load role blueprints for a guild. Return None if not configured."""
        config = await self.store.load(guild_id)
        blueprint_data = config.get_other("roles:blueprints")

        if not blueprint_data:
            return None

        try:
            return BlueprintSet.from_dict(guild_id, blueprint_data)
        except ValueError as e:
            logger.error(f"Failed to load blueprints for guild {guild_id}: {e}")
            return None

    async def save_blueprints(self, blueprint_set: BlueprintSet) -> None:
        """Save role blueprints for a guild."""
        config = await self.store.load(blueprint_set.guild_id)
        config.set_other("roles:blueprints", blueprint_set.to_dict())
        config.set_other("roles:blueprint_version", blueprint_set.version)
        await self.store.save(config)

    async def load_role_ids(self, guild_id: int) -> dict[str, int]:
        """Load stored role ID mappings (blueprint_key -> discord_role_id)."""
        config = await self.store.load(guild_id)
        role_ids = config.get_other("roles:role_ids", {})

        if not isinstance(role_ids, dict):
            return {}

        return {k: int(v) for k, v in role_ids.items() if isinstance(v, (int, str))}

    async def save_role_ids(self, guild_id: int, role_ids: dict[str, int]) -> None:
        """Save role ID mappings."""
        config = await self.store.load(guild_id)
        config.set_other("roles:role_ids", role_ids)
        await self.store.save(config)

    async def set_role_id(self, guild_id: int, blueprint_key: str, role_id: int) -> None:
        """Store a single role ID mapping."""
        role_ids = await self.load_role_ids(guild_id)
        role_ids[blueprint_key] = role_id
        await self.save_role_ids(guild_id, role_ids)

    async def delete_role_id(self, guild_id: int, blueprint_key: str) -> None:
        """Remove a role ID mapping."""
        role_ids = await self.load_role_ids(guild_id)
        role_ids.pop(blueprint_key, None)
        await self.save_role_ids(guild_id, role_ids)

    async def get_sync_history(self, guild_id: int) -> dict:
        """Load last sync info (timestamp, changes, etc.)."""
        config = await self.store.load(guild_id)
        return config.get_other("roles:sync_history", {})

    async def save_sync_history(self, guild_id: int, history: dict) -> None:
        """Save sync history."""
        config = await self.store.load(guild_id)
        config.set_other("roles:sync_history", history)
        await self.store.save(config)
