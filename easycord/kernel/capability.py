"""Declarative capability system. Maps Discord permissions + plugin grants to features.

Usage:
    @slash(
        description="Ban user",
        capabilities=["ban_members"]
    )
    async def ban_cmd(ctx, user):
        ...

Capabilities resolved against:
1. Discord guild member permissions (fail-closed)
2. Plugin runtime grants (opt-in)
3. Explicit overrides (for testing)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Set

import discord


class CapabilityError(Exception):
    """Raised when capability check fails."""

    pass


@dataclass
class Capability:
    """Represents a required permission or capability.

    Attributes
    ----------
    name : str
        Capability name (e.g., "ban_members", "send_messages")
    discord_perm : str, optional
        Corresponding Discord permission name (e.g., "ban_members")
    description : str
        Human-readable description
    """

    name: str
    discord_perm: Optional[str] = None
    description: str = ""

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Capability):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return False


class CapabilityRegistry:
    """Resolves capabilities at runtime against Discord perms + plugin grants."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._plugin_grants: dict[str, Set[str]] = {}
        self._overrides: dict[str, bool] = {}

    def define(
        self, name: str, discord_perm: Optional[str] = None, description: str = ""
    ) -> Capability:
        """Register a capability."""
        cap = Capability(name=name, discord_perm=discord_perm, description=description)
        self._capabilities[name] = cap
        return cap

    def grant(self, plugin_name: str, *capabilities: str) -> None:
        """Grant capabilities to a plugin at runtime."""
        if plugin_name not in self._plugin_grants:
            self._plugin_grants[plugin_name] = set()
        self._plugin_grants[plugin_name].update(capabilities)

    def revoke(self, plugin_name: str, *capabilities: str) -> None:
        """Revoke capabilities from a plugin."""
        if plugin_name in self._plugin_grants:
            self._plugin_grants[plugin_name].difference_update(capabilities)

    def override(self, capability: str, allow: bool) -> None:
        """Override capability check (for testing)."""
        self._overrides[capability] = allow

    def check(
        self,
        ctx: discord.Interaction | discord.Member | None,
        *capabilities: str,
        plugin_name: Optional[str] = None,
    ) -> bool:
        """Check if capabilities are granted.

        Parameters
        ----------
        ctx : discord.Interaction | discord.Member, optional
            Interaction or member to check permissions for
        *capabilities : str
            Capability names to verify
        plugin_name : str, optional
            Plugin requesting capabilities (for grants)

        Returns
        -------
        bool
            True if all capabilities granted, False otherwise
        """
        if not capabilities:
            return True

        for cap_name in capabilities:
            # Check overrides first (for testing)
            if cap_name in self._overrides:
                if not self._overrides[cap_name]:
                    return False
                continue

            # Check plugin grants
            if plugin_name and plugin_name in self._plugin_grants:
                if cap_name in self._plugin_grants[plugin_name]:
                    continue

            # Check Discord permissions
            cap = self._capabilities.get(cap_name)
            if cap and cap.discord_perm and ctx:
                # Extract member from interaction
                member = ctx.user if isinstance(ctx, discord.Interaction) else ctx

                if isinstance(member, discord.Member):
                    if member.guild_permissions.value & (
                        1 << self._perm_to_bit(cap.discord_perm)
                    ):
                        continue

            # No grant found
            return False

        return True

    async def check_async(
        self,
        ctx: discord.Interaction | discord.Member | None,
        *capabilities: str,
        plugin_name: Optional[str] = None,
    ) -> bool:
        """Async version of check (for future DB lookups)."""
        return self.check(ctx, *capabilities, plugin_name=plugin_name)

    def _perm_to_bit(self, perm_name: str) -> int:
        """Convert permission name to Discord permission bit."""
        # Map of permission names to bit positions
        perm_bits = {
            "create_instant_invite": 0,
            "kick_members": 1,
            "ban_members": 2,
            "administrator": 3,
            "manage_channels": 4,
            "manage_guild": 5,
            "add_reactions": 6,
            "view_audit_log": 7,
            "priority_speaker": 8,
            "stream": 9,
            "view_channel": 10,
            "send_messages": 11,
            "send_tts_messages": 12,
            "manage_messages": 13,
            "embed_links": 14,
            "attach_files": 15,
            "read_message_history": 16,
            "mention_everyone": 17,
            "use_external_emojis": 18,
            "view_guild_insights": 19,
            "connect": 20,
            "speak": 21,
            "mute_members": 22,
            "deafen_members": 23,
            "move_members": 24,
            "use_voice_activation": 25,
            "change_nickname": 26,
            "manage_nicknames": 27,
            "manage_roles": 28,
            "manage_webhooks": 29,
            "manage_guild_expressions": 30,
            "use_application_commands": 31,
            "request_to_speak": 32,
            "manage_events": 33,
            "manage_threads": 34,
            "create_public_threads": 35,
            "create_private_threads": 36,
            "use_external_stickers": 37,
            "send_messages_in_threads": 38,
            "use_embedded_activities": 39,
            "moderate_members": 40,
        }
        return perm_bits.get(perm_name, 0)
