"""Tests for easycord.plugins — AI providers and AIPlugin."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from easycord.plugins._ai_providers import (
    AIProvider,
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
)
from easycord.plugins.openclaude import AIPlugin, OpenClaudePlugin


# ============================================================================
# Section 1 — AIProvider base (abstract enforcement)
# ============================================================================


def test_aiprovider_abstract():
    """AIProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        AIProvider(api_key="test", model="test")


# ============================================================================
# Section 2 — AnthropicProvider unit tests
# ============================================================================


def test_anthropic_requires_api_key():
    """AnthropicProvider requires ANTHROPIC_API_KEY."""
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider(api_key=None)


def test_anthropic_accepts_explicit_key():
    """AnthropicProvider accepts explicit api_key."""
    provider = AnthropicProvider(api_key="test-key")
    assert provider._api_key == "test-key"


def test_anthropic_reads_env_var(monkeypatch):
    """AnthropicProvider reads ANTHROPIC_API_KEY from environment."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    provider = AnthropicProvider()
    assert provider._api_key == "env-key"


def test_anthropic_custom_model():
    """AnthropicProvider accepts custom model."""
    provider = AnthropicProvider(api_key="test", model="claude-3-opus")
    assert provider._model == "claude-3-opus"


def test_anthropic_missing_sdk():
    """AnthropicProvider raises ImportError if anthropic SDK missing."""
    provider = AnthropicProvider(api_key="test")
    with patch.dict("sys.modules", {"anthropic": None}):
        with pytest.raises(ImportError, match="anthropic"):
            provider._init_client()


def test_anthropic_query_returns_text():
    """AnthropicProvider.query returns response text."""
    provider = AnthropicProvider(api_key="test")
    with patch.object(provider, "_init_client"):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Claude response")]
        provider._client = MagicMock()
        provider._client.messages.create.return_value = mock_response
        assert provider.query("hello") == "Claude response"


# ============================================================================
# Section 3 — OpenAIProvider unit tests
# ============================================================================


def test_openai_requires_api_key():
    """OpenAIProvider requires OPENAI_API_KEY."""
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIProvider(api_key=None)


def test_openai_accepts_explicit_key():
    """OpenAIProvider accepts explicit api_key."""
    provider = OpenAIProvider(api_key="test-key")
    assert provider._api_key == "test-key"


def test_openai_reads_env_var(monkeypatch):
    """OpenAIProvider reads OPENAI_API_KEY from environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    provider = OpenAIProvider()
    assert provider._api_key == "env-key"


def test_openai_custom_model():
    """OpenAIProvider accepts custom model."""
    provider = OpenAIProvider(api_key="test", model="gpt-3.5-turbo")
    assert provider._model == "gpt-3.5-turbo"


def test_openai_missing_sdk():
    """OpenAIProvider raises ImportError if openai SDK missing."""
    provider = OpenAIProvider(api_key="test")
    with patch.dict("sys.modules", {"openai": None}):
        with pytest.raises(ImportError, match="openai"):
            provider._init_client()


def test_openai_query_returns_text():
    """OpenAIProvider.query returns response text."""
    provider = OpenAIProvider(api_key="test")
    with patch.object(provider, "_init_client"):
        mock_choice = MagicMock()
        mock_choice.message.content = "GPT response"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        provider._client = MagicMock()
        provider._client.chat.completions.create.return_value = mock_response
        assert provider.query("hello") == "GPT response"


# ============================================================================
# Section 4 — GeminiProvider unit tests
# ============================================================================


def test_gemini_requires_api_key():
    """GeminiProvider requires GOOGLE_API_KEY."""
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        GeminiProvider(api_key=None)


def test_gemini_accepts_explicit_key():
    """GeminiProvider accepts explicit api_key."""
    provider = GeminiProvider(api_key="test-key")
    assert provider._api_key == "test-key"


def test_gemini_reads_env_var(monkeypatch):
    """GeminiProvider reads GOOGLE_API_KEY from environment."""
    monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
    provider = GeminiProvider()
    assert provider._api_key == "env-key"


def test_gemini_custom_model():
    """GeminiProvider accepts custom model."""
    provider = GeminiProvider(api_key="test", model="gemini-pro")
    assert provider._model == "gemini-pro"


def test_gemini_missing_sdk():
    """GeminiProvider raises ImportError if google-generativeai SDK missing."""
    provider = GeminiProvider(api_key="test")
    with patch.dict("sys.modules", {"google.generativeai": None}):
        with pytest.raises(ImportError, match="google-generativeai"):
            provider._init_client()


def test_gemini_query_returns_text():
    """GeminiProvider.query returns response text."""
    provider = GeminiProvider(api_key="test")
    with patch.object(provider, "_init_client"):
        mock_response = MagicMock()
        mock_response.text = "Gemini response"
        provider._client = MagicMock()
        provider._client.generate_content.return_value = mock_response
        assert provider.query("hello") == "Gemini response"


