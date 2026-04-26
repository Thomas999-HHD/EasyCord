"""Role blueprint system — declarative, typed, versioned."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import discord


@dataclass
class RolePermission:
    """Single permission (allow/deny) in a role."""

    name: str  # "ban_members", "kick_members", etc.
    grant: bool = True  # True = allow, False = deny

    def to_bits(self) -> tuple[int, int]:
        """Return (allow_bits, deny_bits) for this permission."""
        if not hasattr(discord.Permissions.all(), self.name):
            raise ValueError(f"Unknown permission: {self.name}")
        perm_value = getattr(discord.Permissions.all(), self.name)
        if self.grant:
            return (int(perm_value), 0)
        return (0, int(perm_value))


@dataclass
class RoleBlueprint:
    """Source of truth for a single role definition."""

    name: str  # Discord role name
    permissions: list[str] = field(default_factory=list)  # ["ban_members", "kick_members"]
    color: int | None = None  # Discord color value (0xRRGGBB)
    hoist: bool = False  # Displayed separately in member list
    mentionable: bool = False  # Can be mentioned by @
    position: Literal["top", "high", "mid", "low", "bottom"] | None = None
    inherits: str | None = None  # Inherit permissions from another blueprint
    deny_permissions: list[str] = field(default_factory=list)  # Explicit denies
    icon: str | None = None  # Icon URL (emoji for now)

    def compute_permissions(self, blueprints: dict[str, RoleBlueprint]) -> discord.Permissions:
        """Compute final permissions after inheritance."""
        allow_bits = 0

        # Inherit parent permissions first
        if self.inherits:
            parent = blueprints.get(self.inherits)
            if parent is None:
                raise ValueError(f"Role {self.name} inherits from unknown role {self.inherits}")
            parent_perms = parent.compute_permissions(blueprints)
            allow_bits |= parent_perms.value

        # Apply allows
        for perm_name in self.permissions:
            if not hasattr(discord.Permissions.all(), perm_name):
                raise ValueError(f"Unknown permission: {perm_name}")
            perm_obj = discord.Permissions(**{perm_name: True})
            allow_bits |= perm_obj.value

        # Apply denies (override allows)
        for perm_name in self.deny_permissions:
            if not hasattr(discord.Permissions.all(), perm_name):
                raise ValueError(f"Unknown permission: {perm_name}")
            perm_obj = discord.Permissions(**{perm_name: True})
            # Remove from allows
            allow_bits &= ~perm_obj.value

        return discord.Permissions(allow_bits)

    def validate(self, blueprints: dict[str, RoleBlueprint]) -> None:
        """Validate blueprint for errors."""
        if not self.name:
            raise ValueError("Role name cannot be empty")
        if len(self.name) > 100:
            raise ValueError("Role name must be <= 100 chars")

        # Validate all permission names
        for perm in self.permissions + self.deny_permissions:
            if not hasattr(discord.Permissions.all(), perm):
                raise ValueError(f"Unknown permission: {perm}")

        # Validate inheritance
        if self.inherits and self.inherits not in blueprints:
            raise ValueError(f"Unknown parent role: {self.inherits}")

        # Validate no inheritance cycles
        visited = set()
        current = self.inherits
        while current:
            if current in visited:
                raise ValueError(f"Circular inheritance detected: {self.name}")
            visited.add(current)
            parent = blueprints.get(current)
            current = parent.inherits if parent else None


@dataclass
class BlueprintSet:
    """Complete set of role blueprints for a guild."""

    guild_id: int
    version: str = "1.0"  # Schema version
    blueprints: dict[str, RoleBlueprint] = field(default_factory=dict)

    def validate_all(self) -> list[str]:
        """Validate all blueprints. Return list of errors."""
        errors = []
        for key, blueprint in self.blueprints.items():
            try:
                blueprint.validate(self.blueprints)
            except ValueError as e:
                errors.append(f"{key}: {e}")
        return errors

    @staticmethod
    def from_dict(guild_id: int, data: dict) -> BlueprintSet:
        """Parse BlueprintSet from dict (from JSON/config)."""
        if not isinstance(data, dict):
            raise ValueError("Blueprint data must be a dict")

        blueprints: dict[str, RoleBlueprint] = {}
        for key, role_data in data.get("blueprints", {}).items():
            if not isinstance(role_data, dict):
                raise ValueError(f"Blueprint {key} must be a dict")

            blueprints[key] = RoleBlueprint(
                name=role_data.get("name", key),
                permissions=role_data.get("permissions", []),
                color=role_data.get("color"),
                hoist=role_data.get("hoist", False),
                mentionable=role_data.get("mentionable", False),
                position=role_data.get("position"),
                inherits=role_data.get("inherits"),
                deny_permissions=role_data.get("deny_permissions", []),
                icon=role_data.get("icon"),
            )

        bp_set = BlueprintSet(
            guild_id=guild_id,
            version=data.get("version", "1.0"),
            blueprints=blueprints,
        )

        errors = bp_set.validate_all()
        if errors:
            raise ValueError(f"Blueprint validation failed: {'; '.join(errors)}")

        return bp_set

    def to_dict(self) -> dict:
        """Serialize to dict for storage."""
        return {
            "version": self.version,
            "blueprints": {
                key: {
                    "name": bp.name,
                    "permissions": bp.permissions,
                    "deny_permissions": bp.deny_permissions,
                    "color": bp.color,
                    "hoist": bp.hoist,
                    "mentionable": bp.mentionable,
                    "position": bp.position,
                    "inherits": bp.inherits,
                    "icon": bp.icon,
                }
                for key, bp in self.blueprints.items()
            },
        }
