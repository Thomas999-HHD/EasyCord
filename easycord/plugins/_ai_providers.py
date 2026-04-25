"""Abstract and concrete AI provider implementations."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):
    """Abstract base for AI API providers."""

    def __init__(self, api_key: Optional[str], model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client = None

    @abstractmethod
    def _init_client(self) -> None:
        """Initialize SDK client. Subclass must implement."""

    @abstractmethod
    def query(self, prompt: str) -> str:
        """Send prompt to AI, return response text."""


class AnthropicProvider(AIProvider):
    """Claude API via Anthropic SDK."""

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    ENV_KEY = "ANTHROPIC_API_KEY"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        resolved_key = api_key or os.getenv(self.ENV_KEY)
        if not resolved_key:
            raise ValueError(f"{self.ENV_KEY} env var or api_key param required")
        super().__init__(resolved_key, model)

    def _init_client(self) -> None:
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError(
                    "anthropic package required. Install with: pip install anthropic"
                )
            self._client = Anthropic(api_key=self._api_key)

    def query(self, prompt: str) -> str:
        self._init_client()
        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


class OpenAIProvider(AIProvider):
    """ChatGPT API via OpenAI SDK."""

    DEFAULT_MODEL = "gpt-4o"
    ENV_KEY = "OPENAI_API_KEY"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        resolved_key = api_key or os.getenv(self.ENV_KEY)
        if not resolved_key:
            raise ValueError(f"{self.ENV_KEY} env var or api_key param required")
        super().__init__(resolved_key, model)

    def _init_client(self) -> None:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai package required. Install with: pip install openai"
                )
            self._client = OpenAI(api_key=self._api_key)

    def query(self, prompt: str) -> str:
        self._init_client()
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content


class GeminiProvider(AIProvider):
    """Google Gemini API via google-generativeai SDK."""

    DEFAULT_MODEL = "gemini-1.5-flash"
    ENV_KEY = "GOOGLE_API_KEY"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        resolved_key = api_key or os.getenv(self.ENV_KEY)
        if not resolved_key:
            raise ValueError(f"{self.ENV_KEY} env var or api_key param required")
        super().__init__(resolved_key, model)

    def _init_client(self) -> None:
        if self._client is None:
            try:
                import google.generativeai as genai
            except ImportError:
                raise ImportError(
                    "google-generativeai package required. "
                    "Install with: pip install google-generativeai"
                )
            genai.configure(api_key=self._api_key)
            self._client = genai.GenerativeModel(self._model)

    def query(self, prompt: str) -> str:
        self._init_client()
        response = self._client.generate_content(prompt)
        return response.text


class OllamaProvider(AIProvider):
    """Local Ollama models via ollama SDK."""

    DEFAULT_MODEL = "llama2"
    ENV_KEY = None

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        super().__init__(None, model)

    def _init_client(self) -> None:
        if self._client is None:
            try:
                import ollama
            except ImportError:
                raise ImportError(
                    "ollama package required. Install with: pip install ollama"
                )
            self._client = ollama

    def query(self, prompt: str) -> str:
        self._init_client()
        response = self._client.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]
