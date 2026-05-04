"""Conversation memory management for multi-turn AI interactions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from easycord.context import Context


@dataclass
class ConversationTurn:
    """Single turn in conversation."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class Conversation:
    """Conversation history for a user in a guild."""

    user_id: int
    guild_id: int | None
    turns: list[ConversationTurn] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_updated: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    max_turns: int = 20  # Keep last N turns
    max_age_minutes: int = 60  # Expire after N minutes

    def add_turn(self, role: str, content: str) -> None:
        """Add a turn to conversation."""
        self.turns.append(ConversationTurn(role=role, content=content))
        self.last_updated = datetime.now(timezone.utc)
        self._cleanup()

    def _cleanup(self) -> None:
        """Remove old turns exceeding limits."""
        # Remove oldest turns if exceeding max
        while len(self.turns) > self.max_turns:
            self.turns.pop(0)

        # Remove turns older than max_age
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=self.max_age_minutes
        )
        self.turns = [t for t in self.turns if t.timestamp > cutoff]

    def is_expired(self) -> bool:
        """Check if conversation is expired."""
        age = datetime.now(timezone.utc) - self.last_updated
        return age > timedelta(minutes=self.max_age_minutes)

    def to_messages(self) -> list[dict]:
        """Convert to message format for providers."""
        return [
            {
                "role": t.role,
                "content": t.content,
            }
            for t in self.turns
        ]

    def estimate_tokens(self, avg_chars_per_token: int = 4) -> int:
        """Rough token estimate for conversation."""
        total_chars = sum(len(t.content) for t in self.turns)
        return max(1, total_chars // avg_chars_per_token)


class ConversationMemory:
    """Manage conversation history per user/guild."""

    def __init__(self):
        self._conversations: dict[tuple[int, int | None], Conversation] = {}

    def get_or_create(
        self,
        user_id: int,
        guild_id: int | None = None,
        max_turns: int = 20,
        max_age_minutes: int = 60,
    ) -> Conversation:
        """Get or create conversation for user/guild."""
        key = (user_id, guild_id)

        if key in self._conversations:
            conv = self._conversations[key]
            if not conv.is_expired():
                return conv
            # Conversation expired, remove it
            del self._conversations[key]

        conv = Conversation(
            user_id=user_id,
            guild_id=guild_id,
            max_turns=max_turns,
            max_age_minutes=max_age_minutes,
        )
        self._conversations[key] = conv
        return conv

    def add_user_message(
        self,
        user_id: int,
        content: str,
        guild_id: int | None = None,
    ) -> None:
        """Add user message to conversation."""
        conv = self.get_or_create(user_id, guild_id)
        conv.add_turn("user", content)

    def add_assistant_message(
        self,
        user_id: int,
        content: str,
        guild_id: int | None = None,
    ) -> None:
        """Add assistant message to conversation."""
        conv = self.get_or_create(user_id, guild_id)
        conv.add_turn("assistant", content)

    def get_messages(
        self,
        user_id: int,
        guild_id: int | None = None,
    ) -> list[dict]:
        """Get conversation history as messages."""
        conv = self.get_or_create(user_id, guild_id)
        return conv.to_messages()

    def clear(self, user_id: int, guild_id: int | None = None) -> None:
        """Clear conversation history."""
        key = (user_id, guild_id)
        if key in self._conversations:
            del self._conversations[key]

    def cleanup_expired(self) -> int:
        """Remove expired conversations. Return count removed."""
        keys_to_remove = [
            key
            for key, conv in self._conversations.items()
            if conv.is_expired()
        ]
        for key in keys_to_remove:
            del self._conversations[key]
        return len(keys_to_remove)

    def get_stats(self) -> dict:
        """Get memory stats."""
        return {
            "total_conversations": len(self._conversations),
            "total_turns": sum(
                len(c.turns) for c in self._conversations.values()
            ),
            "avg_turns_per_conv": (
                sum(len(c.turns) for c in self._conversations.values())
                / max(1, len(self._conversations))
            ),
        }
