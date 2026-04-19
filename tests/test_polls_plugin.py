"""Tests for easycord.plugins.polls — PollsPlugin and _PollView."""
import discord
import pytest
from unittest.mock import AsyncMock, MagicMock

from easycord.plugins.polls import PollsPlugin, _PollView


# ── _PollView unit tests (async — discord.ui.View needs a running loop) ───────

async def test_tally_starts_at_zero():
    view = _PollView("Q", ["A", "B", "C"], 60)
    assert view._tally() == [0, 0, 0]


async def test_tally_counts_votes():
    view = _PollView("Q", ["A", "B"], 60)
    view.votes = {1: 0, 2: 0, 3: 1}
    assert view._tally() == [2, 1]


async def test_build_embed_has_question_in_title():
    view = _PollView("Favourite color?", ["Red", "Blue"], 60)
    embed = view.build_embed()
    assert "Favourite color?" in embed.title


async def test_build_embed_closed_changes_color():
    view = _PollView("Q", ["A", "B"], 60)
    open_embed = view.build_embed(closed=False)
    closed_embed = view.build_embed(closed=True)
    assert open_embed.color != closed_embed.color


async def test_build_embed_closed_footer():
    view = _PollView("Q", ["A", "B"], 60)
    embed = view.build_embed(closed=True)
    assert "closed" in embed.footer.text.lower()


async def test_build_embed_includes_all_options():
    view = _PollView("Q", ["Alpha", "Beta", "Gamma"], 60)
    embed = view.build_embed()
    for option in ["Alpha", "Beta", "Gamma"]:
        assert option in embed.description


async def test_bar_length_always_ten():
    view = _PollView("Q", ["A", "B"], 60)
    for filled in range(11):
        bar = view._bar(filled)
        assert len(bar) == 10


async def test_buttons_match_options():
    view = _PollView("Q", ["X", "Y", "Z"], 30)
    button_labels = [c.label for c in view.children if isinstance(c, discord.ui.Button)]
    assert button_labels == ["X", "Y", "Z"]


async def test_vote_callback_records_vote():
    view = _PollView("Q", ["A", "B"], 60)
    interaction = MagicMock()
    interaction.user = MagicMock()
    interaction.user.id = 42
    interaction.response = MagicMock()
    interaction.response.edit_message = AsyncMock()

    btn = view.children[0]  # option A
    await btn.callback(interaction)
    assert view.votes[42] == 0


async def test_vote_callback_allows_changing_vote():
    view = _PollView("Q", ["A", "B"], 60)
    interaction = MagicMock()
    interaction.user = MagicMock()
    interaction.user.id = 99
    interaction.response = MagicMock()
    interaction.response.edit_message = AsyncMock()

    await view.children[0].callback(interaction)  # vote A
    await view.children[1].callback(interaction)  # change to B
    assert view.votes[99] == 1


async def test_on_timeout_disables_all_buttons():
    view = _PollView("Q", ["A", "B"], 60)
    await view.on_timeout()
    for child in view.children:
        assert child.disabled is True


# ── PollsPlugin slash command ─────────────────────────────────────────────────

def _make_ctx():
    ctx = MagicMock()
    ctx.respond = AsyncMock()
    ctx.edit_response = AsyncMock()
    return ctx


async def test_poll_command_responds_with_embed(monkeypatch):
    plugin = PollsPlugin()
    ctx = _make_ctx()
    monkeypatch.setattr(_PollView, "wait", AsyncMock())
    await plugin.poll(ctx, "Best fruit?", "Apple", "Banana", duration=10)
    ctx.respond.assert_called_once()
    embed = ctx.respond.call_args.kwargs["embed"]
    assert "Best fruit?" in embed.title


async def test_poll_command_rejects_single_option(monkeypatch):
    plugin = PollsPlugin()
    ctx = _make_ctx()
    monkeypatch.setattr(_PollView, "wait", AsyncMock())
    await plugin.poll(ctx, "Q?", "Only one", "", duration=10)
    ctx.respond.assert_called_once()
    assert ctx.respond.call_args.kwargs.get("ephemeral") is True


async def test_poll_command_rejects_short_duration(monkeypatch):
    plugin = PollsPlugin()
    ctx = _make_ctx()
    monkeypatch.setattr(_PollView, "wait", AsyncMock())
    await plugin.poll(ctx, "Q?", "A", "B", duration=2)
    assert ctx.respond.call_args.kwargs.get("ephemeral") is True


async def test_poll_command_filters_empty_options(monkeypatch):
    plugin = PollsPlugin()
    ctx = _make_ctx()
    monkeypatch.setattr(_PollView, "wait", AsyncMock())
    await plugin.poll(ctx, "Q?", "A", "B", "", "", "", duration=10)
    ctx.respond.assert_called_once()
    view = ctx.respond.call_args.kwargs["view"]
    assert len(view.children) == 2


async def test_poll_edits_response_after_close(monkeypatch):
    plugin = PollsPlugin()
    ctx = _make_ctx()
    monkeypatch.setattr(_PollView, "wait", AsyncMock())
    await plugin.poll(ctx, "Q?", "A", "B", duration=10)
    ctx.edit_response.assert_called_once()
    final_embed = ctx.edit_response.call_args.kwargs["embed"]
    assert "closed" in final_embed.footer.text.lower()
