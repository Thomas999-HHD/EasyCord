"""Simple message-trigger auto-replies for guilds."""
from __future__ import annotations

import discord

from easycord import on, slash

from .base import JsonConfigPlugin


def _normalize_trigger(text: str) -> str:
    return " ".join(text.strip().lower().split())


class AutoReplyPlugin(JsonConfigPlugin):
    """Register message triggers that respond with canned replies.

    This is a small quality-of-life plugin for server FAQs, onboarding hints,
    and short canned responses without needing a full bot command tree.
    """

    @on("message")
    async def _on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        content = _normalize_trigger(message.content)
        if not content:
            return
        rules = self._read_config(message.guild.id).get("rules", {})
        response = rules.get(content)
        if response:
            await message.channel.send(response)

    @slash(
        description="Add an auto-reply trigger for this server.",
        permissions=["manage_guild"],
        guild_only=True,
    )
    async def autoreply_add(self, ctx, trigger: str, response: str) -> None:
        guild = self.require_guild(ctx)
        key = _normalize_trigger(trigger)

        def updater(config: dict) -> None:
            config.setdefault("rules", {})[key] = response

        self._update_config(guild.id, updater)
        await ctx.respond(
            f"Auto-reply added for `{trigger.strip()}`.",
            ephemeral=True,
        )

    @slash(
        description="Remove an auto-reply trigger from this server.",
        permissions=["manage_guild"],
        guild_only=True,
    )
    async def autoreply_remove(self, ctx, trigger: str) -> None:
        guild = self.require_guild(ctx)
        key = _normalize_trigger(trigger)
        removed = self._update_config(
            guild.id,
            lambda config: config.get("rules", {}).pop(key, None),
        )
        if removed is None:
            await ctx.respond(f"No auto-reply found for `{trigger.strip()}`.", ephemeral=True)
            return
        await ctx.respond(f"Auto-reply removed for `{trigger.strip()}`.", ephemeral=True)

    @slash(
        description="List all auto-reply triggers for this server.",
        guild_only=True,
    )
    async def autoreply_list(self, ctx) -> None:
        guild = self.require_guild(ctx)
        rules = self._read_config(guild.id).get("rules", {})
        if not rules:
            await ctx.respond("No auto-replies configured yet.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"Auto-replies - {guild.name}",
            color=discord.Color.green(),
        )
        lines = [f"`{trigger}` → {response}" for trigger, response in sorted(rules.items())]
        embed.description = "\n".join(lines)
        await ctx.respond(embed=embed, ephemeral=True)

