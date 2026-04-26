"""Public API for role operations — other plugins use this."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from .plugin import RolesPlugin

logger = logging.getLogger("easycord.roles")


class RolesAPI:
    """Public interface for role operations."""

    def __init__(self, plugin: RolesPlugin):
        self.plugin = plugin

    async def assign(self, user_id: int, guild_id: int, role_key: str) -> bool:
        """Assign a templated role to a user.

        role_key: blueprint key (e.g., "moderator")
        return: True if successful
        """
        try:
            guild = self.plugin.bot.get_guild(guild_id)
            if not guild:
                logger.warning(f"Guild {guild_id} not found")
                return False

            member = await guild.fetch_member(user_id)
            if not member:
                logger.warning(f"Member {user_id} not found in guild {guild_id}")
                return False

            role_ids = await self.plugin.storage.load_role_ids(guild_id)
            role_id = role_ids.get(role_key)

            if not role_id:
                logger.warning(f"Role {role_key} not found in blueprint")
                return False

            role = guild.get_role(role_id)
            if not role:
                logger.warning(f"Discord role {role_id} not found")
                return False

            await member.add_roles(role)
            logger.info(f"Assigned role {role_key} to {member} in {guild.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to assign role {role_key} to {user_id}: {e}")
            return False

    async def remove(self, user_id: int, guild_id: int, role_key: str) -> bool:
        """Remove a templated role from a user.

        return: True if successful
        """
        try:
            guild = self.plugin.bot.get_guild(guild_id)
            if not guild:
                return False

            member = await guild.fetch_member(user_id)
            if not member:
                return False

            role_ids = await self.plugin.storage.load_role_ids(guild_id)
            role_id = role_ids.get(role_key)

            if not role_id:
                return False

            role = guild.get_role(role_id)
            if not role:
                return False

            await member.remove_roles(role)
            logger.info(f"Removed role {role_key} from {member} in {guild.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove role {role_key} from {user_id}: {e}")
            return False

    async def has(self, user_id: int, guild_id: int, role_key: str) -> bool:
        """Check if user has a role."""
        try:
            guild = self.plugin.bot.get_guild(guild_id)
            if not guild:
                return False

            member = await guild.fetch_member(user_id)
            if not member:
                return False

            role_ids = await self.plugin.storage.load_role_ids(guild_id)
            role_id = role_ids.get(role_key)

            if not role_id:
                return False

            return any(r.id == role_id for r in member.roles)

        except Exception as e:
            logger.error(f"Failed to check role {role_key} for {user_id}: {e}")
            return False

    async def get_role(self, guild_id: int, role_key: str) -> discord.Role | None:
        """Get Discord role object for a blueprint key."""
        try:
            guild = self.plugin.bot.get_guild(guild_id)
            if not guild:
                return None

            role_ids = await self.plugin.storage.load_role_ids(guild_id)
            role_id = role_ids.get(role_key)

            if not role_id:
                return None

            return guild.get_role(role_id)

        except Exception as e:
            logger.error(f"Failed to get role {role_key}: {e}")
            return None

    async def list_roles(self, guild_id: int) -> dict[str, discord.Role]:
        """Get all managed roles for a guild.

        return: dict of blueprint_key -> discord.Role
        """
        try:
            guild = self.plugin.bot.get_guild(guild_id)
            if not guild:
                return {}

            role_ids = await self.plugin.storage.load_role_ids(guild_id)
            result = {}

            for key, role_id in role_ids.items():
                role = guild.get_role(role_id)
                if role:
                    result[key] = role

            return result

        except Exception as e:
            logger.error(f"Failed to list roles for guild {guild_id}: {e}")
            return {}
