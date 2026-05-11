"""Guild, channel, webhook, and emoji management helpers for Bot."""
from __future__ import annotations

from pathlib import Path
import inspect
from typing import Any

import discord
from discord import app_commands

from .guild_adaptation import (
    GuildAdaptationProfile,
    GuildAdaptationResult,
    diff_guild_adaptation,
    format_guild_adaptation_summary,
    plan_guild_adaptation,
    validate_guild_adaptation_profile,
)
from .server_config import ServerConfigStore


class _GuildMixin:
    """Mixin: guild/channel/webhook/emoji management methods."""

    # ── Guild lookup ──────────────────────────────────────────

    async def fetch_guild(self, guild_id: int) -> discord.Guild:
        """Return a guild by ID, checking the cache first.

        Raises ``discord.NotFound`` if the bot is not in the guild.
        """
        return self.get_guild(guild_id) or await super().fetch_guild(guild_id)  # type: ignore[misc]

    async def fetch_channel(self, channel_id: int) -> discord.abc.GuildChannel:
        """Return a channel by ID, checking the cache first.

        Raises ``discord.NotFound`` / ``discord.Forbidden`` on failure.
        """
        return self.get_channel(channel_id) or await super().fetch_channel(channel_id)  # type: ignore[misc]

    # ── Guild management ──────────────────────────────────────

    async def leave_guild(self, guild_id: int) -> None:
        """Make the bot leave a guild.

        Raises ``RuntimeError`` if the bot is not in the guild.
        """
        guild = self.get_guild(guild_id)
        if guild is None:
            raise RuntimeError(f"Bot is not in guild {guild_id}")
        await guild.leave()

    # ── Guild adaptation ─────────────────────────────────────

    def plan_guild_adaptation(
        self,
        guild: discord.Guild,
        *,
        profile: GuildAdaptationProfile | str | None = None,
    ) -> dict[str, Any]:
        """Infer channel and role config from a guild's cached structure.

        This is an offline inspection helper. It does not create channels,
        change roles, sync commands, or contact Discord.
        """
        selected = validate_guild_adaptation_profile(
            profile or getattr(self, "_guild_adaptation_profile", "standard")
        )
        return plan_guild_adaptation(guild, profile=selected)

    async def diff_guild_adaptation(
        self,
        guild: discord.Guild,
        *,
        profile: GuildAdaptationProfile | str | None = None,
        overwrite: bool = False,
        store: ServerConfigStore | None = None,
    ) -> dict[str, Any]:
        """Dry-run a guild adaptation against stored config."""
        plan = self.plan_guild_adaptation(guild, profile=profile)
        config_store = store or getattr(self, "_guild_config_store", None)
        if config_store is None:
            config_store = ServerConfigStore()
            self._guild_config_store = config_store
        config = await config_store.load(guild.id)
        return diff_guild_adaptation(config, plan, overwrite=overwrite)

    def describe_guild_adaptation(
        self,
        guild: discord.Guild,
        result_or_plan: Any | None = None,
    ) -> str:
        """Return an admin-facing summary for a guild adaptation."""
        data = result_or_plan or self.plan_guild_adaptation(guild)
        return format_guild_adaptation_summary(data)

    async def apply_guild_adaptation(
        self,
        guild: discord.Guild,
        *,
        overwrite: bool = False,
        profile: GuildAdaptationProfile | str | None = None,
        store: ServerConfigStore | None = None,
    ) -> GuildAdaptationResult:
        """Persist inferred channel and role keys for a guild.

        Existing config is preserved by default. Pass ``overwrite=True`` to
        replace existing ``ServerConfig`` channel and role keys with the
        current inference result.
        """
        plan = self.plan_guild_adaptation(guild, profile=profile)
        config_store = store or getattr(self, "_guild_config_store", None)
        if config_store is None:
            config_store = ServerConfigStore()
            self._guild_config_store = config_store

        config = await config_store.load(guild.id)
        created_keys: dict[str, Any] = {}
        preserved_keys: dict[str, Any] = {}
        overwritten_keys: dict[str, Any] = {}

        for key, channel_id in plan["channels"].items():
            existing = config.get_channel(key)
            flat_key = f"channels.{key}"
            if existing is None:
                config.set_channel(key, channel_id)
                created_keys[flat_key] = channel_id
            elif overwrite and existing != channel_id:
                config.set_channel(key, channel_id)
                overwritten_keys[flat_key] = channel_id
            else:
                preserved_keys[flat_key] = existing

        for key, role_id in plan["roles"].items():
            existing = config.get_role(key)
            flat_key = f"roles.{key}"
            if existing is None:
                config.set_role(key, role_id)
                created_keys[flat_key] = role_id
            elif overwrite and existing != role_id:
                config.set_role(key, role_id)
                overwritten_keys[flat_key] = role_id
            else:
                preserved_keys[flat_key] = existing

        hints = {
            **dict(plan.get("hints", {})),
            "low_confidence_suggestions": list(plan.get("low_confidence_suggestions", [])),
        }
        result = GuildAdaptationResult(
            guild_id=guild.id,
            applied=bool(created_keys or overwritten_keys or preserved_keys),
            profile=plan["profile"],
            created_keys=created_keys,
            preserved_keys=preserved_keys,
            overwritten_keys=overwritten_keys,
            warnings=list(plan.get("warnings", [])),
            suggestions=list(plan.get("suggestions", [])),
            plan=plan,
        )
        config.set_other("guild_adaptation", result.to_dict())
        config.set_other("guild_adaptation_hints", hints)
        await config_store.save(config)
        return result

    async def _dispatch_guild_adaptation_callbacks(
        self,
        result: GuildAdaptationResult,
    ) -> None:
        callbacks = list(getattr(self, "_guild_adaptation_callbacks", []))
        for callback in callbacks:
            try:
                maybe_awaitable = callback(result)
                if inspect.isawaitable(maybe_awaitable):
                    await maybe_awaitable
            except Exception as exc:
                import logging
                logging.getLogger("easycord").exception(
                    "Error in guild adaptation callback",
                    exc_info=exc,
                )

    def on_guild_adaptation(self, func):
        """Register a callback for completed guild adaptation results."""
        if not callable(func):
            raise TypeError(
                f"guild adaptation callback must be callable, got {type(func).__name__!r}"
            )
        self._guild_adaptation_callbacks.append(func)
        return func

    def add_guild_adaptation_commands(self) -> None:
        """Register optional admin commands for reviewing guild adaptation."""
        root = self.tree.get_command("easycord")
        if not isinstance(root, app_commands.Group):
            root = app_commands.Group(
                name="easycord",
                description="EasyCord developer and setup tools",
            )
            self.tree.add_command(root)

        setup = next(
            (
                command
                for command in root.commands
                if isinstance(command, app_commands.Group) and command.name == "setup"
            ),
            None,
        )
        if setup is None:
            setup = app_commands.Group(
                name="setup",
                description="Review EasyCord guild onboarding",
            )
            root.add_command(setup)

        if any(command.name == "review" for command in setup.commands):
            return

        async def review(ctx) -> None:
            if ctx.guild is None:
                await ctx.respond("This command only works in a server.", ephemeral=True)
                return
            config_store = getattr(self, "_guild_config_store", None)
            if config_store is None:
                config_store = ServerConfigStore()
                self._guild_config_store = config_store
            config = await config_store.load(ctx.guild.id)
            latest = config.get_other("guild_adaptation")
            if latest:
                summary = format_guild_adaptation_summary(latest)
            else:
                summary = format_guild_adaptation_summary(
                    self.plan_guild_adaptation(ctx.guild)
                )
            await ctx.respond(summary, ephemeral=True)

        async def explain(ctx) -> None:
            await ctx.respond(
                "EasyCord guild adaptation analyzes cached channel and role "
                "names, writes only EasyCord ServerConfigStore keys, and never "
                "creates channels, edits roles, changes permissions, or calls "
                "Discord APIs. Use /easycord setup review before enabling "
                "optional server features.",
                ephemeral=True,
            )

        self._register_slash(
            review,
            name="review",
            description="Review inferred EasyCord guild onboarding config.",
            guild_id=None,
            guild_only=True,
            require_admin=True,
            ephemeral=True,
            parent=setup,
        )
        self._register_slash(
            explain,
            name="explain",
            description="Explain what EasyCord guild adaptation does.",
            guild_id=None,
            guild_only=True,
            require_admin=True,
            ephemeral=True,
            parent=setup,
        )

    # ── Channel management ────────────────────────────────────

    async def create_channel(
        self,
        guild_id: int,
        name: str,
        *,
        channel_type: str = "text",
        category_id: int | None = None,
        topic: str | None = None,
        reason: str | None = None,
    ) -> discord.abc.GuildChannel:
        """Create a channel in a guild and return it.

        ``channel_type`` must be one of ``"text"``, ``"voice"``, ``"category"``,
        ``"stage"``, or ``"forum"``.

        Raises ``RuntimeError`` if the bot is not in the guild.
        Raises ``ValueError`` for an unrecognised ``channel_type``.
        """
        guild = self.get_guild(guild_id)
        if guild is None:
            raise RuntimeError(f"Bot is not in guild {guild_id}")

        category: discord.CategoryChannel | None = None
        if category_id is not None:
            cat = self.get_channel(category_id)
            if isinstance(cat, discord.CategoryChannel):
                category = cat

        if channel_type == "text":
            return await guild.create_text_channel(
                name, category=category, topic=topic, reason=reason
            )
        if channel_type == "voice":
            return await guild.create_voice_channel(
                name, category=category, reason=reason
            )
        if channel_type == "category":
            return await guild.create_category(name, reason=reason)
        if channel_type == "stage":
            return await guild.create_stage_channel(
                name, category=category, reason=reason
            )
        if channel_type == "forum":
            return await guild.create_forum(
                name, category=category, reason=reason
            )
        raise ValueError(
            f"Unknown channel_type {channel_type!r}. "
            "Must be 'text', 'voice', 'category', 'stage', or 'forum'."
        )

    async def delete_channel(
        self, channel_id: int, *, reason: str | None = None
    ) -> None:
        """Delete a channel by ID."""
        channel = self.get_channel(channel_id) or await super().fetch_channel(channel_id)  # type: ignore[misc]
        await channel.delete(reason=reason)

    # ── Webhooks ──────────────────────────────────────────────

    async def send_webhook(
        self,
        channel_id: int,
        content: str | None = None,
        *,
        username: str | None = None,
        avatar_url: str | None = None,
        embed: discord.Embed | None = None,
        **kwargs,
    ) -> None:
        """Send a message via a webhook in the given channel.

        On first call for a channel, creates a webhook named ``"Webhook"`` and
        caches it. Subsequent calls reuse the cached webhook.

        Example::

            await bot.send_webhook(CHANNEL_ID, "Hello from a webhook!")
        """
        if channel_id not in self._webhooks:  # type: ignore[attr-defined]
            channel = self.get_channel(channel_id) or await self.fetch_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                raise RuntimeError(
                    f"Channel {channel_id} is not a text channel"
                )
            self._webhooks[channel_id] = await channel.create_webhook(name="Webhook")  # type: ignore[attr-defined]
        webhook = self._webhooks[channel_id]  # type: ignore[attr-defined]
        try:
            await webhook.send(content, username=username, avatar_url=avatar_url, embed=embed, **kwargs)
        except discord.NotFound:
            # Recreate stale cached webhook once and retry.
            channel = self.get_channel(channel_id) or await self.fetch_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                raise RuntimeError(
                    f"Channel {channel_id} is not a text channel"
                ) from None
            self._webhooks[channel_id] = await channel.create_webhook(name="Webhook")  # type: ignore[attr-defined]
            webhook = self._webhooks[channel_id]  # type: ignore[attr-defined]
            await webhook.send(content, username=username, avatar_url=avatar_url, embed=embed, **kwargs)

    # ── Emoji management ──────────────────────────────────────

    async def create_emoji(
        self,
        guild_id: int,
        name: str,
        image_path: str,
        *,
        reason: str | None = None,
    ) -> discord.Emoji:
        """Create a custom emoji in a guild from a local image file.

        Raises ``RuntimeError`` if the bot is not in the guild.
        """
        guild = self.get_guild(guild_id)
        if guild is None:
            raise RuntimeError(f"Bot is not in guild {guild_id}")
        path = Path(image_path)
        if not path.exists() or not path.is_file():
            raise RuntimeError(f"Emoji image file not found: {image_path}")
        # Discord's custom emoji upload limit is 256 KiB.
        if path.stat().st_size > 256 * 1024:
            raise RuntimeError(
                f"Emoji image exceeds 256 KiB: {image_path}"
            )
        with path.open("rb") as f:
            image_bytes = f.read()
        return await guild.create_custom_emoji(name=name, image=image_bytes, reason=reason)

    async def delete_emoji(
        self,
        guild_id: int,
        emoji_id: int,
        *,
        reason: str | None = None,
    ) -> None:
        """Delete a custom emoji from a guild by emoji ID.

        Raises ``RuntimeError`` if the bot is not in the guild.
        """
        guild = self.get_guild(guild_id)
        if guild is None:
            raise RuntimeError(f"Bot is not in guild {guild_id}")
        emoji = await guild.fetch_emoji(emoji_id)
        await emoji.delete(reason=reason)

    async def fetch_guild_emojis(self, guild_id: int) -> list[discord.Emoji]:
        """Return all custom emojis for a guild.

        Raises ``RuntimeError`` if the bot is not in the guild.
        """
        guild = self.get_guild(guild_id)
        if guild is None:
            raise RuntimeError(f"Bot is not in guild {guild_id}")
        return await guild.fetch_emojis()
