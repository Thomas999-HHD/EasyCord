"""Diff engine — compare desired vs actual role state."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import discord

from .blueprint import BlueprintSet, RoleBlueprint


class ChangeType(Enum):
    """Type of change to apply."""

    CREATE = "create"
    UPDATE_PERMS = "update_perms"
    UPDATE_COLOR = "update_color"
    UPDATE_HOIST = "update_hoist"
    UPDATE_MENTIONABLE = "update_mentionable"
    UPDATE_NAME = "update_name"
    DELETE = "delete"


@dataclass
class RoleDiff:
    """Single role change (desired vs actual)."""

    blueprint_key: str  # Key in blueprint dict
    blueprint: RoleBlueprint
    discord_role: discord.Role | None  # None if doesn't exist yet
    change_type: ChangeType
    reason: str = ""  # Human-readable reason
    details: dict = field(default_factory=dict)  # Extra context

    @property
    def role_name(self) -> str:
        return self.blueprint.name if self.blueprint else (self.discord_role.name if self.discord_role else "?")


@dataclass
class DiffResult:
    """Complete diff between desired and actual state."""

    guild_id: int
    blueprint_set: BlueprintSet
    desired_ids: dict[str, int | None] = field(default_factory=dict)  # blueprint_key -> role_id
    changes: list[RoleDiff] = field(default_factory=list)
    unmanaged_roles: list[discord.Role] = field(default_factory=list)

    def is_clean(self) -> bool:
        """True if no changes needed."""
        return len(self.changes) == 0

    def summary(self) -> str:
        """Human-readable diff summary."""
        if self.is_clean():
            return "✅ All roles in sync"

        lines = [f"Changes for guild {self.guild_id}:"]
        for diff in self.changes:
            if diff.change_type == ChangeType.CREATE:
                lines.append(f"  + CREATE {diff.role_name}")
            elif diff.change_type == ChangeType.DELETE:
                lines.append(f"  - DELETE {diff.role_name}")
            else:
                lines.append(f"  ~ {diff.change_type.value.upper()} {diff.role_name}: {diff.reason}")

        if self.unmanaged_roles:
            lines.append(f"\n⚠️  Unmanaged roles (not in blueprint):")
            for role in self.unmanaged_roles:
                lines.append(f"  - {role.name} (ID: {role.id})")

        return "\n".join(lines)


class DiffEngine:
    """Compare desired state (blueprint) to actual state (Discord)."""

    def __init__(self, bot_guild_id: int | None = None):
        """bot_guild_id: optional, to exclude bot role from unmanaged."""
        self.bot_guild_id = bot_guild_id

    async def compute_diff(
        self,
        guild: discord.Guild,
        blueprint_set: BlueprintSet,
        stored_ids: dict[str, int] | None = None,
    ) -> DiffResult:
        """Compute changes needed to match blueprint.

        stored_ids: dict of blueprint_key -> discord_role_id (for tracking)
        """
        result = DiffResult(guild_id=guild.id, blueprint_set=blueprint_set)
        stored_ids = stored_ids or {}

        # Track which Discord roles we've seen
        seen_discord_ids = set()

        # For each blueprint, find or create role
        for bp_key, bp in blueprint_set.blueprints.items():
            stored_id = stored_ids.get(bp_key)
            discord_role = None

            # Try to find by stored ID first
            if stored_id:
                discord_role = guild.get_role(stored_id)

            # Try to find by name if not in storage
            if not discord_role:
                for role in guild.roles:
                    if role.name == bp.name:
                        discord_role = role
                        break

            if discord_role:
                seen_discord_ids.add(discord_role.id)
                result.desired_ids[bp_key] = discord_role.id

                # Check if we need to update
                diffs = self._diff_role(bp, discord_role, blueprint_set)
                result.changes.extend(diffs)
            else:
                # Role doesn't exist
                result.desired_ids[bp_key] = None
                result.changes.append(
                    RoleDiff(
                        blueprint_key=bp_key,
                        blueprint=bp,
                        discord_role=None,
                        change_type=ChangeType.CREATE,
                        reason="Role does not exist",
                    )
                )

        # Find unmanaged roles (in Discord but not in blueprint)
        for role in guild.roles:
            if role.id not in seen_discord_ids and not self._is_system_role(role):
                result.unmanaged_roles.append(role)

        return result

    def _diff_role(
        self,
        blueprint: RoleBlueprint,
        discord_role: discord.Role,
        blueprint_set: BlueprintSet,
    ) -> list[RoleDiff]:
        """Compare single blueprint vs Discord role."""
        diffs: list[RoleDiff] = []

        # Check permissions
        desired_perms = blueprint.compute_permissions(blueprint_set.blueprints)
        if discord_role.permissions.value != desired_perms.value:
            diffs.append(
                RoleDiff(
                    blueprint_key=blueprint.name,
                    blueprint=blueprint,
                    discord_role=discord_role,
                    change_type=ChangeType.UPDATE_PERMS,
                    reason=f"{discord_role.permissions.value} → {desired_perms.value}",
                    details={
                        "current": discord_role.permissions.value,
                        "desired": desired_perms.value,
                    },
                )
            )

        # Check color
        current_color = discord_role.color.value if discord_role.color else 0
        desired_color = blueprint.color or 0
        if current_color != desired_color:
            diffs.append(
                RoleDiff(
                    blueprint_key=blueprint.name,
                    blueprint=blueprint,
                    discord_role=discord_role,
                    change_type=ChangeType.UPDATE_COLOR,
                    reason=f"{current_color} → {desired_color}",
                )
            )

        # Check hoist
        if discord_role.hoist != blueprint.hoist:
            diffs.append(
                RoleDiff(
                    blueprint_key=blueprint.name,
                    blueprint=blueprint,
                    discord_role=discord_role,
                    change_type=ChangeType.UPDATE_HOIST,
                    reason=f"{discord_role.hoist} → {blueprint.hoist}",
                )
            )

        # Check mentionable
        if discord_role.mentionable != blueprint.mentionable:
            diffs.append(
                RoleDiff(
                    blueprint_key=blueprint.name,
                    blueprint=blueprint,
                    discord_role=discord_role,
                    change_type=ChangeType.UPDATE_MENTIONABLE,
                    reason=f"{discord_role.mentionable} → {blueprint.mentionable}",
                )
            )

        return diffs

    def _is_system_role(self, role: discord.Role) -> bool:
        """True if role should not be managed (bot role, @everyone, etc.)."""
        if role.is_bot_managed():
            return True
        if role.is_integration():
            return True
        # @everyone role
        if role.id == role.guild.id:
            return True
        return False
