"""Offline guild structure adaptation helpers."""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal


GuildAdaptationProfile = Literal["conservative", "standard", "aggressive"]
VALID_GUILD_ADAPTATION_PROFILES: tuple[GuildAdaptationProfile, ...] = (
    "conservative",
    "standard",
    "aggressive",
)

_PROFILE_THRESHOLDS: dict[GuildAdaptationProfile, float] = {
    "conservative": 0.90,
    "standard": 0.75,
    "aggressive": 0.60,
}

_PROFILE_KEYS: dict[GuildAdaptationProfile, dict[str, set[str]]] = {
    "conservative": {
        "channels": {"logging", "moderation"},
        "roles": {"admin", "moderator", "staff"},
    },
    "standard": {
        "channels": {
            "logging",
            "welcome",
            "announcements",
            "rules",
            "general",
            "moderation",
            "support",
        },
        "roles": {"admin", "moderator", "staff", "member"},
    },
    "aggressive": {
        "channels": {
            "logging",
            "welcome",
            "goodbye",
            "announcements",
            "rules",
            "general",
            "moderation",
            "support",
            "starboard",
        },
        "roles": {"admin", "moderator", "staff", "member"},
    },
}

_CHANNEL_PATTERNS: dict[str, tuple[str, ...]] = {
    "logging": (
        "mod-logs",
        "mod-log",
        "moderation-logs",
        "audit-logs",
        "audit-log",
        "server-logs",
        "member-logs",
        "logs",
    ),
    "welcome": ("welcome", "welcomes", "introductions", "start-here", "arrivals"),
    "goodbye": ("goodbye", "goodbyes", "leaves", "departures"),
    "announcements": ("announcements", "announcement", "news", "updates"),
    "rules": ("rules", "guidelines", "server-rules"),
    "general": ("general", "chat", "lounge", "main-chat"),
    "moderation": ("moderation", "mod-chat", "staff-chat", "staff"),
    "support": ("support", "help", "tickets", "ticket-support"),
    "starboard": ("starboard", "highlights", "best-of"),
}

_ROLE_PATTERNS: dict[str, tuple[str, ...]] = {
    "admin": ("admin", "administrator", "owner"),
    "moderator": ("moderator", "moderators", "mod", "mods"),
    "staff": ("staff", "team", "support"),
    "member": ("member", "members", "verified"),
}


@dataclass(frozen=True, slots=True)
class GuildAdaptationSuggestion:
    """A confidence-scored EasyCord config suggestion."""

    key: str
    value: Any
    confidence: float
    reason: str
    source: str
    section: str
    name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "source": self.source,
            "section": self.section,
            "name": self.name,
        }


@dataclass(slots=True)
class GuildAdaptationResult(Mapping[str, Any]):
    """Result from applying a guild adaptation plan.

    The class is mapping-compatible for v5.4 callers that treated
    ``apply_guild_adaptation(...)`` as returning a plain dictionary.
    """

    guild_id: int
    applied: bool
    profile: GuildAdaptationProfile
    created_keys: dict[str, Any] = field(default_factory=dict)
    preserved_keys: dict[str, Any] = field(default_factory=dict)
    overwritten_keys: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    plan: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            **dict(self.plan),
            "guild_id": self.guild_id,
            "applied": self.applied,
            "profile": self.profile,
            "created_keys": dict(self.created_keys),
            "preserved_keys": dict(self.preserved_keys),
            "overwritten_keys": dict(self.overwritten_keys),
            "warnings": list(self.warnings),
            "suggestions": [dict(item) for item in self.suggestions],
        }
        data["applied_channels"] = _legacy_section(
            self.created_keys, "channels", self.overwritten_keys
        )
        data["preserved_channels"] = _legacy_section(self.preserved_keys, "channels")
        data["applied_roles"] = _legacy_section(
            self.created_keys, "roles", self.overwritten_keys
        )
        data["preserved_roles"] = _legacy_section(self.preserved_keys, "roles")
        return data

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())


