"""AI assistant plugins using various LLM provider APIs."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from easycord import Plugin, slash

if TYPE_CHECKING:
    from ._ai_providers import AIProvider


class AIPlugin(Plugin):
    """General-purpose AI assistant for any LLM provider.

    Members can ask questions via `/ask` and receive AI-generated responses.
    Supports Anthropic Claude, OpenAI GPT, Google Gemini, Ollama, and others.

    Quick start::

        from easycord.plugins.openclaude import AIPlugin
        from easycord.plugins._ai_providers import AnthropicProvider

        provider = AnthropicProvider(api_key="sk-ant-...")
        bot.add_plugin(AIPlugin(provider=provider))

    Slash commands registered
    -------------------------
    ``/ask`` — Ask the AI a question and get a response.
    """

    def __init__(self, provider: AIProvider) -> None:
        """Initialize AI plugin.

        Parameters
        ----------
        provider : AIProvider
            An AI provider instance (AnthropicProvider, OpenAIProvider, etc.).
        """
        super().__init__()
        self._provider = provider

    @staticmethod
    def _format_response(text: str) -> str:
        """Truncate response to Discord's 2000 char limit."""
        if len(text) > 2000:
            return text[:1997] + "..."
        return text

    @slash(description="Ask an AI a question and get a response.", guild_only=True)
    async def ask(self, ctx, prompt: str) -> None:
        """Ask AI a question.

        Parameters
        ----------
        ctx : Context
            Command context.
        prompt : str
            Question or prompt for the AI.
        """
        await ctx.defer()

        try:
            response_text = self._provider.query(prompt)
            await ctx.respond(self._format_response(response_text))

        except ImportError as exc:
            await ctx.respond(
                ctx.t(
                    "ai.sdk_not_installed",
                    default=str(exc),
                ),
                ephemeral=True,
            )
        except Exception as exc:
            await ctx.respond(
                ctx.t(
                    "ai.error",
                    default="Error calling AI: {error}",
                    error=str(exc),
                ),
                ephemeral=True,
            )


class OpenClaudePlugin(AIPlugin):
    """Backwards-compatible wrapper for Anthropic Claude.

    Maintains the original OpenClaudePlugin interface while delegating to AIPlugin.

    Members can ask questions via `/ask` and receive Claude-generated responses.
    Requires ANTHROPIC_API_KEY environment variable or explicit API key.

    Quick start::

        from easycord.plugins.openclaude import OpenClaudePlugin
        bot.add_plugin(OpenClaudePlugin())

    Slash commands registered
    -------------------------
    ``/ask`` — Ask Claude a question and get an AI-powered response.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
    ) -> None:
        """Initialize OpenClaude plugin.

        Parameters
        ----------
        api_key : str, optional
            Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        model : str
            Claude model to use (default: claude-3-5-sonnet-20241022).
        """
        from ._ai_providers import AnthropicProvider

        provider = AnthropicProvider(api_key=api_key, model=model)
        super().__init__(provider=provider)