# ============================================================================
# Section 5 — OllamaProvider unit tests
# ============================================================================


def test_ollama_no_api_key_required():
    """OllamaProvider doesn't require API key (local)."""
    provider = OllamaProvider()
    assert provider._api_key is None


def test_ollama_accepts_explicit_model():
    """OllamaProvider accepts custom model name."""
    provider = OllamaProvider(model="llama3")
    assert provider._model == "llama3"


def test_ollama_missing_sdk():
    """OllamaProvider raises ImportError if ollama SDK missing."""
    provider = OllamaProvider()
    with patch.dict("sys.modules", {"ollama": None}):
        with pytest.raises(ImportError, match="ollama"):
            provider._init_client()


def test_ollama_query_returns_text():
    """OllamaProvider.query returns response text."""
    provider = OllamaProvider()
    with patch.object(provider, "_init_client"):
        mock_ollama = MagicMock()
        mock_ollama.chat.return_value = {"message": {"content": "Ollama response"}}
        provider._client = mock_ollama
        assert provider.query("hello") == "Ollama response"


# ============================================================================
# Section 6 — AIPlugin unit tests
# ============================================================================


@pytest.mark.asyncio
async def test_aiplugin_ask_calls_provider_and_responds():
    """AIPlugin.ask calls provider and responds with result."""
    provider = MagicMock(spec=AIProvider)
    provider.query.return_value = "AI response"
    plugin = AIPlugin(provider=provider)
    ctx = MagicMock()
    ctx.defer = AsyncMock()
    ctx.respond = AsyncMock()

    await plugin.ask(ctx, prompt="test")

    ctx.defer.assert_called_once()
    ctx.respond.assert_called_once_with("AI response")


@pytest.mark.asyncio
async def test_aiplugin_truncates_long_response():
    """AIPlugin.ask truncates responses over 2000 chars."""
    provider = MagicMock(spec=AIProvider)
    provider.query.return_value = "x" * 3000
    plugin = AIPlugin(provider=provider)
    ctx = MagicMock()
    ctx.defer = AsyncMock()
    ctx.respond = AsyncMock()

    await plugin.ask(ctx, prompt="test")

    text = ctx.respond.call_args[0][0]
    assert len(text) <= 2000
    assert text.endswith("...")


@pytest.mark.asyncio
async def test_aiplugin_handles_import_error():
    """AIPlugin.ask handles ImportError from provider."""
    provider = MagicMock(spec=AIProvider)
    provider.query.side_effect = ImportError("sdk missing")
    plugin = AIPlugin(provider=provider)
    ctx = MagicMock()
    ctx.defer = AsyncMock()
    ctx.t = MagicMock(return_value="sdk missing")
    ctx.respond = AsyncMock()

    await plugin.ask(ctx, prompt="test")

    ctx.respond.assert_called_once()
    assert ctx.respond.call_args[1].get("ephemeral") is True


@pytest.mark.asyncio
async def test_aiplugin_handles_api_error():
    """AIPlugin.ask handles generic API errors."""
    provider = MagicMock(spec=AIProvider)
    provider.query.side_effect = Exception("rate limit exceeded")
    plugin = AIPlugin(provider=provider)
    ctx = MagicMock()
    ctx.defer = AsyncMock()
    ctx.t = MagicMock(return_value="Error calling AI: rate limit exceeded")
    ctx.respond = AsyncMock()

    await plugin.ask(ctx, prompt="test")

    ctx.respond.assert_called_once()
    assert ctx.respond.call_args[1].get("ephemeral") is True


# ============================================================================
# Section 7 — OpenClaudePlugin backwards-compat tests
# ============================================================================


def test_openclaude_init_requires_api_key():
    """OpenClaudePlugin requires ANTHROPIC_API_KEY."""
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        OpenClaudePlugin(api_key=None)


def test_openclaude_init_with_api_key():
    """OpenClaudePlugin initializes with explicit API key."""
    plugin = OpenClaudePlugin(api_key="test-key")
    assert plugin._provider._api_key == "test-key"


def test_openclaude_init_with_env_var(monkeypatch):
    """OpenClaudePlugin reads ANTHROPIC_API_KEY from environment."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    plugin = OpenClaudePlugin()
    assert plugin._provider._api_key == "env-key"


def test_openclaude_model_customizable():
    """OpenClaudePlugin accepts custom model."""
    plugin = OpenClaudePlugin(api_key="test", model="claude-3-opus")
    assert plugin._provider._model == "claude-3-opus"


@pytest.mark.asyncio
async def test_openclaude_ask_defers_and_responds():
    """OpenClaudePlugin.ask defers and responds."""
    plugin = OpenClaudePlugin(api_key="test-key")
    ctx = MagicMock()
    ctx.defer = AsyncMock()
    ctx.respond = AsyncMock()

    with patch.object(plugin._provider, "query", return_value="Test response"):
        await plugin.ask(ctx, prompt="Test prompt")

    ctx.defer.assert_called_once()
    ctx.respond.assert_called_once_with("Test response")
