## EasyCord v5.4.0 - 2026-05-10

### Added
- Stable JSON contracts for `easycord doctor --json`, `easycord inspect --json`, `easycord sync-plan --json`, and `easycord audit-tools --json`.
- Project scaffold templates via `easycord new --template minimal|plugin|ai|database`.
- Template discovery via `easycord new --list-templates`.
- Actionable doctor diagnostics with stable `code`, `severity`, and `fix` fields.
- Offline AI tool safety auditing via `easycord audit-tools`, `audit_tool_registry()`, and `format_tool_audit()`.
- CI-friendly AI safety gates via `easycord audit-tools --fail-on-warnings`.
- `FakeContextBuilder` plus `with_roles()` for fluent offline command and tool tests.

### Compatibility
- Existing CLI commands, flags, formatter exports, testing helpers, and default `easycord new` behavior are preserved.
- CLI commands remain dependency-free and avoid live Discord or AI-provider side effects by default.
- AI tool audits are advisory by default and do not change runtime tool execution.

### Verification
- `python -m compileall -q easycord tests`
- `pytest tests/ -q`
- `python -m build`
- `python -m twine check dist/*`
