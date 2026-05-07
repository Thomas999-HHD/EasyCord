# Dynamic Component Routing

EasyCord v5.2 component handlers can use typed custom ID patterns.

```python
from easycord import Plugin, component

class TicketPlugin(Plugin):
    @component("ticket:close:{ticket_id:int}")
    async def close_ticket(self, ctx, ticket_id: int):
        await ctx.respond(f"Closing ticket {ticket_id}", ephemeral=True)
```

Supported route types:

- `str`
- `int`
- `snowflake`

Poll buttons can carry multiple IDs:

```python
@component("poll:vote:{poll_id:int}:{choice_id:int}")
async def vote(ctx, poll_id: int, choice_id: int):
    await ctx.respond("Vote recorded.", ephemeral=True)
```

Malformed IDs are ignored safely. Static and dynamic component IDs are checked
for collisions when registered.

## TTL

Use `ttl=` for temporary in-process routes:

```python
@component("wizard:{session_id:snowflake}:next", ttl=300)
async def next_step(ctx, session_id: int):
    ...
```

Routes without `ttl` are persistent and can be re-registered during startup.
Routes with `ttl` are intended for short-lived flows and expire without
dispatching after their deadline.
