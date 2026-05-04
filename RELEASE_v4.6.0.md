# EasyCord v4.6.0 Release Notes

**Release Date:** May 4, 2026
**Status:** Stable
**Tests:** 691 passing

## Overview

v4.6.0 is a maintenance and architecture release. It fixes async deprecation warnings in all AI providers, improves bulk moderation logging, removes a dead decorator parameter, and splits the i18n module into a clean sub-package.

---

## Bug Fixes

- **`asyncio.get_event_loop()` deprecation** — All AI provider `query()` methods now use `asyncio.get_running_loop()` as required inside async functions (Python 3.10+). Affected providers: Anthropic, OpenAI, Gemini, Groq, Mistral, HuggingFace, Together, Ollama, LiteLLM.
- **Bulk moderation logging** — `bulk_timeout`, `bulk_role_add`, and `bulk_role_remove` now log failures at `WARNING` level instead of swallowing them silently.
- **Test suite fixes** — 14 broken tests fixed (mock paths updated for i18n sub-package split, provider test mocks updated for SDK API changes, plugin reload tests fixed for property semantics).

## Breaking Changes

- **Removed `rate_limit` parameter from `@slash` decorator** — It was stored on the method but never acted on by the framework. Use the `cooldown` parameter instead, which has always been the functional rate-limiting mechanism.

## Architecture

- **`easycord/i18n.py` → `easycord/i18n/` sub-package** — The i18n module has been split into focused files (`_manager.py`, `_types.py`, `_diagnostics.py`, `_utils.py`). All public API remains unchanged — existing `from easycord.i18n import LocalizationManager` imports continue to work.
- **Plugin command registry** — Every slash command registered via a plugin is now tracked in `bot.registry.commands` with its name, description, owning plugin, and guild scope. Use `bot.registry.list_commands()` or `bot.registry.commands_for_plugin("MyPlugin")` to inspect at runtime.

---

## Installation

```bash
# From GitHub (stable)
pip install "easycord @ git+https://github.com/rolling-codes/EasyCord.git@v4.6.0"

# From source
git clone --branch v4.6.0 https://github.com/rolling-codes/EasyCord.git
cd EasyCord
pip install -e ".[dev]"
```

---

## Test Results

| Category | Count | Status |
|----------|-------|--------|
| Core framework tests | 691 | ✅ PASS |
| Regressions | 0 | ✅ |

---

## Release Links

- **GitHub Release:** https://github.com/rolling-codes/EasyCord/releases/tag/v4.6.0
- **Previous (v4.5.0-beta.3):** https://github.com/rolling-codes/EasyCord/releases/tag/v4.5.0-beta.3