def validate_guild_adaptation_profile(
    profile: str | None,
) -> GuildAdaptationProfile:
    """Return a validated profile name or raise ``ValueError``."""
    selected = profile or "standard"
    if selected not in VALID_GUILD_ADAPTATION_PROFILES:
        valid = ", ".join(VALID_GUILD_ADAPTATION_PROFILES)
        raise ValueError(
            f"Invalid guild adaptation profile {selected!r}. "
            f"Expected one of: {valid}."
        )
    return selected  # type: ignore[return-value]


def _legacy_section(
    primary: Mapping[str, Any],
    section: str,
    secondary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for source in (primary, secondary or {}):
        prefix = f"{section}."
        for key, value in source.items():
            if key.startswith(prefix):
                result[key[len(prefix):]] = value
    return result


def _normalize_name(value: object) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _score_name(name: str, aliases: Iterable[str]) -> float:
    if not name:
        return 0.0
    tokens = set(filter(None, name.split("-")))
    best = 0.0
    for alias in aliases:
        alias_name = _normalize_name(alias)
        alias_tokens = set(filter(None, alias_name.split("-")))
        if name == alias_name:
            best = max(best, 1.0)
        elif name.endswith(f"-{alias_name}") or name.startswith(f"{alias_name}-"):
            best = max(best, 0.92)
        elif alias_name in name:
            best = max(best, 0.82)
        elif alias_tokens and alias_tokens <= tokens:
            best = max(best, 0.72)
    return best


def _confidence(score: float) -> str:
    if score >= 0.95:
        return "high"
    if score >= 0.75:
        return "medium"
    return "low"


def _named_items(values: Iterable[Any]) -> list[Any]:
    return [
        item
        for item in values
        if getattr(item, "id", None) is not None and getattr(item, "name", None)
    ]


def _iter_channels(guild: Any) -> list[Any]:
    text_channels = getattr(guild, "text_channels", None)
    if text_channels is not None:
        return _named_items(text_channels)
    return _named_items(getattr(guild, "channels", []) or [])


def _iter_roles(guild: Any) -> list[Any]:
    roles = []
    for role in getattr(guild, "roles", []) or []:
        name = _normalize_name(getattr(role, "name", ""))
        if name in {"everyone", "here"}:
            continue
        roles.append(role)
    return _named_items(roles)


def _best_match(items: list[Any], aliases: tuple[str, ...]) -> tuple[Any | None, float]:
    best_item = None
    best_score = 0.0
    for item in items:
        score = _score_name(_normalize_name(getattr(item, "name", "")), aliases)
        if score > best_score:
            best_item = item
            best_score = score
    return best_item, best_score


def _suggestions_for(
    *,
    items: list[Any],
    patterns: Mapping[str, tuple[str, ...]],
    allowed_keys: set[str],
    section: str,
    threshold: float,
) -> tuple[dict[str, int], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    planned: dict[str, int] = {}
    matches: list[dict[str, Any]] = []
    suggestions: list[dict[str, Any]] = []
    low_confidence: list[dict[str, Any]] = []
    for key, aliases in patterns.items():
        if key not in allowed_keys:
            continue
        item, score = _best_match(items, aliases)
        if item is None or score <= 0:
            continue
        value = int(getattr(item, "id"))
        name = str(getattr(item, "name", ""))
        suggestion = GuildAdaptationSuggestion(
            key=key,
            value=value,
            confidence=round(score, 2),
            reason=f"Matched {section[:-1]} named {name!r}.",
            source=name,
            section=section,
            name=name,
        ).to_dict()
        suggestions.append(suggestion)
        matches.append(
            {
                "kind": section[:-1],
                "key": key,
                "id": value,
                "name": name,
                "confidence": round(score, 2),
                "confidence_label": _confidence(score),
            }
        )
        if score >= threshold:
            planned[key] = value
        else:
            low_confidence.append(suggestion)
    return planned, matches, suggestions, low_confidence


def _channel_prefix_hints(channels: list[Any]) -> dict[str, int]:
    prefixes: Counter[str] = Counter()
    allowed = {"mod", "staff", "bot", "ticket", "rules", "welcome"}
    for channel in channels:
        name = _normalize_name(getattr(channel, "name", ""))
        if "-" not in name:
            continue
        prefix = name.split("-", 1)[0]
        if prefix in allowed:
            prefixes[prefix] += 1
    return dict(sorted(prefixes.items()))


def _locale_hints(guild: Any) -> dict[str, str]:
    hints: dict[str, str] = {}
    for attr in ("preferred_locale", "guild_locale", "locale"):
        value = getattr(guild, attr, None)
        if value:
            hints[attr] = str(value)
    return hints


def _feature_toggles(channels: Mapping[str, int]) -> dict[str, bool]:
    return {
        "member_logging": "logging" in channels,
        "welcome_messages": "welcome" in channels,
        "support_workflow": "support" in channels,
        "starboard": "starboard" in channels,
    }


def _onboarding_hints(channels: Mapping[str, int], roles: Mapping[str, int]) -> list[str]:
    hints = ["Run /easycord setup review to inspect inferred configuration."]
    if "logging" in channels:
        hints.append("Confirm the logging channel before enabling moderation logs.")
    if "welcome" in channels:
        hints.append("Enable optional welcome messages after reviewing the welcome channel.")
    if "admin" not in roles and "moderator" not in roles:
        hints.append("Configure admin or moderator role keys for role-gated commands.")
    return hints


def plan_guild_adaptation(
    guild: Any,
    profile: GuildAdaptationProfile | str = "standard",
) -> dict[str, Any]:
    """Infer useful per-guild config from cached channel and role names.

    The helper is offline-only: it reads the supplied guild object's cached
    ``text_channels``/``channels`` and ``roles`` attributes and never creates,
    edits, or fetches Discord resources.
    """
    selected = validate_guild_adaptation_profile(profile)
    threshold = _PROFILE_THRESHOLDS[selected]
    profile_keys = _PROFILE_KEYS[selected]
    channels = _iter_channels(guild)
    roles = _iter_roles(guild)

    inferred_channels, channel_matches, channel_suggestions, low_channels = _suggestions_for(
        items=channels,
        patterns=_CHANNEL_PATTERNS,
        allowed_keys=profile_keys["channels"],
        section="channels",
        threshold=threshold,
    )
    inferred_roles, role_matches, role_suggestions, low_roles = _suggestions_for(
        items=roles,
        patterns=_ROLE_PATTERNS,
        allowed_keys=profile_keys["roles"],
        section="roles",
        threshold=threshold,
    )

    warnings: list[str] = []
    if "logging" not in inferred_channels:
        warnings.append(
            "No high-confidence logging channel was detected. Create a channel "
            "like #mod-logs or configure the logging channel manually."
        )
    if "admin" not in inferred_roles and "moderator" not in inferred_roles:
        warnings.append(
            "No high-confidence admin or moderator role was detected by name. "
            "Configure role keys manually before using role-gated commands."
        )

    hints = {}
    if selected in {"standard", "aggressive"}:
        hints = {
            "feature_toggles": _feature_toggles(inferred_channels),
            "locale_hints": _locale_hints(guild),
            "channel_prefixes": _channel_prefix_hints(channels),
            "onboarding_hints": _onboarding_hints(inferred_channels, inferred_roles),
        }

    low_confidence = low_channels + low_roles
    suggestions = channel_suggestions + role_suggestions
    return {
        "ok": bool(inferred_channels or inferred_roles),
        "guild_id": int(getattr(guild, "id", 0) or 0),
        "guild_name": str(getattr(guild, "name", "")),
        "profile": selected,
        "threshold": threshold,
        "channels": inferred_channels,
        "roles": inferred_roles,
        "matches": channel_matches + role_matches,
        "warnings": warnings,
        "suggestions": suggestions,
        "low_confidence_suggestions": low_confidence,
        "hints": hints,
    }


def _section_from_config(config: Any, section: str) -> dict[str, Any]:
    if hasattr(config, f"list_{section}"):
        return dict(getattr(config, f"list_{section}")())
    if isinstance(config, Mapping):
        raw = config.get(section, {})
        return dict(raw) if isinstance(raw, Mapping) else {}
    return {}


def diff_guild_adaptation(
    existing_config: Any,
    planned_config: Mapping[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Return a dry-run diff between existing config and an adaptation plan."""
    added: dict[str, Any] = {}
    preserved: dict[str, Any] = {}
    overwritten: dict[str, Any] = {}
    for section in ("channels", "roles"):
        existing = _section_from_config(existing_config, section)
        planned = dict(planned_config.get(section, {}))
        for key, value in planned.items():
            flat_key = f"{section}.{key}"
            if key not in existing:
                added[flat_key] = value
            elif overwrite and existing[key] != value:
                overwritten[flat_key] = value
            else:
                preserved[flat_key] = existing[key]

    return {
        "profile": planned_config.get("profile", "standard"),
        "added": added,
        "preserved": preserved,
        "overwritten": overwritten,
        "warnings": list(planned_config.get("warnings", [])),
        "suggestions": list(planned_config.get("suggestions", [])),
        "low_confidence_suggestions": list(
            planned_config.get("low_confidence_suggestions", [])
        ),
    }


def format_guild_adaptation_summary(plan_or_result: Mapping[str, Any]) -> str:
    """Return a human-readable admin summary for a plan or result."""
    data = (
        plan_or_result.to_dict()
        if hasattr(plan_or_result, "to_dict")
        else dict(plan_or_result)
    )
    profile = data.get("profile", "standard")
    lines = [f"EasyCord adapted to this server using the {profile} profile.", ""]

    channels = dict(data.get("channels", {}))
    roles = dict(data.get("roles", {}))
    lines.append("Detected:")
    if channels or roles:
        for key, value in channels.items():
            lines.append(f"- {key} channel: {value}")
        for key, value in roles.items():
            lines.append(f"- {key} role: {value}")
    else:
        lines.append("- No high-confidence channels or roles were detected.")

    created = dict(data.get("created_keys", {}))
    overwritten = dict(data.get("overwritten_keys", {}))
    applied = {**created, **overwritten}
    lines.extend(["", "Applied config:"])
    if applied:
        for key in sorted(applied):
            lines.append(f"- {key}")
    else:
        legacy = {
            **{f"channels.{k}": v for k, v in dict(data.get("applied_channels", {})).items()},
            **{f"roles.{k}": v for k, v in dict(data.get("applied_roles", {})).items()},
        }
        if legacy:
            for key in sorted(legacy):
                lines.append(f"- {key}")
        else:
            lines.append("- No config keys were applied.")

    preserved = dict(data.get("preserved_keys", {}))
    lines.extend(["", "Preserved existing config:"])
    if preserved:
        for key in sorted(preserved):
            lines.append(f"- {key}")
    else:
        lines.append("- No existing config keys were preserved.")

    lines.extend(
        [
            "",
            "No Discord channels, roles, categories, permissions, or messages were changed.",
            "",
            "Suggested next steps:",
        ]
    )
    hints = data.get("hints", {})
    onboarding = hints.get("onboarding_hints", []) if isinstance(hints, Mapping) else []
    next_steps = list(onboarding) or [
        "Run /easycord setup review.",
        "Confirm logging and moderation channels.",
        "Enable optional welcome messages after review.",
    ]
    for step in next_steps:
        lines.append(f"- {step}")
    for warning in data.get("warnings", []):
        lines.append(f"- {warning}")
    return "\n".join(lines)


__all__ = [
    "GuildAdaptationProfile",
    "GuildAdaptationResult",
    "GuildAdaptationSuggestion",
    "VALID_GUILD_ADAPTATION_PROFILES",
    "diff_guild_adaptation",
    "format_guild_adaptation_summary",
    "plan_guild_adaptation",
    "validate_guild_adaptation_profile",
]
