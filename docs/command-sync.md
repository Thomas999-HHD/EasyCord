# Command Sync

EasyCord v5.2 adds a command sync planner so developers can preview what would
change before syncing with Discord.

```python
plan = bot.plan_command_sync(remote_commands=["old_ping"])
print(plan)
```

The plan contains:

- `added`
- `changed`
- `removed`
- `unchanged`
- `warnings`

Run a dry-run sync in tests or startup diagnostics:

```python
plan = await bot.sync_commands(dry_run=True, remote_commands=["old_ping"])
```

Actual sync still uses `discord.app_commands.CommandTree`:

```python
await bot.sync_commands()
```

If a plan includes remote removals, EasyCord requires an explicit confirmation:

```python
await bot.sync_commands(
    remote_commands=["old_ping"],
    confirm_removals=True,
)
```

For development guild syncs:

```python
await bot.sync_commands(guild_id=123456789012345678)
```

Guild sync copies global commands into the target guild before syncing so local
iteration stays fast without publishing global commands.
