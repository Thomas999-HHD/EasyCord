"""Localization package for EasyCord.

Public API — all names importable directly from ``easycord.i18n``:

    from easycord.i18n import LocalizationManager, DiagnosticMode
"""
from ._types import DiagnosticMode, TranslationValidationReport
from ._utils import _normalize_locale, detect_os_locale
from ._diagnostics import LocalizationDiagnostics
from ._manager import LocalizationManager

__all__ = [
    "DiagnosticMode",
    "TranslationValidationReport",
    "LocalizationDiagnostics",
    "LocalizationManager",
    "_normalize_locale",
    "detect_os_locale",
]
