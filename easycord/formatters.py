"""Developer-facing text formatters for EasyCord diagnostics."""
from __future__ import annotations

from typing import Any, Mapping


_INTERACTION_ORDER = ("slash", "context_menu", "component", "modal", "autocomplete")


def format_interaction_inventory(inventory: Mapping[str, list[Mapping[str, Any]]]) -> str:
    """Return a compact text summary of ``Bot.inspect_interactions()`` output."""
    lines = ["EasyCord interaction inventory"]
    for kind in _INTERACTION_ORDER:
        entries = list(inventory.get(kind, []))
        lines.append(f"{kind}: {len(entries)}")
        for entry in entries:
            source = entry.get("source") or "Bot"
            name = entry.get("pattern") or entry.get("name") or "<unnamed>"
            scope = entry.get("guild_id")
            scope_text = f"guild:{scope}" if scope is not None else "global"
            enabled = "enabled" if entry.get("enabled", True) else "disabled"
            lines.append(f"  - {name} ({source}, {scope_text}, {enabled})")
    return "\n".join(lines)


def format_sync_plan(plan: Mapping[str, list[str]]) -> str:
    """Return a compact text summary of ``Bot.plan_command_sync()`` output."""
    lines = ["EasyCord command sync plan"]
    for key in ("added", "changed", "removed", "unchanged", "warnings"):
        values = list(plan.get(key, []))
        rendered = ", ".join(str(value) for value in values) if values else "-"
        lines.append(f"{key}: {rendered}")
    return "\n".join(lines)


def format_doctor_report(report: Mapping[str, Any]) -> str:
    """Return a compact text summary of ``easycord doctor`` checks."""
    lines = ["EasyCord doctor"]
    for check in report.get("checks", []):
        status = "ok" if check.get("ok") else "error"
        detail = check.get("detail")
        suffix = f" - {detail}" if detail else ""
        lines.append(f"{status}: {check.get('name', '<unnamed>')}{suffix}")
    summary = report.get("summary")
    if summary:
        lines.append(str(summary))
    return "\n".join(lines)


__all__ = [
    "format_doctor_report",
    "format_interaction_inventory",
    "format_sync_plan",
]
