"""Policy engine — enforce safety rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import discord

from .diff import ChangeType, DiffResult, RoleDiff


@dataclass
class PolicyConfig:
    """Safety and behavior rules."""

    prevent_self_escalation: bool = True  # Cmd author can't give themselves higher perms
    protect_admin_role: bool = True  # Prevent modifying admin role
    prevent_dangerous_perms: bool = True  # Prevent administrator, ban all members, etc.
    require_reason: bool = False  # Require reason text for changes (future)
    max_roles_per_user: int | None = None  # Limit total roles per member
    audit_log: bool = True  # Emit audit events


@dataclass
class PolicyViolation:
    """Single policy violation."""

    code: str  # "self_escalation", "protect_admin", etc.
    message: str  # Human-readable reason
    severity: Literal["warn", "error"] = "error"
    diff: RoleDiff | None = None  # The change that violated policy


class PolicyEngine:
    """Enforce safety rules before applying changes."""

    def __init__(self, config: PolicyConfig | None = None):
        self.config = config or PolicyConfig()

    async def validate(
        self,
        guild: discord.Guild,
        diff_result: DiffResult,
        author: discord.Member | None = None,
    ) -> list[PolicyViolation]:
        """Check if changes violate policy. Return list of violations."""
        violations: list[PolicyViolation] = []

        for diff in diff_result.changes:
            v = self._check_diff(guild, diff, author)
            violations.extend(v)

        return violations

    def _check_diff(
        self,
        guild: discord.Guild,
        diff: RoleDiff,
        author: discord.Member | None,
    ) -> list[PolicyViolation]:
        """Check single diff for violations."""
        violations: list[PolicyViolation] = []

        # Prevent dangerous permissions (administrator)
        if self.config.prevent_dangerous_perms:
            if diff.change_type in (ChangeType.CREATE, ChangeType.UPDATE_PERMS):
                # Create empty dict for compute_permissions (since we don't have blueprint_set here)
                perms = diff.blueprint.compute_permissions({diff.blueprint.name: diff.blueprint})
                if perms.administrator:
                    violations.append(
                        PolicyViolation(
                            code="dangerous_perm",
                            message=f"Role {diff.role_name} has 'administrator' permission (prevented)",
                            severity="error",
                            diff=diff,
                        )
                    )

        # Protect admin roles
        if self.config.protect_admin_role and diff.blueprint.name.lower() in (
            "admin",
            "administrator",
        ):
            violations.append(
                PolicyViolation(
                    code="protect_admin",
                    message=f"Cannot modify admin role {diff.role_name}",
                    severity="warn",
                    diff=diff,
                )
            )

        # Prevent self-escalation (author giving themselves higher perms)
        if self.config.prevent_self_escalation and author:
            if diff.change_type == ChangeType.UPDATE_PERMS and diff.discord_role:
                # If author has this role and we're elevating perms
                if diff.discord_role in author.roles:
                    current_perms = diff.discord_role.permissions
                    desired_perms = diff.blueprint.compute_permissions(diff.blueprint_set.blueprints)
                    if desired_perms.value > current_perms.value:
                        violations.append(
                            PolicyViolation(
                                code="self_escalation",
                                message=f"Cannot escalate your own role {diff.role_name}",
                                severity="error",
                                diff=diff,
                            )
                        )

        return violations
