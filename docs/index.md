# Documentation

EasyCord is a **unified Discord bot framework** — not just a decorator layer or command handler. It provides a complete system for building production bots with commands, events, moderation, configuration, plugins, and AI orchestration all integrated.

The documentation is organized around one beginner-friendly path: install the package, make one command, then grow into plugins, features, and AI agents.

## Start here

1. [`getting-started.md`](getting-started.md) — create a bot, run it, and organize the first files (5 minutes).
2. [`framework.md`](framework.md) — understand EasyCord as a unified system, not just slash commands (philosophy + architecture).
3. [`concepts.md`](concepts.md) — learn slash commands, events, middleware, and plugins.
4. [`examples.md`](examples.md) — copy smaller patterns into your own bot.
5. [`fork-and-expand.md`](fork-and-expand.md) — turn a starter bot into a real project structure.
6. [`api.md`](api.md) — reference signatures when you already know what you want to build.
7. [`release-notes.md`](release-notes.md) — summary of the latest refactor and feature update.

## Guides & References

**The canonical pattern:**
- [`quickstart-production.md`](quickstart-production.md) — build a complete production-ready bot end-to-end (150 lines, plugins + AI + error handling). Shows the intended EasyCord way.

**For specific tasks:**
- [`migration-from-discord.py.md`](migration-from-discord.py.md) — moving an existing discord.py bot to EasyCord (side-by-side comparison, "what you can delete" checklist).
- [`security-best-practices.md`](security-best-practices.md) — token management, permissions, input validation, AI tool safety (with safety pipeline model), and production deployment.
- [`performance-tuning.md`](performance-tuning.md) — optimize command latency, memory usage, database queries, and concurrent throughput.
- [`troubleshooting.md`](troubleshooting.md) — common issues (bot won't start, commands don't appear, permissions fail) and solutions.
- [`stability-and-scope.md`](stability-and-scope.md) — what's frozen (won't break in v4.x), what's intentional gaps, extension surface, upgrade safety.

## What this removes

| Beginner pain | This framework answer |
| --- | --- |
| Building and syncing a command tree | `@bot.slash(...)` |
| Writing the same permission checks repeatedly | Permission guards on the decorator |
| Repeating rate-limit and logging setup | Middleware once for the whole bot |
| Wiring buttons and selects by hand | `@bot.component(...)` |
| Growing from one file into a larger bot | Plugins and a simple folder layout |
| Building moderation from scratch | `ModerationPlugin` (rule-based) + `AIModeratorPlugin` (optional) |
| Managing per-guild config without a database | `ServerConfigStore` or `PluginConfigManager` |
| Handling member events, logging, welcome messages | `MemberLoggingPlugin`, `WelcomePlugin`, etc. |
| Scaling to AI agents (optional) | `Orchestrator`, `@ai_tool`, tool registry (not required) |

**Note:** AI features are completely optional. You can build fully-featured bots without any AI dependencies. See [`examples/core-bot.py`](../examples/core-bot.py) and [`docs/security-best-practices.md#when-not-to-use-ai-integration`](security-best-practices.md#when-not-to-use-ai-integration) for when to skip AI.

## Suggested learning order

- Make the starter bot in [`getting-started.md`](getting-started.md)
- Copy [`examples/basic_bot.py`](../examples/basic_bot.py)
- Add one plugin from [`examples/plugin_bot.py`](../examples/plugin_bot.py)
- Read [`concepts.md`](concepts.md) only after you have a bot running

## Design goals

1. **Make the first bot obvious.** One command should take 10 lines. Slash commands, events, and responses should feel natural.
2. **Unified system, not framework sprawl.** Commands, events, moderation, configuration, and AI orchestration should integrate seamlessly — no "pick your own middleware" or "choose your config store" paralysis.
3. **Plugins as first-class architecture.** As bots grow, plugins should feel like the natural way to organize features. Plugins shouldn't need to know about each other.
4. **Production-ready out of the box.** Moderation, logging, role assignment, leveling — ship with solid plugins you can use immediately, not tutorials on how to build them.
5. **Scale to AI agents.** Once a bot is useful, let it become intelligent. Tool calling, multi-provider LLMs, permission gates — all built-in.
