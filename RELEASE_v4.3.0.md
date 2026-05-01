# v4.3.0 — Slash Rate Limits and Safer Plugin Cleanup

**Release Date:** 2026-05-01

## Summary

v4.3.0 closes two easy-to-miss edge cases and sharpens the plugin authoring flow without changing the overall framework model.

## What Changed

### Slash command validation

- Added command-level `rate_limit=(limit, window)` support to `@slash` / `Bot.slash`.
- Validates rate-limit input up front so invalid values fail fast instead of silently doing nothing.
- Deduplicates slash aliases so repeated names no longer double-register.

### Plugin unload cleanup

- `@on(..., on_cleanup=...)` cleanup callbacks now run when a plugin unloads.
- Cleanup functions are invoked once per plugin even if multiple handlers share the same callback.

### Release handoff

- Updated the model files and release docs to match the current 4.3.0 state.
- Moved the live workspace to a Desktop junction so the project is available at `C:\Users\Tom\Desktop\LSPDFRManager-1.1.1`.

## Testing

- `pytest tests/test_decorators.py tests/test_plugin.py tests/test_bot.py`
- `pytest` (`619 passed`)
