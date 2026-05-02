"""AI orchestration layer — routing, tool loops, context management."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from easycord.tools import ToolCall, ToolRegistry

if TYPE_CHECKING:
    from easycord.context import Context
    from easycord.plugins._ai_providers import AIProvider
    from easycord.conversation_memory import ConversationMemory


@dataclass
class RunContext:
    """Context for orchestrator.run()."""

    messages: list[dict]
    ctx: Context  # Discord context for permission checks
    max_steps: int = 5
    timeout_ms: int = 30000
    system_prompt: str | None = None  # AI system context
    conversation_memory: ConversationMemory | None = None  # For multi-turn


@dataclass
class FinalResponse:
    """Result from orchestrator."""

    text: str
    provider: Optional[AIProvider] = None
    steps: int = 0


class ProviderStrategy(ABC):
    """Abstract provider selection strategy."""

    @abstractmethod
    def select(
        self, run_ctx: RunContext, attempt: int
    ) -> AIProvider:
        """Select provider for this attempt. Raise on no more options."""


class FallbackStrategy(ProviderStrategy):
    """Try providers in chain; move to next on failure."""

    def __init__(self, providers: list[AIProvider]):
        self.providers = providers

    def select(self, run_ctx: RunContext, attempt: int) -> AIProvider:
        if attempt >= len(self.providers):
            raise IndexError("No more providers to try")
        return self.providers[min(attempt, len(self.providers) - 1)]


class Orchestrator:
    """Coordinate provider selection, tool execution, and looping."""

    def __init__(
        self,
        strategy: ProviderStrategy,
        tools: ToolRegistry,
    ):
        self.strategy = strategy
        self.tools = tools

    def _build_prompt(self, messages: list[dict[str, Any]]) -> str:
        """Build a legacy string prompt from chat-style messages."""
        prompt_parts: list[str] = []
        for message in messages:
            content = message.get("content")
            if content in (None, ""):
                continue
            role = str(message.get("role", "user")).upper()
            prompt_parts.append(f"{role}: {content}")
        return "\n\n".join(prompt_parts).strip()

    async def _query_provider(
        self,
        provider: AIProvider,
        *,
        prompt: str,
        tools_schema: list[dict],
    ):
        """Query either legacy string providers or richer tool-aware providers."""
        try:
            return await provider.query(
                prompt=prompt,
                tools=tools_schema if tools_schema else None,
            )
        except TypeError:
            return await provider.query(prompt)

    def _extract_output(self, output) -> tuple[str | None, ToolCall | None]:
        """Normalize provider outputs across legacy and richer provider styles."""
        if isinstance(output, str):
            return output, None

        text = getattr(output, "text", None)
        tool_call = getattr(output, "tool_call", None)

        if isinstance(text, str):
            return text, tool_call
        return None, tool_call

    async def run(self, run_ctx: RunContext) -> FinalResponse:
        """Execute orchestration loop."""
        max_steps = run_ctx.max_steps
        attempt = 0
        steps = 0
        messages = list(run_ctx.messages)

        # Prepend system prompt if provided
        if run_ctx.system_prompt:
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": run_ctx.system_prompt,
                },
            )

        while steps < max_steps:
            try:
                provider = self.strategy.select(run_ctx, attempt)
            except IndexError:
                return FinalResponse(
                    text="All providers exhausted",
                    provider=None,
                    steps=steps,
                )

            try:
                # Build tool schema for provider
                tools_schema = self.tools.to_provider_schema(run_ctx.ctx)
                prompt = self._build_prompt(messages)

                # Query provider
                output = await self._query_provider(
                    provider,
                    prompt=prompt,
                    tools_schema=tools_schema,
                )
                text, tool_call = self._extract_output(output)

                # Check for tool call
                if tool_call:
                    allowed, reason = self.tools.can_execute(
                        run_ctx.ctx, tool_call.name
                    )
                    if not allowed:
                        messages.append(
                            {
                                "role": "assistant",
                                "content": f"Tool '{tool_call.name}' not available: {reason}",
                            }
                        )
                        steps += 1
                        continue

                    result = await self.tools.execute(
                        run_ctx.ctx, tool_call
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "name": tool_call.name,
                            "content": result.output or result.error,
                        }
                    )
                    steps += 1
                    continue

                # Check for final text
                if text:
                    # Save to conversation memory if provided
                    if run_ctx.conversation_memory:
                        run_ctx.conversation_memory.add_assistant_message(
                            run_ctx.ctx.user.id,
                            text,
                            run_ctx.ctx.guild.id if run_ctx.ctx.guild else None,
                        )
                    return FinalResponse(
                        text=text,
                        provider=provider,
                        steps=steps,
                    )

                # Neither tool nor text — try fallback
                attempt += 1
                continue

            except Exception:
                # Provider failed — try fallback
                attempt += 1
                continue

        return FinalResponse(
            text="Max steps reached",
            provider=None,
            steps=steps,
        )
