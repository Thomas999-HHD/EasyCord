"""Per-guild XP leveling and named rank system for EasyCord bots."""
from __future__ import annotations

import asyncio
import json
import math
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable

import discord

from easycord import Plugin, slash, on


# ── XP / level formulae ───────────────────────────────────────────────────────

def _xp_for_level(level: int) -> int:
    """Total XP required to reach *level* from zero.

    Uses a triangular progression: each level costs ``level * 100`` XP more
    than the previous one.

    - Level 1:  100 XP total
    - Level 2:  300 XP total
    - Level 5:  1 500 XP total
    - Level 10: 5 500 XP total
    """
    return level * (level + 1) // 2 * 100


def _level_from_xp(xp: int) -> int:
    """Return the level achieved for a given total XP amount.

    Solves ``n*(n+1)/2*100 ≤ xp`` in O(1) via ``math.isqrt``, then steps
    forward at most once to handle integer-division edge cases.
    """
    n = (math.isqrt(1 + 8 * xp // 100) - 1) // 2
    while _xp_for_level(n + 1) <= xp:
        n += 1
    return n


# ── Plugin ────────────────────────────────────────────────────────────────────

class LevelsPlugin(Plugin):
    """Per-guild XP, leveling, and customisable named ranks.

    Members earn XP for sending messages (one award per cooldown window).
    Reaching a new level posts a congratulation embed and optionally assigns
    a configured role reward.  Admins manage ranks and role rewards through
    slash commands.

    Quick start::

        from easycord.plugins.levels import LevelsPlugin

        bot.add_plugin(LevelsPlugin())

    Advanced::

        bot.add_plugin(LevelsPlugin(
            xp_per_message=15,
            cooldown_seconds=45,
            announce_levelups=True,
        ))

    Slash commands registered
    -------------------------
    ``/rank``            — Show your level, XP, and rank.
    ``/leaderboard``     — Top-10 XP leaderboard for the server.
    ``/give_xp``         — (manage_guild) Award XP to a member.
    ``/set_rank``        — (manage_guild) Attach a rank name to a level.
    ``/remove_rank``     — (manage_guild) Delete a rank name.
    ``/set_level_role``  — (manage_guild) Assign a role reward to a level.
    ``/ranks``           — List all configured ranks and role rewards.
    """

    def __init__(
        self,
        *,
        xp_per_message: int = 10,
        cooldown_seconds: float = 60.0,
        data_dir: str = ".easycord/levels",
        announce_levelups: bool = True,
    ) -> None:
        self._xp_per_message = xp_per_message
        self._cooldown = cooldown_seconds
        self._data_dir = Path(data_dir)
        self._announce = announce_levelups
        self._data_dir.mkdir(parents=True, exist_ok=True)
        # Per-guild locks: _xp_locks guards XP read-modify-write;
        # _cfg_locks guards config read-modify-write separately.
        self._xp_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._cfg_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        # In-memory cooldown tracker: {guild_id: {user_id: last_award_time}}
        self._cooldowns: dict[int, dict[int, float]] = defaultdict(dict)

    # ── Storage helpers ───────────────────────────────────────────────────────

    def _xp_path(self, guild_id: int) -> Path:
        return self._data_dir / f"{guild_id}_xp.json"

    def _cfg_path(self, guild_id: int) -> Path:
        return self._data_dir / f"{guild_id}_config.json"

    def _read_xp(self, guild_id: int) -> dict[str, dict]:
        """Synchronous read — call only while holding ``self._xp_locks[guild_id]``."""
        path = self._xp_path(guild_id)
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _write_xp(self, guild_id: int, data: dict[str, dict]) -> None:
        """Atomic synchronous write — call only while holding ``self._xp_locks[guild_id]``."""
        path = self._xp_path(guild_id)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)

    def _read_config(self, guild_id: int) -> dict:
        """Synchronous config read — safe for display; use ``_update_config`` for writes."""
        path = self._cfg_path(guild_id)
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    async def _update_config(self, guild_id: int, fn: Callable[[dict], object]) -> object:
        """Read config, call ``fn(config)`` inside a per-guild lock, write back atomically.

        Returns whatever ``fn`` returns, so callers can retrieve values from
        the mutation (e.g. ``dict.pop`` returning the removed value).
        """
        async with self._cfg_locks[guild_id]:
            config = self._read_config(guild_id)
            result = fn(config)
            path = self._cfg_path(guild_id)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            os.replace(tmp, path)
        return result

    # ── XP mutation ───────────────────────────────────────────────────────────

    async def add_xp(
        self, guild_id: int, user_id: int, amount: int
    ) -> tuple[int, int, bool]:
        """Add *amount* XP to a member and return ``(total_xp, level, leveled_up)``.

        The read-modify-write is protected by a per-guild lock so concurrent
        message events cannot corrupt the stored totals.
        """
        async with self._xp_locks[guild_id]:
            data = self._read_xp(guild_id)
            uid = str(user_id)
            entry = data.get(uid, {"xp": 0, "level": 0})
            old_level = entry["level"]
            entry["xp"] += amount
            entry["level"] = _level_from_xp(entry["xp"])
            data[uid] = entry
            self._write_xp(guild_id, data)
        return entry["xp"], entry["level"], entry["level"] > old_level

    def get_entry(self, guild_id: int, user_id: int) -> dict:
        """Return the stored entry for a user without holding the lock (read-only snapshot)."""
        data = self._read_xp(guild_id)
        return data.get(str(user_id), {"xp": 0, "level": 0})

    # ── Rank helpers ──────────────────────────────────────────────────────────

    def _rank_for_level(self, config: dict, level: int) -> str | None:
        """Return the highest rank name whose threshold is at or below *level*."""
        eligible = [
            (int(k), v)
            for k, v in config.get("ranks", {}).items()
            if int(k) <= level
        ]
        return max(eligible, key=lambda t: t[0])[1] if eligible else None

    # ── Progress bar ──────────────────────────────────────────────────────────

    @staticmethod
    def _progress_bar(xp: int, level: int, width: int = 10) -> str:
        current_floor = _xp_for_level(level)
        next_ceil = _xp_for_level(level + 1)
        span = next_ceil - current_floor
        filled = int((xp - current_floor) / span * width) if span else width
        return "█" * filled + "░" * (width - filled)

    # ── Guild guard ───────────────────────────────────────────────────────────

    @staticmethod
    async def _require_guild(ctx) -> bool:
        """Respond ephemerally and return ``False`` if invoked outside a server."""
        if ctx.guild is None:
            await ctx.respond("This command only works inside a server.", ephemeral=True)
            return False
        return True

    # ── Event: award XP on message ────────────────────────────────────────────

    @on("message")
    async def _award_xp(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        now = time.monotonic()

        if now - self._cooldowns[guild_id].get(user_id, 0.0) < self._cooldown:
            return
        self._cooldowns[guild_id][user_id] = now

        xp, level, leveled_up = await self.add_xp(guild_id, user_id, self._xp_per_message)

        if not leveled_up or not self._announce:
            return

        config = self._read_config(guild_id)
        rank = self._rank_for_level(config, level)
        rank_text = f" — **{rank}**" if rank else ""

        embed = discord.Embed(
            description=f"{message.author.mention} reached **Level {level}**{rank_text}! 🎉",
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Total XP: {xp}")

        role_rewards: dict[str, int] = config.get("role_rewards", {})
        role_id = role_rewards.get(str(level))
        if role_id and isinstance(message.author, discord.Member):
            role = message.guild.get_role(role_id)
            if role:
                try:
                    await message.author.add_roles(role, reason=f"Reached level {level}")
                    embed.add_field(name="Role awarded", value=role.mention, inline=False)
                except discord.HTTPException:
                    pass

        await message.channel.send(embed=embed)

    # ── Slash commands ────────────────────────────────────────────────────────

    @slash(description="Show your current level, XP, and rank.")
    async def rank(self, ctx) -> None:
        if not await self._require_guild(ctx):
            return

        entry = self.get_entry(ctx.guild.id, ctx.user.id)
        config = self._read_config(ctx.guild.id)
        level = entry["level"]
        xp = entry["xp"]
        rank_name = self._rank_for_level(config, level)
        next_xp = _xp_for_level(level + 1)
        current_floor = _xp_for_level(level)

        embed = discord.Embed(
            title=f"{ctx.user.display_name}'s Rank",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{xp:,}", inline=True)
        if rank_name:
            embed.add_field(name="Rank", value=rank_name, inline=True)

        bar = self._progress_bar(xp, level)
        progress = xp - current_floor
        needed = next_xp - current_floor
        embed.add_field(
            name=f"Progress to Level {level + 1}",
            value=f"`{bar}` {progress:,} / {needed:,} XP",
            inline=False,
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @slash(description="Show the server's top-10 XP leaderboard.")
    async def leaderboard(self, ctx) -> None:
        if not await self._require_guild(ctx):
            return

        data = self._read_xp(ctx.guild.id)
        if not data:
            await ctx.respond("No one has earned XP yet!", ephemeral=True)
            return

        config = self._read_config(ctx.guild.id)
        top = sorted(data.items(), key=lambda kv: kv[1]["xp"], reverse=True)[:10]

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (uid, entry) in enumerate(top):
            prefix = medals[i] if i < 3 else f"`{i + 1}.`"
            member = ctx.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"
            rank_name = self._rank_for_level(config, entry["level"])
            rank_text = f" · *{rank_name}*" if rank_name else ""
            lines.append(
                f"{prefix} **{name}** — Level {entry['level']}{rank_text} ({entry['xp']:,} XP)"
            )

        embed = discord.Embed(
            title=f"🏆 {ctx.guild.name} Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        await ctx.respond(embed=embed)

    @slash(description="Award XP to a member.", permissions=["manage_guild"])
    async def give_xp(self, ctx, member: discord.Member, amount: int) -> None:
        if not await self._require_guild(ctx):
            return
        if amount <= 0:
            await ctx.respond("Amount must be a positive number.", ephemeral=True)
            return
        xp, level, leveled_up = await self.add_xp(ctx.guild.id, member.id, amount)
        msg = f"Gave **{amount:,} XP** to {member.mention}. They now have **{xp:,} XP** (Level {level})."
        if leveled_up:
            msg += " 🎉 Level up!"
        await ctx.respond(msg)

    @slash(description="Name a rank for a specific level.", permissions=["manage_guild"])
    async def set_rank(self, ctx, level: int, name: str) -> None:
        if not await self._require_guild(ctx):
            return
        if level < 1:
            await ctx.respond("Level must be at least 1.", ephemeral=True)
            return

        def _set(config: dict) -> None:
            config.setdefault("ranks", {})[str(level)] = name

        await self._update_config(ctx.guild.id, _set)
        await ctx.respond(f"Rank **{name}** set for Level {level}.", ephemeral=True)

    @slash(description="Remove the rank name for a specific level.", permissions=["manage_guild"])
    async def remove_rank(self, ctx, level: int) -> None:
        if not await self._require_guild(ctx):
            return

        removed = await self._update_config(
            ctx.guild.id,
            lambda config: config.get("ranks", {}).pop(str(level), None),
        )
        if removed is None:
            await ctx.respond(f"No rank is configured at level {level}.", ephemeral=True)
            return
        await ctx.respond(f"Removed rank **{removed}** from Level {level}.", ephemeral=True)

    @slash(description="Assign a role reward when a member reaches a level.", permissions=["manage_guild"])
    async def set_level_role(self, ctx, level: int, role: discord.Role) -> None:
        if not await self._require_guild(ctx):
            return
        if level < 1:
            await ctx.respond("Level must be at least 1.", ephemeral=True)
            return

        def _set(config: dict) -> None:
            config.setdefault("role_rewards", {})[str(level)] = role.id

        await self._update_config(ctx.guild.id, _set)
        await ctx.respond(
            f"Members who reach **Level {level}** will receive {role.mention}.",
            ephemeral=True,
        )

    @slash(description="List all configured ranks and role rewards.")
    async def ranks(self, ctx) -> None:
        if not await self._require_guild(ctx):
            return

        config = self._read_config(ctx.guild.id)
        rank_map: dict[str, str] = config.get("ranks", {})
        role_map: dict[str, int] = config.get("role_rewards", {})

        all_levels = sorted(set(rank_map) | set(role_map), key=int)
        if not all_levels:
            await ctx.respond(
                "No ranks or role rewards configured yet.\n"
                "Use `/set_rank` or `/set_level_role` to add some.",
                ephemeral=True,
            )
            return

        lines = []
        for lvl_str in all_levels:
            parts = [f"**Level {lvl_str}**"]
            if lvl_str in rank_map:
                parts.append(f"*{rank_map[lvl_str]}*")
            if lvl_str in role_map:
                role = ctx.guild.get_role(role_map[lvl_str])
                parts.append(role.mention if role else f"Role {role_map[lvl_str]}")
            lines.append(" — ".join(parts))

        embed = discord.Embed(
            title=f"📊 {ctx.guild.name} Ranks",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        await ctx.respond(embed=embed)
