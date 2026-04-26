"""Slash commands for role management."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from easycord.api.v1 import Context

from .blueprint import BlueprintSet, RoleBlueprint

if TYPE_CHECKING:
    from .plugin import RolesPlugin

logger = logging.getLogger("easycord.roles")


class RoleCommands:
    """Slash command handlers for role management."""

    def __init__(self, plugin: RolesPlugin):
        self.plugin = plugin

    async def setup(self, ctx: Context) -> None:
        """Initialize default role blueprints for this guild."""
        await ctx.defer()

        guild = ctx.guild
        if not guild:
            await ctx.respond("❌ This command only works in servers.")
            return

        # Check if blueprints already exist
        existing = await self.plugin.storage.load_blueprints(guild.id)
        if existing:
            await ctx.respond("⚠️ Role blueprints already configured. Use `/roles reset` to start over.")
            return

        # Create default blueprint set
        blueprints: dict[str, RoleBlueprint] = {
            "bot": RoleBlueprint(
                name="Bot",
                permissions=["manage_roles", "manage_channels", "manage_messages", "send_messages"],
                hoist=True,
                mentionable=False,
            ),
            "admin": RoleBlueprint(
                name="Admin",
                permissions=["ban_members", "kick_members", "manage_messages", "moderate_members"],
                color=0xFF0000,
                hoist=True,
                mentionable=True,
            ),
            "moderator": RoleBlueprint(
                name="Moderator",
                inherits="member",
                permissions=["kick_members", "manage_messages"],
                color=0xFF6600,
                hoist=False,
            ),
            "member": RoleBlueprint(
                name="Member",
                permissions=["send_messages", "read_message_history"],
                color=0x0099FF,
                hoist=False,
            ),
        }

        bp_set = BlueprintSet(
            guild_id=guild.id,
            version="1.0",
            blueprints=blueprints,
        )

        await self.plugin.storage.save_blueprints(bp_set)

        summary = "\n".join([f"  • `{key}`: {bp.name}" for key, bp in blueprints.items()])
        await ctx.respond(
            f"""✅ Role blueprints initialized for {guild.name}:
{summary}

Use `/roles sync` to create these roles.
Use `/roles debug` to see current state."""
        )

    async def sync(self, ctx: Context) -> None:
        """Apply role blueprint changes to this guild."""
        await ctx.defer()

        guild = ctx.guild
        if not guild:
            await ctx.respond("❌ This command only works in servers.")
            return

        if not ctx.guild_id:
            await ctx.respond("❌ Guild context missing.")
            return

        # Load blueprints
        blueprint_set = await self.plugin.storage.load_blueprints(guild.id)
        if not blueprint_set:
            await ctx.respond("❌ No role blueprints configured. Use `/roles setup` first.")
            return

        # Load current role IDs
        role_ids = await self.plugin.storage.load_role_ids(guild.id)

        # Compute diff
        diff_result = await self.plugin.diff_engine.compute_diff(guild, blueprint_set, role_ids)

        # Check policies
        violations = await self.plugin.policy_engine.validate(guild, diff_result, ctx.member)

        if violations:
            violation_text = "\n".join([f"  • {v.message}" for v in violations])
            await ctx.respond(
                f"""⚠️ Policy violations prevented sync:
{violation_text}

Contact an admin if you need to override."""
            )
            return

        if diff_result.is_clean():
            await ctx.respond("✅ All roles are already in sync.")
            return

        # Apply changes
        result = await self.plugin.reconcile_engine.apply_diff(guild, diff_result)

        # Update stored role IDs
        for bp_key, role_id in diff_result.desired_ids.items():
            if role_id:
                await self.plugin.storage.set_role_id(guild.id, bp_key, role_id)

        # Emit event
        await self.plugin.bot.events.emit(
            self.plugin._event("sync", {
                "guild_id": guild.id,
                "changes_applied": result.changes_applied,
                "success": result.success,
            })
        )

        summary = diff_result.summary()
        if result.success:
            await ctx.respond(f"✅ Sync completed:\n{summary}")
        else:
            errors = "\n".join([f"  • {e}" for e in result.errors])
            await ctx.respond(f"⚠️ Sync partially failed:\n{summary}\n\nErrors:\n{errors}")

    async def simulate(self, ctx: Context) -> None:
        """Preview changes without applying them."""
        await ctx.defer()

        guild = ctx.guild
        if not guild:
            await ctx.respond("❌ This command only works in servers.")
            return

        # Load blueprints
        blueprint_set = await self.plugin.storage.load_blueprints(guild.id)
        if not blueprint_set:
            await ctx.respond("❌ No role blueprints configured.")
            return

        role_ids = await self.plugin.storage.load_role_ids(guild.id)
        diff_result = await self.plugin.diff_engine.compute_diff(guild, blueprint_set, role_ids)

        if diff_result.is_clean():
            await ctx.respond("✅ No changes needed.")
            return

        summary = diff_result.summary()
        await ctx.respond(f"""🔍 Simulation (dry-run):
{summary}

Use `/roles sync` to apply these changes.""")

    async def debug(self, ctx: Context) -> None:
        """Show current role state and blueprint."""
        await ctx.defer()

        guild = ctx.guild
        if not guild:
            await ctx.respond("❌ This command only works in servers.")
            return

        # Load blueprints
        blueprint_set = await self.plugin.storage.load_blueprints(guild.id)
        if not blueprint_set:
            await ctx.respond("No blueprints configured. Use `/roles setup`.")
            return

        role_ids = await self.plugin.storage.load_role_ids(guild.id)

        # Build debug output
        lines = ["**Managed Roles:**"]
        for bp_key, bp in blueprint_set.blueprints.items():
            role_id = role_ids.get(bp_key)
            if role_id:
                discord_role = guild.get_role(role_id)
                status = "✅" if discord_role else "❌"
                lines.append(f"  {status} `{bp_key}` → {bp.name} (ID: {role_id})")
            else:
                lines.append(f"  ⚠️ `{bp_key}` → {bp.name} (not created)")

        await ctx.respond("\n".join(lines))

    async def export(self, ctx: Context) -> None:
        """Export role blueprints as JSON."""
        await ctx.defer()

        guild = ctx.guild
        if not guild:
            await ctx.respond("❌ This command only works in servers.")
            return

        blueprint_set = await self.plugin.storage.load_blueprints(guild.id)
        if not blueprint_set:
            await ctx.respond("❌ No blueprints configured.")
            return

        data = blueprint_set.to_dict()
        json_str = json.dumps(data, indent=2)

        # Send as file if too large for message
        if len(json_str) > 2000:
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_str)
                await ctx.send_file(f.name, filename="role-blueprint.json")
        else:
            await ctx.respond(f"```json\n{json_str}\n```")

    async def reset(self, ctx: Context) -> None:
        """Reset all role blueprints (confirmation required)."""
        await ctx.defer()

        guild = ctx.guild
        if not guild:
            await ctx.respond("❌ This command only works in servers.")
            return

        # Confirmation prompt
        confirmed = await ctx.confirm(
            "⚠️ This will delete all role blueprints. Continue?",
            timeout=30,
        )

        if not confirmed:
            await ctx.respond("Cancelled.")
            return

        # Clear blueprints and role IDs
        config = await self.plugin.storage.store.load(guild.id)
        config.remove_other("roles:blueprints")
        config.remove_other("roles:blueprint_version")
        config.remove_other("roles:role_ids")
        await self.plugin.storage.store.save(config)

        await ctx.respond("✅ Role blueprints reset. Use `/roles setup` to configure again.")
