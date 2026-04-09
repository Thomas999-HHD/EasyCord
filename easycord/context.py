from __future__ import annotations

import discord


class Context:
    """Wraps a discord.Interaction with a cleaner response API."""

    def __init__(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        self._responded = False

    # ── Attributes ────────────────────────────────────────────

    @property
    def user(self) -> discord.User | discord.Member:
        return self.interaction.user

    @property
    def guild(self) -> discord.Guild | None:
        return self.interaction.guild

    @property
    def channel(self) -> discord.abc.Messageable | None:
        return self.interaction.channel  # type: ignore[return-value]

    @property
    def command_name(self) -> str | None:
        cmd = self.interaction.command
        return cmd.name if cmd is not None else None

    @property
    def data(self) -> dict | None:
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
        self._responded = True
        await self.interaction.response.defer(ephemeral=ephemeral)

    async def respond_embed(
        self,
        title: str,
        description: str | None = None,
        *,
        color: discord.Color = discord.Color.blue(),
        ephemeral: bool = False,
        **kwargs,
    ) -> None:
        embed = discord.Embed(title=title, description=description, color=color)
        await self.respond(embed=embed, ephemeral=ephemeral, **kwargs)
