"""Support ticket plugin for EasyCord bots."""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path

import discord

from easycord import Plugin, slash
from easycord.decorators import on


_TOPIC_RE = re.compile(r"Ticket #\d+ \| opener:(\d+)")


class TicketPlugin(Plugin):
    """Creates and manages private support-ticket channels.

    Quick start::

        from easycord.plugins.tickets import TicketPlugin
        bot.add_plugin(TicketPlugin())

    Slash commands registered
    -------------------------
    ``/open_ticket [reason]``       — Open a new ticket (everyone).
    ``/close_ticket``               — Close the current ticket (opener or manage_channels).
    ``/add_to_ticket member``       — Grant access (support role or manage_channels).
    ``/remove_from_ticket member``  — Revoke access (support role or manage_channels).
    ``/set_ticket_category``        — Set the Discord category (manage_guild).
    ``/set_support_role``           — Set the staff role (manage_guild).
    ``/ticket_config``              — Show current config (manage_guild).
    """

    def __init__(self, *, data_dir: str = ".easycord/tickets") -> None:
        super().__init__()
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

    # ── Config helpers ────────────────────────────────────────

    def _cfg_path(self, guild_id: int) -> Path:
        return self._data_dir / f"{guild_id}.json"

    def _read_config(self, guild_id: int) -> dict:
        path = self._cfg_path(guild_id)
        if not path.exists():
            return {"category_id": None, "support_role_id": None, "ticket_count": 0}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _write_config(self, guild_id: int, config: dict) -> None:
        path = self._cfg_path(guild_id)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        os.replace(tmp, path)

    def _update_config(self, guild_id: int, **kwargs) -> None:
        cfg = self._read_config(guild_id)
        cfg.update(kwargs)
        self._write_config(guild_id, cfg)

    # ── Channel helpers ───────────────────────────────────────

    def _is_ticket_channel(self, channel) -> bool:
        return bool(channel.topic and _TOPIC_RE.search(channel.topic))

    def _parse_opener_id(self, channel) -> int | None:
        if not channel.topic:
            return None
        m = _TOPIC_RE.search(channel.topic)
        return int(m.group(1)) if m else None

    def _has_support_role(self, ctx, cfg: dict) -> bool:
        role_id = cfg.get("support_role_id")
        if not role_id or not ctx.member:
            return False
        return any(r.id == role_id for r in ctx.member.roles)

    # ── Slash commands ────────────────────────────────────────

    @slash(description="Open a support ticket.", guild_only=True)
    async def open_ticket(self, ctx, reason: str = "") -> None:
        if not ctx.guild:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return

        cfg = self._read_config(ctx.guild.id)
        count = cfg["ticket_count"] + 1
        self._update_config(ctx.guild.id, ticket_count=count)

        name = f"ticket-{ctx.user.name}-{count}"
        topic = f"Ticket #{count} | opener:{ctx.user.id}"

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            ctx.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        support_role_id = cfg.get("support_role_id")
        if support_role_id:
            role = ctx.guild.get_role(support_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True
                )

        category = None
        category_id = cfg.get("category_id")
        if category_id:
            category = ctx.guild.get_channel(category_id)

        channel = await ctx.guild.create_text_channel(
            name, topic=topic, overwrites=overwrites, category=category
        )

        reason_text = f"\n**Reason:** {reason}" if reason else ""
        embed = discord.Embed(
            title=f"Ticket #{count}",
            description=(
                f"Opened by {ctx.user.mention}{reason_text}\n\n"
                "Support will be with you shortly. "
                "Use `/close_ticket` to close this ticket."
            ),
            color=discord.Color.green(),
        )
        await channel.send(embed=embed)
        await ctx.respond(f"Your ticket has been opened: {channel.mention}", ephemeral=True)

    @slash(description="Close this support ticket.", guild_only=True)
    async def close_ticket(self, ctx) -> None:
        if not self._is_ticket_channel(ctx.channel):
            await ctx.respond("This is not a ticket channel.", ephemeral=True)
            return

        opener_id = self._parse_opener_id(ctx.channel)
        is_opener = ctx.user.id == opener_id
        has_perm = ctx.member and ctx.member.guild_permissions.manage_channels
        if not is_opener and not has_perm:
            await ctx.respond(
                "Only the ticket opener or staff can close this ticket.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Ticket Closed",
            description=f"Closed by {ctx.user.mention}. This channel will be deleted shortly.",
            color=discord.Color.red(),
        )
        await ctx.channel.send(embed=embed)
        await asyncio.sleep(5)
        await ctx.channel.delete(reason=f"Ticket closed by {ctx.user}")

    @slash(description="Add a member to this ticket.", guild_only=True)
    async def add_to_ticket(self, ctx, member: discord.Member) -> None:
        if not self._is_ticket_channel(ctx.channel):
            await ctx.respond("This is not a ticket channel.", ephemeral=True)
            return

        cfg = self._read_config(ctx.guild.id)
        has_perm = (
            self._has_support_role(ctx, cfg)
            or (ctx.member and ctx.member.guild_permissions.manage_channels)
        )
        if not has_perm:
            await ctx.respond(
                "You don't have permission to modify this ticket.", ephemeral=True
            )
            return

        await ctx.channel.set_permissions(member, view_channel=True, send_messages=True)
        await ctx.respond(f"{member.mention} has been added to this ticket.", ephemeral=True)

    @slash(description="Remove a member from this ticket.", guild_only=True)
    async def remove_from_ticket(self, ctx, member: discord.Member) -> None:
        if not self._is_ticket_channel(ctx.channel):
            await ctx.respond("This is not a ticket channel.", ephemeral=True)
            return

        cfg = self._read_config(ctx.guild.id)
        has_perm = (
            self._has_support_role(ctx, cfg)
            or (ctx.member and ctx.member.guild_permissions.manage_channels)
        )
        if not has_perm:
            await ctx.respond(
                "You don't have permission to modify this ticket.", ephemeral=True
            )
            return

        await ctx.channel.set_permissions(member, view_channel=False, send_messages=False)
        await ctx.respond(
            f"{member.mention} has been removed from this ticket.", ephemeral=True
        )

    @slash(
        description="Set the category for new ticket channels.",
        permissions=["manage_guild"],
        guild_only=True,
    )
    async def set_ticket_category(self, ctx, category: discord.CategoryChannel) -> None:
        self._update_config(ctx.guild.id, category_id=category.id)
        await ctx.respond(
            f"Ticket channels will be created in {category.mention}.", ephemeral=True
        )

    @slash(
        description="Set the support role automatically added to tickets.",
        permissions=["manage_guild"],
        guild_only=True,
    )
    async def set_support_role(self, ctx, role: discord.Role) -> None:
        self._update_config(ctx.guild.id, support_role_id=role.id)
        await ctx.respond(
            f"{role.mention} will be added to all new tickets.", ephemeral=True
        )

    @slash(description="Show the current ticket configuration.", guild_only=True)
    async def ticket_config(self, ctx) -> None:
        cfg = self._read_config(ctx.guild.id)

        def _ch(key: str) -> str:
            cid = cfg.get(key)
            if not cid:
                return "*not set*"
            ch = ctx.guild.get_channel(cid)
            return ch.mention if ch else f"<#{cid}> *(deleted?)*"

        def _role() -> str:
            rid = cfg.get("support_role_id")
            if not rid:
                return "*not set*"
            r = ctx.guild.get_role(rid)
            return r.mention if r else f"<@&{rid}> *(deleted?)*"

        embed = discord.Embed(
            title=f"Ticket config — {ctx.guild.name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Category", value=_ch("category_id"), inline=True)
        embed.add_field(name="Support role", value=_role(), inline=True)
        embed.add_field(name="Tickets opened", value=str(cfg["ticket_count"]), inline=True)
        await ctx.respond(embed=embed, ephemeral=True)
