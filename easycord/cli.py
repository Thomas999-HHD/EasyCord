"""Command line tools for EasyCord developers."""
from __future__ import annotations

import argparse
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import sys
import textwrap
import platform
from typing import Sequence

from .bot import Bot
from .formatters import (
    format_doctor_report,
    format_interaction_inventory,
    format_sync_plan,
)


def _class_name(name: str) -> str:
    parts = re.split(r"[^0-9A-Za-z]+", name)
    cleaned = "".join(part[:1].upper() + part[1:] for part in parts if part)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"Plugin{cleaned}"
    return cleaned


def _module_name(name: str) -> str:
    lowered = re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_").lower()
    if not lowered:
        return "plugin"
    if lowered[0].isdigit():
        return f"plugin_{lowered}"
    return lowered


def _load_bot(spec: str) -> Bot:
    if ":" not in spec:
        raise SystemExit("Bot target must use 'module:object', for example 'bot:bot'.")
    module_name, object_name = spec.split(":", 1)
    if not module_name or not object_name:
        raise SystemExit("Bot target must include both module and object names.")
    if "" not in sys.path:
        sys.path.insert(0, "")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Could not import module {module_name!r}: {exc}") from exc
    try:
        candidate = getattr(module, object_name)
    except AttributeError as exc:
        raise SystemExit(
            f"Module {module_name!r} has no object named {object_name!r}."
        ) from exc
    if not isinstance(candidate, Bot):
        raise SystemExit(
            f"{spec!r} resolved to {type(candidate).__name__}, not an easycord.Bot."
        )
    return candidate


