"""
LLM Client — Abstraction layer for LLM inference.

Supports Ollama (local) and OpenAI-compatible APIs (Together, OpenRouter).
All generation parameters are externalized via config files.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Generation parameters for LLM inference."""

    temperature: float = 0.0
    top_p: float = 1.0
    repetition_penalty: float = 1.0
    max_tokens: int = 4096
    seed: int = 42
    num_ctx: int = 8192


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""

    content: str  # Raw text response
    model: str  # Model identifier used
    prompt_tokens: int  # Input token count
    completion_tokens: int  # Output token count
    total_tokens: int  # Total token count
    generation_time_ms: float  # Wall-clock generation time


class LLMClient:
    """
    Unified LLM client supporting Ollama and OpenAI-compatible APIs.

    Usage:
        client = LLMClient(
            provider="ollama",
            model_name="qwen2.5:7b-instruct",
            base_url="http://localhost:11434",
            generation_config=GenerationConfig(temperature=0.0, seed=42),
        )
        response = client.chat(system_prompt="...", user_prompt="...")
    """

    def __init__(
        self,
        provider: str,
        model_name: str,
        base_url: str,
        generation_config: GenerationConfig,
        api_key: str | None = None,
    ):
        self.provider = provider.lower()
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.config = generation_config
        self.api_key = api_key

        if self.provider not in ("ollama", "together", "openrouter", "openai_compatible"):
            raise ValueError(
                f"Unsupported provider: {self.provider}. "
                f"Supported: ollama, together, openrouter, openai_compatible"
            )

    def chat(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """
        Send a chat completion request to the LLM.

        Args:
            system_prompt: System-level instructions (role, schema, rules).
            user_prompt: User-level content (the snippet to process).

        Returns:
            LLMResponse with the model's output and metadata.

        Raises:
            requests.RequestException: On network/API errors.
            ValueError: On unexpected response format.
        """
        if self.provider == "ollama":
            return self._chat_ollama(system_prompt, user_prompt)
        else:
            return self._chat_openai_compatible(system_prompt, user_prompt)

    def _chat_ollama(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Send request to Ollama's /api/chat endpoint."""
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "repeat_penalty": self.config.repetition_penalty,
                "num_predict": self.config.max_tokens,
                "seed": self.config.seed,
                "num_ctx": self.config.num_ctx,
            },
        }

        logger.info(
            "Sending request to Ollama: model=%s, temperature=%.2f, seed=%d",
            self.model_name,
            self.config.temperature,
            self.config.seed,
        )

        start_time = time.time()
        response = requests.post(url, json=payload, timeout=300)
        elapsed_ms = (time.time() - start_time) * 1000

        response.raise_for_status()
        data = response.json()

        content = data.get("message", {}).get("content", "")
        # Ollama provides token counts in different formats depending on version
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        return LLMResponse(
            content=content,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            generation_time_ms=elapsed_ms,
        )

    def _chat_openai_compatible(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Send request to OpenAI-compatible API (Together, OpenRouter, etc.)."""
        if self.provider == "together":
            url = f"{self.base_url}/v1/chat/completions"
        elif self.provider == "openrouter":
            url = f"{self.base_url}/api/v1/chat/completions"
        else:
            url = f"{self.base_url}/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens,
            "seed": self.config.seed,
            "repetition_penalty": self.config.repetition_penalty,
        }

        logger.info(
            "Sending request to %s: model=%s, temperature=%.2f, seed=%d",
            self.provider,
            self.model_name,
            self.config.temperature,
            self.config.seed,
        )

        start_time = time.time()
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        elapsed_ms = (time.time() - start_time) * 1000

        response.raise_for_status()
        data = response.json()

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=self.model_name,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            generation_time_ms=elapsed_ms,
        )

    def health_check(self) -> bool:
        """Verify the LLM endpoint is reachable and the model is available."""
        try:
            if self.provider == "ollama":
                url = f"{self.base_url}/api/tags"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if self.model_name not in model_names:
                    # Check without tag suffix
                    base_name = self.model_name.split(":")[0]
                    if not any(base_name in name for name in model_names):
                        logger.warning(
                            "Model '%s' not found in Ollama. Available: %s",
                            self.model_name,
                            model_names,
                        )
                        return False
                return True
            else:
                # For API providers, just check if the endpoint responds
                url = f"{self.base_url}/v1/models"
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                response = requests.get(url, headers=headers, timeout=10)
                return response.status_code == 200
        except requests.RequestException as e:
            logger.error("Health check failed: %s", e)
            return False
