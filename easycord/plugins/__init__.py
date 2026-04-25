"""Optional first-party plugins."""
from ._ai_providers import (
    AIProvider,
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
)
from .levels import LevelsPlugin
from .openclaude import AIPlugin, OpenClaudePlugin
from .polls import PollsPlugin
from .tags import TagsPlugin
from .welcome import WelcomePlugin

__all__ = [
    "AIPlugin",
    "AIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "LevelsPlugin",
    "OllamaProvider",
    "OpenAIProvider",
    "OpenClaudePlugin",
    "PollsPlugin",
    "TagsPlugin",
    "WelcomePlugin",
]
