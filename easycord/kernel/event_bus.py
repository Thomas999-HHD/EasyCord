"""Async event bus with priority, wildcard subscriptions, and cancellation.

Replaces v3 implicit event handling. Decoupled, pluggable, testable.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Sequence


@dataclass
class Event:
    """Emitted event with optional cancellation."""

    name: str
    data: dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False

    def cancel(self) -> None:
        """Mark event as cancelled. Downstream handlers see this."""
        self.cancelled = True


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Async pub-sub bus with priority ordering and wildcard subscriptions.

    Usage:
        bus = EventBus()

        @bus.on("member.join")
        async def on_member_join(event):
            member = event.data["member"]
            await send_welcome(member)

        @bus.on("member.*")  # Wildcard
        async def on_any_member(event):
            ...

        # Emit
        event = Event("member.join", {"member": member})
        await bus.emit(event)

        # With cancellation
        if not event.cancelled:
            await do_thing()
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[tuple[int, EventHandler]]] = {}
        self._wildcards: dict[str, list[tuple[int, EventHandler]]] = {}

    def on(
        self, pattern: str, priority: int = 0
    ) -> Callable[[EventHandler], EventHandler]:
        """Register handler for event pattern.

        Parameters
        ----------
        pattern : str
            Event name or wildcard (e.g., "member.join", "member.*", "*")
        priority : int
            Execution order (higher runs first). Default 0.

        Returns
        -------
        Decorator function
        """

        def decorator(handler: EventHandler) -> EventHandler:
            if "*" in pattern:
                if pattern not in self._wildcards:
                    self._wildcards[pattern] = []
                self._wildcards[pattern].append((priority, handler))
                self._wildcards[pattern].sort(reverse=True)
            else:
                if pattern not in self._handlers:
                    self._handlers[pattern] = []
                self._handlers[pattern].append((priority, handler))
                self._handlers[pattern].sort(reverse=True)
            return handler

        return decorator

    async def emit(self, event: Event) -> Event:
        """Emit event to all matching handlers.

        Returns
        -------
        Event
            Same event object (may be cancelled by handlers)
        """
        tasks: list[Coroutine[Any, Any, None]] = []

        # Exact match handlers
        if event.name in self._handlers:
            for _, handler in self._handlers[event.name]:
                tasks.append(handler(event))

        # Wildcard handlers
        prefix = event.name.split(".")[0] if "." in event.name else ""
        wildcard = f"{prefix}.*" if prefix else "*"

        for pattern in [wildcard, "*"]:
            if pattern in self._wildcards:
                for _, handler in self._wildcards[pattern]:
                    tasks.append(handler(event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=False)

        return event

    def disconnect(self, pattern: str, handler: EventHandler | None = None) -> None:
        """Unregister handler(s).

        Parameters
        ----------
        pattern : str
            Event pattern to disconnect from
        handler : Callable, optional
            Specific handler. If None, disconnect all for pattern.
        """
        targets = self._wildcards if "*" in pattern else self._handlers

        if pattern not in targets:
            return

        if handler is None:
            targets[pattern].clear()
        else:
            targets[pattern] = [(p, h) for p, h in targets[pattern] if h is not handler]

    def listeners(self, pattern: str) -> Sequence[EventHandler]:
        """Get all handlers for a pattern."""
        targets = self._wildcards if "*" in pattern else self._handlers
        return [h for _, h in targets.get(pattern, [])]