def _write_new_project(target: Path, name: str) -> list[Path]:
    plugin_module = _module_name(name)
    plugin_class = f"{_class_name(name)}Plugin"
    files = {
        "bot.py": f'''\
            import os

            from easycord import Bot

            from plugins.{plugin_module} import {plugin_class}


            bot = Bot(auto_sync=False)
            bot.add_plugin({plugin_class}())


            if __name__ == "__main__":
                bot.run(os.environ["DISCORD_TOKEN"])
            ''',
        "plugins/__init__.py": "",
        f"plugins/{plugin_module}.py": f'''\
            from easycord import Plugin, slash


            class {plugin_class}(Plugin):
                @slash(description="Say hello")
                async def hello(self, ctx):
                    await ctx.respond(f"Hello, {{ctx.user.display_name}}!")
            ''',
        ".env.example": "DISCORD_TOKEN=replace-me\n",
        "pyproject.toml": f'''\
            [project]
            name = "{_module_name(name).replace("_", "-")}-bot"
            version = "0.1.0"
            requires-python = ">=3.10"
            dependencies = ["easycord"]

            [project.optional-dependencies]
            dev = ["pytest>=7", "pytest-asyncio>=0.21"]

            [tool.pytest.ini_options]
            asyncio_mode = "auto"
            ''',
        "tests/test_bot.py": f'''\
            from bot import bot
            from easycord.testing import invoke


            async def test_hello_command():
                ctx = await invoke(bot, "hello")
                ctx.assert_contains("Hello")
            ''',
    }
    written: list[Path] = []
    for relative, content in files.items():
        path = target / relative
        if path.exists():
            raise SystemExit(f"Refusing to overwrite existing file: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content), encoding="utf-8")
        written.append(path)
    return written


def _test_template(plugin_name: str) -> str:
    plugin_class = f"{_class_name(plugin_name)}Plugin"
    module_name = _module_name(plugin_name)
    return textwrap.dedent(
        f'''\
        from easycord import Bot
        from easycord.testing import invoke

        from plugins.{module_name} import {plugin_class}


        async def test_{module_name}_command():
            bot = Bot(auto_sync=False, db_backend="memory")
            try:
                bot.add_plugin({plugin_class}())
                ctx = await invoke(bot, "hello")
                assert ctx.response_count == 1
            finally:
                await bot.close()
        '''
    )


def cmd_new(args: argparse.Namespace) -> int:
    target = Path(args.name)
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"Directory {target} already exists and is not empty.")
    written = _write_new_project(target, target.name)
    print(f"Created EasyCord project at {target}")
    for path in written:
        print(f"  {path.relative_to(target)}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    bot = _load_bot(args.target)
    inventory = bot.inspect_interactions()
    if args.json:
        print(json.dumps(inventory, indent=2, default=str))
    else:
        print(format_interaction_inventory(inventory))
    return 0


def cmd_sync_plan(args: argparse.Namespace) -> int:
    bot = _load_bot(args.target)
    plan = bot.plan_command_sync(remote_commands=args.remote or None)
    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        print(format_sync_plan(plan))
    return 0


def _doctor_report(target: str | None = None) -> dict[str, object]:
    checks: list[dict[str, object]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    python_version = platform.python_version()
    add("Python >= 3.10", sys.version_info >= (3, 10), python_version)

    try:
        discord_version = metadata.version("discord.py")
    except metadata.PackageNotFoundError:
        add("discord.py installed", False, "package not found")
    else:
        add("discord.py installed", True, f"v{discord_version}")

    add(
        "DISCORD_TOKEN configured",
        bool(os.getenv("DISCORD_TOKEN")),
        "set" if os.getenv("DISCORD_TOKEN") else "missing",
    )

    if target:
        try:
            bot = _load_bot(target)
        except SystemExit as exc:
            add("bot target imports", False, str(exc))
        else:
            inventory = bot.inspect_interactions()
            total = sum(len(entries) for entries in inventory.values())
            add("bot target imports", True, f"{target} ({total} interactions)")
            add("auto_sync disabled for local imports", not bot._auto_sync)

    failed = sum(1 for check in checks if not check["ok"])
    return {
        "checks": checks,
        "failed": failed,
        "summary": "All checks passed." if failed == 0 else f"{failed} check(s) need attention.",
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    report = _doctor_report(args.target)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_doctor_report(report))
    return 0 if report["failed"] == 0 else 1


def cmd_test_template(args: argparse.Namespace) -> int:
    content = _test_template(args.plugin_name)
    if args.output:
        path = Path(args.output)
        if path.exists():
            raise SystemExit(f"Refusing to overwrite existing file: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")
    else:
        print(content, end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="easycord", description="EasyCord developer toolkit")
    subcommands = parser.add_subparsers(dest="command", required=True)

    new = subcommands.add_parser("new", help="Create a starter EasyCord bot project")
    new.add_argument("name")
    new.set_defaults(func=cmd_new)

    inspect = subcommands.add_parser("inspect", help="Show a bot's registered interactions")
    inspect.add_argument("target", help="Bot object as module:object, for example bot:bot")
    inspect.add_argument("--json", action="store_true", help="Print raw JSON")
    inspect.set_defaults(func=cmd_inspect)

    sync_plan = subcommands.add_parser("sync-plan", help="Preview command sync changes")
    sync_plan.add_argument("target", help="Bot object as module:object, for example bot:bot")
    sync_plan.add_argument("--remote", action="append", default=[], help="Remote command name to compare")
    sync_plan.add_argument("--json", action="store_true", help="Print raw JSON")
    sync_plan.set_defaults(func=cmd_sync_plan)

    doctor = subcommands.add_parser("doctor", help="Check local EasyCord development setup")
    doctor.add_argument("target", nargs="?", help="Optional bot object as module:object")
    doctor.add_argument("--json", action="store_true", help="Print raw JSON")
    doctor.set_defaults(func=cmd_doctor)

    template = subcommands.add_parser("test-template", help="Generate a starter plugin test")
    template.add_argument("plugin_name")
    template.add_argument("-o", "--output", help="Write the template to a file")
    template.set_defaults(func=cmd_test_template)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
