## EasyCord v5.3.0 - 2026-05-10

### Added
- Dependency-free `easycord` CLI for local development:
  - `easycord new` scaffolds a runnable bot project with a plugin, `.env.example`, project metadata, and pytest coverage.
  - `easycord inspect` prints registered EasyCord interactions from a `module:object` bot target.
  - `easycord sync-plan` previews local command sync changes without contacting Discord.
  - `easycord doctor` checks Python support, `discord.py`, `DISCORD_TOKEN`, optional bot imports, interaction count, and local auto-sync safety.
  - `easycord test-template` generates starter plugin tests.
- Developer-facing formatters:
  - `format_doctor_report()`
  - `format_interaction_inventory()`
  - `format_sync_plan()`
- Offline testing helpers for interaction flows:
  - `invoke_user_command()`
  - `invoke_message_command()`
  - `invoke_component()`
  - `invoke_modal()`
- Developer toolkit documentation in `docs/developer-toolkit.md`.

### Fixed
- `easycord new <path>` now derives scaffold module names from the target folder name instead of the full path.
- Health diagnostics now tolerate offline clients where Discord API latency is unavailable.
- Database environment defaults now use concrete fallback values under slotted dataclasses.

### Compatibility
- CLI commands avoid live Discord side effects by default.
- `sync-plan` only compares local state with manually supplied remote command names.
- Generated projects use `Bot(auto_sync=False)` so imports and tests do not sync commands.

### Verification
- `python -m compileall -q easycord tests`
- `pytest tests/test_release_readiness.py tests/test_public_api.py tests/test_developer_toolkit.py -q`
- `pytest tests/ -q`
- `python -m build`
- `python -m twine check dist/*` when `twine` is available
