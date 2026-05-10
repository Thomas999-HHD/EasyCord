"""Tests for the EasyCord developer toolkit."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from easycord import (
    Bot,
    format_doctor_report,
    format_interaction_inventory,
    format_sync_plan,
)
from easycord.cli import main
from easycord.testing import invoke_component, invoke_modal


def test_format_interaction_inventory_and_sync_plan() -> None:
    bot = Bot(auto_sync=False, db_backend="memory")
    try:
        @bot.slash(description="Ping")
        async def ping(ctx):
            await ctx.respond("pong")

        inventory = format_interaction_inventory(bot.inspect_interactions())
        plan = format_sync_plan(bot.plan_command_sync(remote_commands=["old"]))

        assert "EasyCord interaction inventory" in inventory
        assert "slash: 1" in inventory
        assert "ping (Bot, global, enabled)" in inventory
        assert "added: ping" in plan
        assert "removed: old" in plan
    finally:
        asyncio.run(bot.close())


def test_format_doctor_report() -> None:
    rendered = format_doctor_report(
        {
            "checks": [
                {"name": "Python >= 3.10", "ok": True, "detail": "3.14.0"},
                {"name": "DISCORD_TOKEN configured", "ok": False, "detail": "missing"},
            ],
            "summary": "1 check(s) need attention.",
        }
    )

    assert "EasyCord doctor" in rendered
    assert "ok: Python >= 3.10 - 3.14.0" in rendered
    assert "error: DISCORD_TOKEN configured - missing" in rendered


async def test_invoke_component_static_and_dynamic_routes() -> None:
    bot = Bot(auto_sync=False, db_backend="memory")
    seen: list[object] = []
    try:
        @bot.component("static:button")
        async def static_button(ctx):
            seen.append("static")
            await ctx.respond("static ok")

        @bot.component("ticket:close:{ticket_id:int}")
        async def close_ticket(ctx, ticket_id: int):
            seen.append(ticket_id)
            await ctx.respond(str(ticket_id))

        static_ctx = await invoke_component(bot, "static:button")
        dynamic_ctx = await invoke_component(bot, "ticket:close:42")

        assert seen == ["static", 42]
        assert static_ctx.last_response == "static ok"
        assert dynamic_ctx.last_response == "42"
    finally:
        await bot.close()


async def test_invoke_component_missing_raises_lookup_error() -> None:
    bot = Bot(auto_sync=False, db_backend="memory")
    try:
        with pytest.raises(LookupError, match="Component"):
            await invoke_component(bot, "missing")
    finally:
        await bot.close()


async def test_invoke_modal_passes_field_values() -> None:
    bot = Bot(auto_sync=False, db_backend="memory")
    seen = {}
    try:
        @bot.modal("profile:edit")
        async def edit_profile(ctx, data):
            seen.update(data)
            await ctx.respond(data["name"])

        ctx = await invoke_modal(bot, "profile:edit", name="Ada", title="Engineer")

        assert seen == {"name": "Ada", "title": "Engineer"}
        assert ctx.last_response == "Ada"
    finally:
        await bot.close()


def test_cli_new_creates_project(tmp_path: Path, capsys) -> None:
    project = tmp_path / "demo_bot"

    assert main(["new", str(project)]) == 0
    output = capsys.readouterr().out

    assert "Created EasyCord project" in output
    assert (project / "bot.py").exists()
    assert (project / "plugins" / "demo_bot.py").exists()
    assert (project / "tests" / "test_bot.py").exists()
    assert "Bot(auto_sync=False)" in (project / "bot.py").read_text(encoding="utf-8")


def test_cli_test_template_prints_and_writes(tmp_path: Path, capsys) -> None:
    assert main(["test-template", "greetings"]) == 0
    printed = capsys.readouterr().out
    assert "from plugins.greetings import GreetingsPlugin" in printed

    output = tmp_path / "tests" / "test_greetings.py"
    assert main(["test-template", "greetings", "--output", str(output)]) == 0
    assert "async def test_greetings_command" in output.read_text(encoding="utf-8")


def test_cli_inspect_and_sync_plan(tmp_path: Path, monkeypatch, capsys) -> None:
    module = tmp_path / "sample_bot.py"
    module.write_text(
        "from easycord import Bot\n"
        "bot = Bot(auto_sync=False, db_backend='memory')\n"
        "@bot.slash(description='Ping')\n"
        "async def ping(ctx):\n"
        "    await ctx.respond('pong')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    assert main(["inspect", "sample_bot:bot"]) == 0
    assert "slash: 1" in capsys.readouterr().out

    assert main(["sync-plan", "sample_bot:bot", "--remote", "old", "--json"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["added"] == ["ping"]
    assert plan["removed"] == ["old"]


def test_cli_doctor_reports_environment_and_bot(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = tmp_path / "sample_bot.py"
    module.write_text(
        "from easycord import Bot\n"
        "bot = Bot(auto_sync=False, db_backend='memory')\n"
        "@bot.slash(description='Ping')\n"
        "async def ping(ctx):\n"
        "    await ctx.respond('pong')\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")

    assert main(["doctor", "sample_bot:bot"]) == 0
    output = capsys.readouterr().out

    assert "EasyCord doctor" in output
    assert "ok: DISCORD_TOKEN configured - set" in output
    assert "ok: bot target imports - sample_bot:bot (1 interactions)" in output

    assert main(["doctor", "sample_bot:bot", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["failed"] == 0


def test_cli_import_errors_are_clear(tmp_path: Path, monkeypatch) -> None:
    module = tmp_path / "not_a_bot.py"
    module.write_text("bot = object()\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    with pytest.raises(SystemExit, match="not an easycord.Bot"):
        main(["inspect", "not_a_bot:bot"])
