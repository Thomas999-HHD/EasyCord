# v3.8.0 — Optional AI & Production Clarity

**Release Date:** 2026-04-25

## Summary

EasyCord v3.8.0 clarifies positioning and expands documentation for production usage. **AI is now explicitly optional**—you can build fully-featured bots without any AI dependencies.

This is a **zero-breaking-change release**. All existing bots work unchanged.

## What Changed

### Positioning

- **Repositioned AI as optional, not default.** EasyCord is now a "modern Discord framework with optional AI capabilities," not an "AI-native framework."
- **Emphasized non-AI workflows.** Core bot features (commands, events, moderation, logging) are first-class and don't depend on AI.
- **Added explicit "No AI required" messaging** throughout README and documentation.

### Documentation

**New guides:**
- [`docs/quickstart-production.md`](docs/quickstart-production.md) — Canonical production bot example (150 lines). Shows plugins, events, member logging, AI moderation, error handling. Demonstrates the intended EasyCord way.
- [`docs/migration-from-discord.py.md`](docs/migration-from-discord.py.md) — Side-by-side comparison with concrete wins ("removes boilerplate," "prevents decorator chains"). Includes migration checklist and "what you can delete" section.
- [`docs/security-best-practices.md`](docs/security-best-practices.md) — Comprehensive security guide. Covers token management, permissions, AI guardrails (prompt injection, tool sandboxing, failure modes), error handling, and deployment.
- [`docs/performance-tuning.md`](docs/performance-tuning.md) — Optimization guide for command latency, memory usage, database efficiency, and concurrent throughput.
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — Searchable guide to common issues with solutions. Covers bot startup, command sync, moderation, database, events, permissions, AI orchestration.
- [`docs/stability-and-scope.md`](docs/stability-and-scope.md) — Explicit API stability guarantees, intentional gaps (threads, voice, auth), extension surface, and upgrade safety.

**Enhanced guides:**
- [`docs/api.md`](docs/api.md) — Added 5 major sections: Helper Libraries, Scheduled Events, Invite Management, AI & Orchestration (with safety model), Conversation Memory, and Advanced Decorators.
- [`docs/index.md`](docs/index.md) — Reorganized with "Guides & References" section. Added note that AI features are completely optional.

### Examples

**New example:**
- [`examples/core-bot.py`](examples/core-bot.py) — 60-line production-ready bot with zero AI dependencies. Demonstrates slash commands, events, member logging, per-guild config, error handling. **Proves framework stands alone.**

### Code

**No code changes.** This release is documentation, examples, and positioning only. All existing functionality remains unchanged.

## Why This Release

### Problem

EasyCord v3.7 was feature-complete but poorly positioned:
- AI was presented as central to the framework
- Non-AI users worried they'd need to understand orchestration, tools, and LLM providers
- Compliance teams couldn't adopt due to perceived AI requirement
- Simple bots felt over-engineered

### Solution

v3.8 separates:
- **Core framework** — commands, events, plugins, moderation, logging (required, non-optional)
- **AI layer** — Orchestrator, tools, LLM providers (completely optional add-on)

### Result

Removes adoption friction for:
- ✅ Hobbyists who just want a simple bot
- ✅ Teams with compliance restrictions (no external APIs)
- ✅ Orgs migrating from discord.py (want stability first, AI later)
- ✅ Budget-conscious teams (LLM API costs)
- ✅ High-throughput bots (latency requirements)

Without sacrificing differentiation—AI features still there, just positioned as upgrade path.

## Migration (None Required)

All changes are **additive and non-breaking**:

- Existing bots work unchanged
- No dependency updates required
- No code rewrites
- No API changes

If you want to adopt new documentation:
```bash
pip install --upgrade easycord
# That's it. Your bot continues working.
```

## Key Messaging

### For new users

"Build Discord bots without AI. Add AI when you need it."

### For existing users

"No breaking changes. AI features remain fully compatible."

### For teams

"Production-ready framework for Discord bots. AI is optional."

## What's Next

v3.9+ will focus on **removing friction from production usage**:

1. **Built-in observability** — structured logging, metrics (Prometheus-compatible)
2. **Config system** — .env + typed config + per-environment overrides
3. **Plugin marketplace** — packaging convention + version compatibility
4. **Testing utilities** — mock context, simulated events, command testing
5. **State/persistence abstraction** — lightweight `await ctx.store.get/set()`
6. **CLI tooling** — `easycord new`, `easycord run`, `easycord doctor`

These follow the same philosophy: remove decisions, make production easier.

## Acknowledgments

This release reflects feedback from teams deploying EasyCord to production and users evaluating whether EasyCord fits their use case.

The repositioning is strategic, not defensive—EasyCord's AI capabilities are genuinely powerful. They're just not required.

## Links

- [Quick Start](docs/getting-started.md)
- [Production Bot Example](docs/quickstart-production.md)
- [Core Bot (No AI)](examples/core-bot.py)
- [Migration Guide](docs/migration-from-discord.py.md)
- [Security Best Practices](docs/security-best-practices.md)
- [Stability Guarantees](docs/stability-and-scope.md)
