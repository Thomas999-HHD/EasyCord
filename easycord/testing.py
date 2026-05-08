"""Testing helpers for EasyCord commands.

These helpers let tests exercise registered commands without connecting to
Discord.  They intentionally model only the interaction attributes EasyCord
uses during command dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord

from .context import Context


class _FakePermissions:
    """Permission object that defaults unknown permissions to ``False``."""

    def __init__(self, **values: bool) -> None:
        self.administrator = False
        for name, value in values.items():
            setattr(self, name, bool(value))

    def __getattr__(self, name: str) -> bool:
        return False


@dataclass
class _CapturedResponse:
    content: str | None = None
    ephemeral: bool = False
    embed: discord.Embed | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)


class _FakeResponder:
    def __init__(self, interaction: "FakeInteraction") -> None:
        self._interaction = interaction
        self.send_message = AsyncMock(side_effect=self._send_message)
        self.defer = AsyncMock(side_effect=self._defer)

    async def _send_message(
        self,
        content: str | None = None,
        *,
        ephemeral: bool = False,
        embed: discord.Embed | None = None,
        **kwargs: Any,
    ) -> None:
        self._interaction._responses.append(
            _CapturedResponse(content, ephemeral, embed, dict(kwargs))
        )

    async def _defer(self, *, ephemeral: bool = False, **_: Any) -> None:
        self._interaction._deferred = True
        self._interaction._deferred_ephemeral = ephemeral


class _FakeFollowup:
    def __init__(self, interaction: "FakeInteraction") -> None:
        self._interaction = interaction
        self.send = AsyncMock(side_effect=self._send)

    async def _send(
        self,
        content: str | None = None,
        *,
        ephemeral: bool = False,
        embed: discord.Embed | None = None,
        **kwargs: Any,
    ) -> None:
        self._interaction._responses.append(
            _CapturedResponse(content, ephemeral, embed, dict(kwargs))
        )


class FakeInteraction:
    """Small fake ``discord.Interaction`` for command unit tests."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        command: Any | None = None,
        user_id: int = 1,
        guild_id: int | None = 100,
        is_admin: bool = False,
        entitlements: list[Any] | None = None,
        locale: str | None = None,
        guild_locale: str | None = None,
        permissions: dict[str, bool] | None = None,
    ) -> None:
        permission_values = dict(permissions or {})
        permission_values.setdefault("administrator", is_admin)
        guild_permissions = _FakePermissions(**permission_values)

        self.user = MagicMock(spec=discord.Member if guild_id is not None else discord.User)
        self.user.id = user_id
        self.user.name = f"user-{user_id}"
        self.user.display_name = f"User {user_id}"
        self.user.guild_permissions = guild_permissions
        self.user.roles = []
        self.user.voice = None

        self.guild = None
        if guild_id is not None:
            self.guild = MagicMock(spec=discord.Guild)
            self.guild.id = guild_id
            self.guild.name = f"Guild {guild_id}"
            self.guild.get_member.return_value = self.user
            self.guild.fetch_member = AsyncMock(return_value=self.user)
            self.guild.me = MagicMock()

        self.channel = MagicMock()
        self.channel.send = AsyncMock()
        self.channel.permissions_for = MagicMock(return_value=guild_permissions)
        self.command = command
        self.data: dict[str, Any] = {}
        self.locale = locale
        self.guild_locale = guild_locale
        self.context = None
        self.entitlements = entitlements or []
        self.client = client or SimpleNamespace(
            localization=None,
            i18n=None,
            ai_provider=None,
            conversation_memory=None,
            get_channel=lambda _channel_id: None,
            fetch_channel=AsyncMock(return_value=None),
        )

        self._responses: list[_CapturedResponse] = []
        self._deferred = False
        self._deferred_ephemeral = False
        self.response = _FakeResponder(self)
        self.followup = _FakeFollowup(self)
        self.edit_original_response = AsyncMock()


class FakeContext(Context):
    """``Context`` with response capture helpers for assertions."""

    @classmethod
    def make(
        cls,
        *,
        client: Any | None = None,
        command: Any | None = None,
        user_id: int = 1,
        guild_id: int | None = 100,
        is_admin: bool = False,
        entitlements: list[Any] | None = None,
        permissions: dict[str, bool] | None = None,
    ) -> "FakeContext":
        interaction = FakeInteraction(
            client=client,
            command=command,
            user_id=user_id,
            guild_id=guild_id,
            is_admin=is_admin,
            entitlements=entitlements,
            permissions=permissions,
        )
        return cls(interaction)

    @property
    def member(self) -> discord.Member | None:
        return self.guild.get_member(self.user.id) if self.guild else None

    @property
    def responses(self) -> list[_CapturedResponse]:
        return self.interaction._responses

    @property
    def response_count(self) -> int:
        return len(self.responses)

    @property
    def last_response(self) -> str | None:
        return self.responses[-1].content if self.responses else None

    @property
    def was_ephemeral(self) -> bool:
        return self.responses[-1].ephemeral if self.responses else False

    def assert_content(self, expected: str) -> None:
        assert self.last_response == expected

    def assert_contains(self, expected: str) -> None:
        assert self.last_response is not None
        assert expected in self.last_response


async def invoke(
    bot: Any,
    command_name: str,
    *,
    user_id: int = 1,
    guild_id: int | None = 100,
    is_admin: bool = True,
    entitlements: list[Any] | None = None,
    permissions: dict[str, bool] | None = None,
    **kwargs: Any,
) -> FakeContext:
    """Invoke a registered slash command and return a captured context."""

    command = bot.tree.get_command(command_name)
    if command is None:
        available = ", ".join(sorted(cmd.name for cmd in bot.tree.walk_commands()))
        raise LookupError(f"Command {command_name!r} is not registered. Available: {available}")

    interaction = FakeInteraction(
        client=bot,
        command=command,
        user_id=user_id,
        guild_id=guild_id,
        is_admin=is_admin,
        entitlements=entitlements,
        permissions=permissions,
    )
    await command.callback(interaction, **kwargs)
    return FakeContext(interaction)


async def invoke_autocomplete(
    bot: Any,
    command_name: str,
    option_name: str,
    current: str,
    *,
    user_id: int = 1,
    guild_id: int | None = 100,
    options: dict[str, Any] | None = None,
) -> list[Any]:
    """Invoke a registered autocomplete callback without Discord."""

    for entry in bot.registry.autocomplete_callbacks.values():
        if (
            entry.metadata.get("command_name") == command_name
            and entry.metadata.get("option_name") == option_name
        ):
            interaction = FakeInteraction(
                client=bot,
                command=bot.tree.get_command(command_name),
                user_id=user_id,
                guild_id=guild_id,
            )
            interaction.namespace = SimpleNamespace(**(options or {}))
            ctx = FakeContext(interaction)
            try:
                return list(await entry.callback(ctx, current, options or {}))
            except TypeError:
                return list(await entry.callback(current))
    raise LookupError(
        f"Autocomplete for {command_name!r}.{option_name!r} is not registered."
    )


__all__ = ["FakeContext", "FakeInteraction", "invoke", "invoke_autocomplete"]
