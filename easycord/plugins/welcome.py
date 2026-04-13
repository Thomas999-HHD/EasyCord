"""Configurable welcome / goodbye plugin for EasyCord bots."""
from __future__ import annotations

import json
import os
from pathlib import Path

import discord

from easycord import Plugin, on, slash


class WelcomePlugin(Plugin):
    """Posts welcome and goodbye embeds and optionally assigns an auto-role on join.

    Configuration is persisted per-guild as JSON files so settings survive
    bot restarts.  Admins configure the plugin through slash commands.

    Quick start::

        from easycord.plugins.welcome import WelcomePlugin
        bot.add_plugin(WelcomePlugin())

    Slash commands registered
    -------------------------
    ``/set_welcome_channel`` — Channel to post welcome messages in.
    ``/set_goodbye_channel`` — Channel to post goodbye messages in.
    ``/set_auto_role``       — Role automatically assigned to new members.
    ``/set_welcome_message`` — Customise the welcome text (supports ``{user}``
                               and ``{server}`` placeholders).
    ``/set_goodbye_message`` — Customise the goodbye text.
    ``/welcome_config``      — Show current welcome configuration.
    """

    def __init__(self, *, data_dir: str = ".easycord/welcome") -> None:
        super().__init__()
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

    # ── Config helpers ────────────────────────────────────────

    def _cfg_path(self, guild_id: int) -> Path:
        return self._data_dir / f"{guild_id}.json"

    def _read_config(self, guild_id: int) -> dict:
        path = self._cfg_path(guild_id)
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _write_config(self, guild_id: int, config: dict) -> None:
        path = self._cfg_path(guild_id)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        os.replace(tmp, path)

    def _update(self, guild_id: int, **kwargs) -> None:
        cfg = self._read_config(guild_id)
        cfg.update(kwargs)
        self._write_config(guild_id, cfg)

    # ── Events ────────────────────────────────────────────────

    @on("member_join")
    async def _on_member_join(self, member: discord.Member) -> None:
        cfg = self._read_config(member.guild.id)

        # Auto-role
        role_id = cfg.get("auto_role")
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="WelcomePlugin auto-role")
                except discord.HTTPException:
                    pass

        # Welcome message
        channel_id = cfg.get("welcome_channel")
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        template = cfg.get(
            "welcome_message",
            "👋 Welcome to **{server}**, {user}! Glad to have you here.",
        )
        text = template.format(user=member.mention, server=member.guild.name)

        embed = discord.Embed(description=text, color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count}")
        await channel.send(embed=embed)

    @on("member_remove")
    async def _on_member_remove(self, member: discord.Member) -> None:
        cfg = self._read_config(member.guild.id)
        channel_id = cfg.get("goodbye_channel")
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        template = cfg.get(
            "goodbye_message",
            "👋 **{user}** has left **{server}**. Farewell!",
        )
        text = template.format(user=str(member), server=member.guild.name)
        embed = discord.Embed(description=text, color=discord.Color.red())
        await channel.send(embed=embed)

    # ── Slash commands ────────────────────────────────────────

    @slash(description="Set the channel for welcome messages.", permissions=["manage_guild"])
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel) -> None:
        if not ctx.guild:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return
        self._update(ctx.guild.id, welcome_channel=channel.id)
        await ctx.respond(f"Welcome messages will be posted in {channel.mention}.", ephemeral=True)

    @slash(description="Set the channel for goodbye messages.", permissions=["manage_guild"])
    async def set_goodbye_channel(self, ctx, channel: discord.TextChannel) -> None:
        if not ctx.guild:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return
        self._update(ctx.guild.id, goodbye_channel=channel.id)
        await ctx.respond(f"Goodbye messages will be posted in {channel.mention}.", ephemeral=True)

    @slash(description="Assign a role automatically when a member joins.", permissions=["manage_guild"])
    async def set_auto_role(self, ctx, role: discord.Role) -> None:
        if not ctx.guild:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return
        self._update(ctx.guild.id, auto_role=role.id)
        await ctx.respond(f"New members will automatically receive {role.mention}.", ephemeral=True)

    @slash(description="Customise the welcome message. Use {user} and {server} as placeholders.", permissions=["manage_guild"])
    async def set_welcome_message(self, ctx, message: str) -> None:
        if not ctx.guild:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return
        self._update(ctx.guild.id, welcome_message=message)
        preview = message.format(user=ctx.user.mention, server=ctx.guild.name)
        await ctx.respond(f"Welcome message updated!\n**Preview:** {preview}", ephemeral=True)

    @slash(description="Customise the goodbye message. Use {user} and {server} as placeholders.", permissions=["manage_guild"])
    async def set_goodbye_message(self, ctx, message: str) -> None:
        if not ctx.guild:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return
        self._update(ctx.guild.id, goodbye_message=message)
        preview = message.format(user=str(ctx.user), server=ctx.guild.name)
        await ctx.respond(f"Goodbye message updated!\n**Preview:** {preview}", ephemeral=True)

    @slash(description="Show the current welcome configuration for this server.")
    async def welcome_config(self, ctx) -> None:
        if not ctx.guild:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return

        cfg = self._read_config(ctx.guild.id)

        def _channel_str(key: str) -> str:
            cid = cfg.get(key)
            if not cid:
                return "*not set*"
            ch = ctx.guild.get_channel(cid)
            return ch.mention if ch else f"<#{cid}> *(deleted?)*"

        def _role_str() -> str:
            rid = cfg.get("auto_role")
            if not rid:
                return "*not set*"
            r = ctx.guild.get_role(rid)
            return r.mention if r else f"<@&{rid}> *(deleted?)*"

        embed = discord.Embed(
            title=f"⚙️ Welcome config — {ctx.guild.name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Welcome channel", value=_channel_str("welcome_channel"), inline=True)
        embed.add_field(name="Goodbye channel", value=_channel_str("goodbye_channel"), inline=True)
        embed.add_field(name="Auto-role", value=_role_str(), inline=True)
        embed.add_field(
            name="Welcome message",
            value=cfg.get("welcome_message", "*default*"),
            inline=False,
        )
        embed.add_field(
            name="Goodbye message",
            value=cfg.get("goodbye_message", "*default*"),
            inline=False,
        )
        await ctx.respond(embed=embed, ephemeral=True)
