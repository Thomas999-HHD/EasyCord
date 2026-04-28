"""Announcement helper plugin for posting server updates consistently."""
from __future__ import annotations

import discord

from easycord import slash

from .base import JsonConfigPlugin


class AnnouncementsPlugin(JsonConfigPlugin):
    """Store an announcement channel and send embeds with one slash command.

    This plugin is intentionally small: it gives server owners a predictable
    "post update" flow without needing to hand-roll the channel lookup each time.
    """

    @slash(
        description="Set the default announcement channel for this server.",
        permissions=["manage_guild"],
        guild_only=True,
    )
    async def set_announcement_channel(
        self,
        ctx,
        channel: discord.TextChannel,
    ) -> None:
        guild = self.require_guild(ctx)
        self._update_config(guild.id, lambda cfg: cfg.update({"announcement_channel": channel.id}))
        await ctx.respond(
            f"Announcements will be posted in {channel.mention}.",
            ephemeral=True,
        )

    @slash(
        description="Post a server announcement as an embed.",
        permissions=["manage_guild"],
        guild_only=True,
    )
    async def announce(
        self,
        ctx,
        title: str,
        message: str,
        ping_everyone: bool = False,
    ) -> None:
        guild = self.require_guild(ctx)
        config = self._read_config(guild.id)
        channel_id = config.get("announcement_channel")

        channel = None
        if channel_id is not None:
            channel = ctx.bot.get_channel(channel_id) or await ctx.bot.fetch_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            channel = self.require_text_channel(ctx)

        embed = discord.Embed(
            title=title,
            description=message,
            color=discord.Color.blurple(),
        )
        content = "@everyone" if ping_everyone else None
        await channel.send(
            content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=ping_everyone),
        )
        await ctx.respond(f"Announcement sent to {channel.mention}.", ephemeral=True)

    @slash(
        description="Show the current announcement configuration.",
        guild_only=True,
    )
    async def announcement_config(self, ctx) -> None:
        guild = self.require_guild(ctx)
        config = self._read_config(guild.id)
        channel_id = config.get("announcement_channel")
        channel_text = f"<#{channel_id}>" if channel_id else "*not set*"

        embed = discord.Embed(
            title=f"Announcement config - {guild.name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Default channel", value=channel_text, inline=False)
        await ctx.respond(embed=embed, ephemeral=True)

