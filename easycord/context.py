"""Context object wrapping discord.Interaction with a simple response API."""
from __future__ import annotations

import asyncio
import types as _types

import discord


class Context:
    """Wraps a ``discord.Interaction`` and gives you a simple response API.

    EasyCord passes a ``Context`` as the first argument to every slash command::

        @bot.slash(description="Ping the bot")
        async def ping(ctx):
            await ctx.respond("Pong!")

    For commands that take a while, call ``defer()`` first so Discord doesn't
    time out while you work (you then have 15 minutes to follow up)::

        @bot.slash(description="Generate a report")
        async def report(ctx):
            await ctx.defer()                   # tells Discord "I'm working on it"
            data = await fetch_data()
            await ctx.respond(f"Done: {data}")  # follows up automatically
    """

    def __init__(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        self._responded = False

    # ── Read-only properties ──────────────────────────────────

    @property
    def user(self) -> discord.User | discord.Member:
        """The user who ran the command."""
        return self.interaction.user

    @property
    def guild(self) -> discord.Guild | None:
        """The server the command was run in, or ``None`` if it was in a DM."""
        return self.interaction.guild

    @property
    def channel(self) -> discord.abc.Messageable | None:
        """The channel the command was run in."""
        return self.interaction.channel  # type: ignore[return-value]

    @property
    def command_name(self) -> str | None:
        """The name of the slash command that was invoked."""
        cmd = self.interaction.command
        return cmd.name if cmd is not None else None

    @property
    def data(self) -> dict | None:
        """The raw interaction data from Discord."""
        return self.interaction.data  # type: ignore[return-value]

    # ── Responding ────────────────────────────────────────────

    async def respond(
        self,
        content: str | None = None,
        *,
        ephemeral: bool = False,
        embed: discord.Embed | None = None,
        **kwargs,
    ) -> None:
        """Send a reply to the command.

        The first call sends an initial response; any further calls send
        follow-up messages automatically.

        Parameters
        ----------
        content:
            The text message to send.
        ephemeral:
            If ``True``, only the user who ran the command can see the reply.
        embed:
            A ``discord.Embed`` to attach instead of (or alongside) text.
        """
        if not self._responded:
            self._responded = True
            await self.interaction.response.send_message(
                content, ephemeral=ephemeral, embed=embed, **kwargs
            )
        else:
            await self.interaction.followup.send(
                content, ephemeral=ephemeral, embed=embed, **kwargs
            )

    async def defer(self, *, ephemeral: bool = False) -> None:
        """Acknowledge the interaction without sending a visible reply yet.

        Use this at the start of commands that take more than 3 seconds, then
        call ``respond()`` when you're ready. You have up to 15 minutes.

        Has no effect if the interaction has already been responded to.
        """
        if self._responded:
            return
        self._responded = True
        await self.interaction.response.defer(ephemeral=ephemeral)

    async def send_embed(
        self,
        title: str,
        description: str | None = None,
        *,
        fields: list[tuple] | None = None,
        footer: str | None = None,
        color: discord.Color = discord.Color.blue(),
        ephemeral: bool = False,
        **kwargs,
    ) -> None:
        """Build and send a Discord embed in one call.

        ``fields`` is a list of ``(name, value)`` or ``(name, value, inline)``
        tuples. ``inline`` defaults to ``True`` when omitted.

        Example — a simple embed with fields::

            await ctx.send_embed(
                "Server Stats",
                fields=[("Members", "150"), ("Online", "42")],
                footer="Updated just now",
                color=discord.Color.green(),
            )
        """
        embed = discord.Embed(title=title, description=description, color=color)
        for field in (fields or []):
            name, value, *rest = field
            embed.add_field(name=name, value=value, inline=rest[0] if rest else True)
        if footer:
            embed.set_footer(text=footer)
        await self.respond(embed=embed, ephemeral=ephemeral, **kwargs)

    async def dm(
        self,
        content: str | None = None,
        *,
        embed: discord.Embed | None = None,
        **kwargs,
    ) -> None:
        """Send a direct message to the user who invoked the command.

        Example::

            @bot.slash(description="Send yourself a reminder")
            async def remind(ctx, message: str):
                await ctx.dm(f"Reminder: {message}")
                await ctx.respond("Reminder sent!", ephemeral=True)
        """
        try:
            await self.user.send(content, embed=embed, **kwargs)
        except discord.Forbidden:
            raise RuntimeError(
                f"Cannot send a DM to {self.user} — they have DMs disabled or have blocked the bot."
            ) from None

    async def send_to(
        self,
        channel_id: int,
        content: str | None = None,
        **kwargs,
    ) -> None:
        """Send a message to any channel by ID.

        Looks up the channel from the client cache first; falls back to a
        Discord API fetch if it is not cached.

        Example::

            @bot.slash(description="Post to the logs channel")
            async def log(ctx, message: str):
                await ctx.send_to(LOG_CHANNEL_ID, f"**Log:** {message}")
                await ctx.respond("Posted.", ephemeral=True)
        """
        try:
            channel = (
                self.interaction.client.get_channel(channel_id)
                or await self.interaction.client.fetch_channel(channel_id)
            )
        except discord.NotFound:
            raise RuntimeError(f"Channel {channel_id} does not exist.") from None
        except discord.Forbidden:
            raise RuntimeError(
                f"Bot does not have permission to access channel {channel_id}."
            ) from None
        await channel.send(content, **kwargs)  # type: ignore[union-attr]

    # ── Interactive UI ────────────────────────────────────────

    async def ask_form(
        self,
        title: str,
        **fields: dict,
    ) -> dict[str, str] | None:
        """Show a modal form and return submitted values as a ``dict``.

        Each keyword argument becomes a text input field. Pass a ``dict``
        with ``discord.ui.TextInput`` kwargs (``label``, ``max_length``,
        ``style``, etc.) as the value. ``style`` may be a string such as
        ``"short"`` or ``"paragraph"``.

        Returns ``None`` if the user dismisses or the modal times out.

        Example::

            result = await ctx.ask_form(
                "Feedback",
                subject=dict(label="Subject", max_length=100),
                body=dict(label="Body", style="paragraph"),
            )
            if result:
                await ctx.respond(f"Got: {result['subject']}")
        """
        future: asyncio.Future[dict[str, str] | None] = asyncio.get_running_loop().create_future()

        # Build TextInput items keyed by field name (used as custom_id).
        attrs: dict = {}
        for name, config in fields.items():
            cfg = dict(config)
            style_raw = cfg.pop("style", discord.TextStyle.short)
            if isinstance(style_raw, str):
                style_raw = getattr(discord.TextStyle, style_raw, discord.TextStyle.short)
            attrs[name] = discord.ui.TextInput(
                label=cfg.pop("label", name),
                custom_id=name,
                style=style_raw,
                **cfg,
            )

        _fut = future

        async def on_submit(self, interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            if not _fut.done():
                _fut.set_result(
                    {c.custom_id: c.value for c in self.children
                     if isinstance(c, discord.ui.TextInput)}
                )

        async def on_timeout(*_) -> None:
            if not _fut.done():
                _fut.set_result(None)

        attrs["on_submit"] = on_submit
        attrs["on_timeout"] = on_timeout

        ModalClass = _types.new_class(
            "_DynamicModal",
            (discord.ui.Modal,),
            {},
            lambda ns: ns.update(attrs),
        )

        await self.interaction.response.send_modal(ModalClass(title=title))
        self._responded = True

        try:
            return await asyncio.wait_for(future, timeout=660)
        except asyncio.TimeoutError:
            return None

    async def confirm(
        self,
        prompt: str,
        *,
        timeout: float = 30,
        yes_label: str = "Yes",
        no_label: str = "Cancel",
        ephemeral: bool = False,
    ) -> bool | None:
        """Show a Yes/No button prompt and return the user's choice.

        Returns ``True`` (yes), ``False`` (no/cancel), or ``None`` (timed out).

        Example::

            confirmed = await ctx.confirm(f"Ban {member.mention}?", timeout=30)
            if confirmed:
                await member.ban()
            elif confirmed is False:
                await ctx.respond("Cancelled.", ephemeral=True)
        """
        future: asyncio.Future[bool | None] = asyncio.get_running_loop().create_future()
        _fut = future
        _yes = yes_label
        _no = no_label

        class _ConfirmView(discord.ui.View):
            @discord.ui.button(label=_yes, style=discord.ButtonStyle.green)
            async def yes_btn(self, interaction: discord.Interaction, *_) -> None:
                await interaction.response.edit_message(view=discord.ui.View())
                if not _fut.done():
                    _fut.set_result(True)
                self.stop()

            @discord.ui.button(label=_no, style=discord.ButtonStyle.red)
            async def no_btn(self, interaction: discord.Interaction, *_) -> None:
                await interaction.response.edit_message(view=discord.ui.View())
                if not _fut.done():
                    _fut.set_result(False)
                self.stop()

            async def on_timeout(self) -> None:
                if not _fut.done():
                    _fut.set_result(None)

        view = _ConfirmView(timeout=timeout)
        await self.respond(prompt, ephemeral=ephemeral, view=view)
        return await future

    async def paginate(
        self,
        pages: list[str | discord.Embed],
        *,
        timeout: float = 120,
        ephemeral: bool = False,
    ) -> None:
        """Show a multi-page browsable message with Prev / Next buttons.

        ``pages`` may be a list of strings or ``discord.Embed`` objects,
        or a mix of both.

        Example::

            await ctx.paginate(["Page 1", "Page 2", "Page 3"])

            embeds = [discord.Embed(title=f"Entry {i}") for i in range(10)]
            await ctx.paginate(embeds, timeout=60)
        """
        if not pages:
            return

        idx = [0]
        n = len(pages)

        def _kw(i: int) -> dict:
            page = pages[i]
            if isinstance(page, discord.Embed):
                return {"embed": page, "content": None}
            return {"content": str(page), "embed": None}

        prev_btn = discord.ui.Button(
            label="◀", style=discord.ButtonStyle.secondary, disabled=True
        )
        next_btn = discord.ui.Button(
            label="▶", style=discord.ButtonStyle.secondary, disabled=n <= 1
        )

        async def on_prev(interaction: discord.Interaction) -> None:
            idx[0] = max(0, idx[0] - 1)
            prev_btn.disabled = idx[0] == 0
            next_btn.disabled = idx[0] == n - 1
            await interaction.response.edit_message(**_kw(idx[0]), view=view)

        async def on_next(interaction: discord.Interaction) -> None:
            idx[0] = min(n - 1, idx[0] + 1)
            prev_btn.disabled = idx[0] == 0
            next_btn.disabled = idx[0] == n - 1
            await interaction.response.edit_message(**_kw(idx[0]), view=view)

        prev_btn.callback = on_prev
        next_btn.callback = on_next

        view = discord.ui.View(timeout=timeout)
        view.add_item(prev_btn)
        view.add_item(next_btn)

        await self.respond(**_kw(0), ephemeral=ephemeral, view=view)
