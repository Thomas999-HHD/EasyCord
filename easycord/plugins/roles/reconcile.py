"""Reconciliation engine — apply changes idempotently."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import discord

from .diff import ChangeType, DiffResult, RoleDiff

logger = logging.getLogger("easycord.roles")


@dataclass
class ReconcileResult:
    """Result of reconciliation."""

    success: bool
    changes_applied: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ReconciliationEngine:
    """Apply role changes to Discord."""

    async def apply_diff(
        self,
        guild: discord.Guild,
        diff_result: DiffResult,
        dry_run: bool = False,
    ) -> ReconcileResult:
        """Apply all changes in diff to Discord.

        dry_run: if True, return what would be done without applying
        """
        result = ReconcileResult(success=True)

        # Sort by change type: creates first, updates, deletes last
        sorted_changes = sorted(
            diff_result.changes,
            key=lambda d: {
                ChangeType.CREATE: 0,
                ChangeType.UPDATE_PERMS: 1,
                ChangeType.UPDATE_COLOR: 2,
                ChangeType.UPDATE_HOIST: 3,
                ChangeType.UPDATE_MENTIONABLE: 4,
                ChangeType.UPDATE_NAME: 5,
                ChangeType.DELETE: 6,
            }.get(d.change_type, 99),
        )

        for diff in sorted_changes:
            try:
                if dry_run:
                    logger.info(f"[DRY-RUN] Would {diff.change_type.value}: {diff.role_name}")
                    result.changes_applied += 1
                else:
                    await self._apply_single(guild, diff, diff_result)
                    result.changes_applied += 1
            except Exception as e:
                result.success = False
                msg = f"Failed to {diff.change_type.value} {diff.role_name}: {e}"
                logger.error(msg)
                result.errors.append(msg)

        return result

    async def _apply_single(self, guild: discord.Guild, diff: RoleDiff, diff_result: DiffResult) -> None:
        """Apply single role change."""
        if diff.change_type == ChangeType.CREATE:
            await self._create_role(guild, diff, diff_result)
        elif diff.change_type == ChangeType.UPDATE_PERMS:
            await self._update_permissions(guild, diff, diff_result)
        elif diff.change_type == ChangeType.UPDATE_COLOR:
            await self._update_color(guild, diff)
        elif diff.change_type == ChangeType.UPDATE_HOIST:
            await self._update_hoist(guild, diff)
        elif diff.change_type == ChangeType.UPDATE_MENTIONABLE:
            await self._update_mentionable(guild, diff)
        elif diff.change_type == ChangeType.DELETE:
            await self._delete_role(guild, diff)

    async def _create_role(self, guild: discord.Guild, diff: RoleDiff, diff_result: DiffResult) -> None:
        """Create new role."""
        bp = diff.blueprint
        perms = bp.compute_permissions(diff_result.blueprint_set.blueprints)
        color = discord.Color(bp.color) if bp.color else discord.Color.default()

        logger.info(f"Creating role: {bp.name}")
        role = await guild.create_role(
            name=bp.name,
            permissions=perms,
            color=color,
            hoist=bp.hoist,
            mentionable=bp.mentionable,
        )

        logger.debug(f"Created role {role.name} (ID: {role.id})")

    async def _update_permissions(
        self,
        guild: discord.Guild,
        diff: RoleDiff,
        diff_result: DiffResult,
    ) -> None:
        """Update role permissions."""
        if not diff.discord_role:
            raise ValueError(f"Role {diff.role_name} not found for update")

        bp = diff.blueprint
        perms = bp.compute_permissions(diff_result.blueprint_set.blueprints)

        logger.info(f"Updating permissions for role: {diff.role_name}")
        await diff.discord_role.edit(permissions=perms)

    async def _update_color(self, guild: discord.Guild, diff: RoleDiff) -> None:
        """Update role color."""
        if not diff.discord_role:
            raise ValueError(f"Role {diff.role_name} not found for update")

        color = discord.Color(diff.blueprint.color) if diff.blueprint.color else discord.Color.default()
        logger.info(f"Updating color for role: {diff.role_name}")
        await diff.discord_role.edit(color=color)

    async def _update_hoist(self, guild: discord.Guild, diff: RoleDiff) -> None:
        """Update role hoist (separate in list)."""
        if not diff.discord_role:
            raise ValueError(f"Role {diff.role_name} not found for update")

        logger.info(f"Updating hoist for role: {diff.role_name}")
        await diff.discord_role.edit(hoist=diff.blueprint.hoist)

    async def _update_mentionable(self, guild: discord.Guild, diff: RoleDiff) -> None:
        """Update role mentionable."""
        if not diff.discord_role:
            raise ValueError(f"Role {diff.role_name} not found for update")

        logger.info(f"Updating mentionable for role: {diff.role_name}")
        await diff.discord_role.edit(mentionable=diff.blueprint.mentionable)

    async def _delete_role(self, guild: discord.Guild, diff: RoleDiff) -> None:
        """Delete role."""
        if not diff.discord_role:
            raise ValueError(f"Role {diff.role_name} not found for deletion")

        logger.info(f"Deleting role: {diff.role_name}")
        await diff.discord_role.delete()
