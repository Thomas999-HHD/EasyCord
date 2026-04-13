"""Tests for the v2.2 middleware additions: dm_only and allowed_roles."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from easycord.middleware import allowed_roles, dm_only


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_ctx(*, guild=True, role_ids: list[int] | None = None):
    ctx = MagicMock()
    ctx.respond = AsyncMock()
    ctx.user = MagicMock()
    ctx.user.id = 1

    if guild:
        ctx.guild = MagicMock()
        member = MagicMock()
        roles = []
        for rid in (role_ids or []):
            r = MagicMock()
            r.id = rid
            roles.append(r)
        member.roles = roles
        ctx.guild.get_member = MagicMock(return_value=member)
    else:
        ctx.guild = None

    return ctx


# ── dm_only ───────────────────────────────────────────────────────────────────

async def test_dm_only_passes_in_dm():
    ctx = _make_ctx(guild=False)
    proceed = AsyncMock()
    await dm_only()(ctx, proceed)
    proceed.assert_called_once()


async def test_dm_only_blocks_in_guild():
    ctx = _make_ctx(guild=True)
    proceed = AsyncMock()
    await dm_only()(ctx, proceed)
    proceed.assert_not_called()
    ctx.respond.assert_called_once()
    assert ctx.respond.call_args.kwargs.get("ephemeral") is True


# ── allowed_roles ─────────────────────────────────────────────────────────────

async def test_allowed_roles_passes_when_member_has_role():
    ctx = _make_ctx(guild=True, role_ids=[100, 200])
    proceed = AsyncMock()
    await allowed_roles(200)(ctx, proceed)
    proceed.assert_called_once()


async def test_allowed_roles_blocks_when_member_lacks_role():
    ctx = _make_ctx(guild=True, role_ids=[100])
    proceed = AsyncMock()
    await allowed_roles(999)(ctx, proceed)
    proceed.assert_not_called()
    ctx.respond.assert_called_once()
    assert ctx.respond.call_args.kwargs.get("ephemeral") is True


async def test_allowed_roles_passes_with_any_matching_role():
    ctx = _make_ctx(guild=True, role_ids=[50, 99])
    proceed = AsyncMock()
    await allowed_roles(1, 2, 99)(ctx, proceed)
    proceed.assert_called_once()


async def test_allowed_roles_passes_in_dm():
    """DMs bypass the role check — combine with guild_only() if needed."""
    ctx = _make_ctx(guild=False)
    proceed = AsyncMock()
    await allowed_roles(999)(ctx, proceed)
    proceed.assert_called_once()


async def test_allowed_roles_blocks_when_member_not_in_cache():
    ctx = _make_ctx(guild=True, role_ids=[])
    ctx.guild.get_member = MagicMock(return_value=None)
    proceed = AsyncMock()
    await allowed_roles(100)(ctx, proceed)
    proceed.assert_not_called()


async def test_allowed_roles_custom_message():
    ctx = _make_ctx(guild=True, role_ids=[])
    proceed = AsyncMock()
    await allowed_roles(999, message="Staff only!")(ctx, proceed)
    assert "Staff only!" in ctx.respond.call_args[0][0]
