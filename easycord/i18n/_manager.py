"""LocalizationManager: locale resolution, fallback chains, and auto-translation."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Callable

from ._diagnostics import LocalizationDiagnostics
from ._types import DiagnosticMode, TranslationValidationReport
from ._utils import _normalize_locale, detect_os_locale

logger = logging.getLogger("easycord.i18n")
trace_logger = logging.getLogger("easycord.i18n.trace")


class LocalizationManager:
    """Store and resolve string templates by locale.

    The manager keeps a dictionary of catalogs keyed by locale string. A lookup
    checks the interaction locale first, then the guild locale, then the
    configured default locale, and finally a simple language-only fallback
    (for example ``pt-BR`` → ``pt``).

    Thread Safety:
    This class is NOT thread-safe. It assumes single-threaded access within
    a request/event scope. Metrics and diagnostics state use non-atomic counters.
    For concurrent access (e.g., sharded deployments, async locale providers),
    external synchronization is required.
    """

    def __init__(
        self,
        *,
        default_locale: str = "en-US",
        translations: Mapping[str, Mapping[str, str]] | None = None,
        auto_translator: Callable[[str, str, str], str | None] | None = None,
        auto_detect_system_locale: bool = False,
        warn_invalid_locale: bool = True,
        diagnostic_mode: DiagnosticMode = DiagnosticMode.SILENT,
        track_metrics: bool = False,
        max_auto_translated_locales: int = 50,
        max_tracked_locales: int = 100,
    ) -> None:
        self.default_locale = _normalize_locale(default_locale) or "en-US"
        self._catalogs: dict[str, dict[str, str]] = {}
        self._auto_translator = auto_translator
        self._auto_detect_system_locale = auto_detect_system_locale
        self._warn_invalid_locale = warn_invalid_locale
        self._system_locale: str | None = None
        self.diagnostics = LocalizationDiagnostics(mode=diagnostic_mode)
        self.track_metrics = track_metrics
        self._max_auto_translated = max_auto_translated_locales
        self._max_tracked_locales = max_tracked_locales
        self._auto_translated_count = 0
        self._metrics: dict[str, int] = {
            "cache_hits": 0,
            "cache_misses": 0,
            "fallback_resolution": 0,
            "missing_keys": 0,
            "auto_translated": 0,
            "locale_frequency": {},
        } if track_metrics else {}
        self._chain_cache: dict[str, list[str]] = {}
        if auto_detect_system_locale:
            self._system_locale = detect_os_locale()
            if self._system_locale:
                logger.debug(f"Detected system locale: {self._system_locale}")
        for locale, values in (translations or {}).items():
            self.register(locale, values)

    def register(self, locale: Any, translations: Mapping[str, str]) -> None:
        """Register or merge a locale catalog."""
        normalized = _normalize_locale(locale)
        if normalized is None:
            raise ValueError("locale must be a non-empty string")
        self._catalogs.setdefault(normalized, {}).update(
            {str(key): str(value) for key, value in translations.items()}
        )

    def locales(self) -> list[str]:
        """Return the known locale tags."""
        return sorted(self._catalogs)

    def get_metrics(self) -> dict[str, int | dict]:
        """Get resolution metrics (only if track_metrics=True).

        Returns IMMUTABLE deep snapshot to prevent caller mutation of internal state.
        """
        if not self.track_metrics:
            return {}
        return {
            "cache_hits": self._metrics["cache_hits"],
            "cache_misses": self._metrics["cache_misses"],
            "fallback_resolution": self._metrics["fallback_resolution"],
            "auto_translated": self._metrics["auto_translated"],
            "missing_keys": self._metrics["missing_keys"],
            "locale_frequency": dict(self._metrics["locale_frequency"]),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics to zero (for per-session tracking)."""
        if self.track_metrics:
            self._metrics["cache_hits"] = 0
            self._metrics["cache_misses"] = 0
            self._metrics["fallback_resolution"] = 0
            self._metrics["auto_translated"] = 0
            self._metrics["missing_keys"] = 0
            self._metrics["locale_frequency"] = {}
        self._auto_translated_count = 0

    def resolve_chain(
        self,
        locale: Any = None,
        *,
        guild_locale: Any = None,
    ) -> list[str]:
        """Return the fallback chain for a locale lookup (with memoization)."""
        normalized_locale = _normalize_locale(locale)
        normalized_guild = _normalize_locale(guild_locale)

        if normalized_locale is None and normalized_guild is None:
            cache_key = (None, None, True)
        else:
            cache_key = (normalized_locale, normalized_guild, False)

        if cache_key in self._chain_cache:
            return self._chain_cache[cache_key]

        chain: list[str] = []
        if normalized_locale is None and normalized_guild is None:
            candidates = [self.default_locale]
        else:
            candidates = [normalized_locale, normalized_guild, self.default_locale]

        for candidate in candidates:
            if not candidate:
                continue
            parts = candidate.split("-")
            for index in range(len(parts), 0, -1):
                value = "-".join(parts[:index])
                if value not in chain:
                    chain.append(value)

        if len(self._chain_cache) < 1000:
            self._chain_cache[cache_key] = chain
        return chain

    def auto_detect_locale(
        self,
        user_locale: Any = None,
        guild_locale: Any = None,
    ) -> str | None:
        """Detect the best locale using auto-detection chain."""
        candidates = [
            _normalize_locale(user_locale),
            _normalize_locale(guild_locale),
            self._system_locale,
            self.default_locale,
        ]

        for candidate in candidates:
            if not candidate:
                continue
            if not self._is_valid_locale(candidate):
                if self._warn_invalid_locale:
                    logger.warning(f"Invalid or unsupported locale: {candidate}")
                continue
            chain = self.resolve_chain(candidate)
            for loc in chain:
                if loc in self._catalogs:
                    return loc

        return self.default_locale if self.default_locale in self._catalogs else None

    def _is_valid_locale(self, locale: str) -> bool:
        """Check if locale format is valid (BCP 47 support)."""
        if not locale or not isinstance(locale, str):
            return False

        parts = locale.split("-")
        if not parts[0] or len(parts[0]) < 2 or len(parts[0]) > 3:
            return False

        if len(parts) == 1:
            return True

        second = parts[1]
        if not second:
            return False

        if len(second) == 4:
            if len(parts) == 2:
                return True
            if len(parts) == 3:
                third = parts[2]
                return len(third) == 2
            return False

        if len(second) == 2:
            return len(parts) == 2

        return False

    def _trace_resolution(
        self,
        key: str,
        raw_locale: Any,
        normalized_locale: str | None,
        guild_locale: Any,
        resolved_locale: str | None,
        fallback_chain: list[str],
        found_in: str | None,
        cache_hit: bool,
    ) -> None:
        """Trace locale resolution path (debug-only telemetry)."""
        if not trace_logger.isEnabledFor(logging.DEBUG):
            return

        trace_logger.debug(
            f"[{key}] "
            f"raw_locale={raw_locale!r} "
            f"normalized={normalized_locale!r} "
            f"guild={guild_locale!r} "
            f"resolved={resolved_locale!r} "
            f"chain={fallback_chain!r} "
            f"found_in={found_in!r} "
            f"cache_hit={cache_hit}"
        )

    def validate_completeness(
        self, base_locale: str | None = None
    ) -> TranslationValidationReport:
        """Validate translation completeness against a base locale."""
        base = base_locale or self.default_locale
        if base not in self._catalogs:
            raise ValueError(f"Base locale '{base}' not registered")

        base_keys = set(self._catalogs[base].keys())
        report = TranslationValidationReport(base)

        for locale in sorted(self._catalogs.keys()):
            if locale == base:
                report.add_locale(locale, [], [], 1.0)
                continue

            locale_keys = set(self._catalogs[locale].keys())
            missing_keys = sorted(base_keys - locale_keys)
            orphaned_keys = sorted(locale_keys - base_keys)
            coverage = (len(locale_keys & base_keys) / len(base_keys)) if base_keys else 1.0

            report.add_locale(locale, missing_keys, orphaned_keys, coverage)

        return report

    def get(
        self,
        key: str,
        *,
        locale: Any = None,
        guild_locale: Any = None,
        default: str | None = None,
    ) -> str:
        """Look up a translated string and fall back safely if missing."""
        requested_locale = _normalize_locale(locale)
        guild_normalized = _normalize_locale(guild_locale)
        found_in = None
        is_cache_hit = False

        preferred_chain: list[str] = []
        for candidate in (requested_locale, guild_normalized):
            if not candidate:
                continue
            parts = candidate.split("-")
            for index in range(len(parts), 0, -1):
                value = "-".join(parts[:index])
                if value not in preferred_chain:
                    preferred_chain.append(value)

        for candidate in preferred_chain:
            catalog = self._catalogs.get(candidate)
            if catalog and key in catalog:
                found_in = candidate
                is_cache_hit = True
                if self.track_metrics:
                    self._metrics["cache_hits"] += 1
                    self._update_locale_frequency(candidate)
                self._trace_resolution(
                    key, locale, requested_locale, guild_locale, candidate,
                    preferred_chain, candidate, True
                )
                return catalog[key]

        if self.track_metrics:
            self._metrics["cache_misses"] += 1

        auto_translated = self._auto_translate_missing(
            key,
            locale=locale,
            guild_locale=guild_locale,
            default=default,
        )
        if auto_translated is not None:
            found_in = "auto_translator"
            if self.track_metrics:
                self._metrics["auto_translated"] += 1
                if requested_locale:
                    self._update_locale_frequency(requested_locale)
            self._trace_resolution(
                key, locale, requested_locale, guild_locale, requested_locale,
                preferred_chain, "auto_translator", False
            )
            return auto_translated

        default_chain = self.resolve_chain(self.default_locale)
        for candidate in default_chain:
            catalog = self._catalogs.get(candidate)
            if catalog and key in catalog:
                found_in = candidate
                if self.track_metrics:
                    self._metrics["fallback_resolution"] += 1
                    self._update_locale_frequency(candidate)
                if requested_locale:
                    self.diagnostics.report_missing_key(
                        key, requested_locale, fallback_locale=candidate
                    )
                self._trace_resolution(
                    key, locale, requested_locale, guild_locale, candidate,
                    default_chain, candidate, False
                )
                return catalog[key]

        if self.track_metrics:
            self._metrics["missing_keys"] += 1
        if requested_locale:
            self.diagnostics.report_missing_key(key, requested_locale)
        self._trace_resolution(
            key, locale, requested_locale, guild_locale, None,
            default_chain, None, False
        )
        return default if default is not None else key

    def _update_locale_frequency(self, locale: str) -> None:
        """Update locale frequency metrics with bounds checking."""
        freq = self._metrics["locale_frequency"]
        freq[locale] = freq.get(locale, 0) + 1

        if len(freq) > self._max_tracked_locales:
            min_locale = min(freq, key=freq.get)
            del freq[min_locale]

    def _find_source_for_key(
        self,
        key: str,
        *,
        default: str | None,
    ) -> tuple[str, str] | None:
        for candidate in self.resolve_chain(self.default_locale):
            catalog = self._catalogs.get(candidate)
            if catalog and key in catalog:
                return candidate, catalog[key]

        if default is not None:
            return self.default_locale, default

        for candidate in sorted(self._catalogs):
            catalog = self._catalogs[candidate]
            if key in catalog:
                return candidate, catalog[key]
        return None

    def _auto_translate_missing(
        self,
        key: str,
        *,
        locale: Any = None,
        guild_locale: Any = None,
        default: str | None = None,
    ) -> str | None:
        if self._auto_translator is None:
            return None

        target_locale = _normalize_locale(locale) or _normalize_locale(guild_locale)
        if target_locale is None:
            return None

        source = self._find_source_for_key(key, default=default)
        if source is None:
            return None
        source_locale, source_text = source
        if source_locale == target_locale:
            return None

        translated = self._auto_translator(source_text, source_locale, target_locale)
        if not translated:
            return None

        if self._auto_translated_count < self._max_auto_translated:
            self.register(target_locale, {key: translated})
            self._auto_translated_count += 1
        return translated

    def format(
        self,
        key: str,
        *,
        locale: Any = None,
        guild_locale: Any = None,
        default: str | None = None,
        **kwargs,
    ) -> str:
        """Look up a translated string and format it with keyword arguments."""
        template = self.get(
            key,
            locale=locale,
            guild_locale=guild_locale,
            default=default,
        )
        return template.format(**kwargs)
