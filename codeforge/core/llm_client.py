"""Ollama/LM Studio LLM client integration.

Provides the core interface for all agents to communicate with the local LLM.
Supports chat completion, streaming responses, and structured output parsing.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from codeforge.utils.config import LLMConfig, get_config
from codeforge.utils.exceptions import LLMConnectionError, LLMResponseError
from codeforge.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChatMessage:
    """A single message in a chat conversation."""

    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    """Structured response from the LLM."""

    content: str
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: float = 0.0
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMStreamChunk:
    """A single chunk from a streaming response."""

    content: str
    done: bool = False


class LlmClient:
    """HTTP client for Ollama API.

    Handles connection management, retry logic, and response parsing.
    """

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or get_config().llm
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.api_url,
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        """Check if the LLM server is reachable."""
        try:
            if self.config.is_groq:
                return bool(self.config.groq_api_key)
            if self.config.is_gemini:
                return bool(self.config.gemini_api_key)
            client = await self._get_client()
            response = await client.get("/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        try:
            client = await self._get_client()
            response = await client.get("/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except httpx.HTTPError as e:
            raise LLMConnectionError(
                f"Failed to list models: {e}",
                code="LIST_MODELS_FAILED",
                details={"host": self.config.host},
            )

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        if self.config.is_groq:
            return await self._chat_groq(
                messages=messages,
                model=model or self.config.groq_model,
                temperature=temperature or self.config.groq_temperature,
                max_tokens=max_tokens or self.config.groq_max_tokens,
                system=system,
            )
        if self.config.is_gemini:
            return await self._chat_gemini(
                messages=messages,
                model=model or self.config.gemini_model,
                temperature=temperature or self.config.gemini_temperature,
                max_tokens=max_tokens or self.config.gemini_max_tokens,
                system=system,
            )
        return await self._chat_ollama(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system=system,
        )

    async def _chat_ollama(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        """Send a chat completion request to Ollama.

        Args:
            messages: List of chat messages.
            model: Override the default model.
            temperature: Override the default temperature.
            max_tokens: Override the default max tokens.
            system: System prompt to prepend.

        Returns:
            LLMResponse with the generated content and metadata.
        """
        model_name = model or self.config.model
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens or self.config.max_tokens

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": max_tok,
            },
        }

        if system:
            payload["system"] = system

        logger.debug(
            "Sending chat request",
            extra={"model": model_name, "message_count": len(messages)},
        )

        start_time = time.time()

        try:
            client = await self._get_client()
            response = await client.post("/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self.config.host}: {e}",
                code="CONNECTION_FAILED",
                details={"host": self.config.host},
            )
        except httpx.TimeoutException:
            raise LLMConnectionError(
                f"Ollama request timed out after {self.config.timeout}s",
                code="TIMEOUT",
                details={"timeout": self.config.timeout},
            )
        except httpx.HTTPError as e:
            raise LLMResponseError(
                f"Ollama HTTP error: {e}",
                code="HTTP_ERROR",
                details={"status": getattr(e, "response", None)},
            )

        duration_ms = (time.time() - start_time) * 1000

        content = data.get("message", {}).get("content", "")
        if not content:
            raise LLMResponseError(
                "Empty response from LLM",
                code="EMPTY_RESPONSE",
            )

        return LLMResponse(
            content=content,
            model=data.get("model", model_name),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            duration_ms=duration_ms,
            raw_response=data,
        )

    async def _chat_groq(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        system: str | None = None,
    ) -> LLMResponse:
        groq_messages: list[dict] = []
        if system:
            groq_messages.append({"role": "system", "content": system})
        for m in messages:
            groq_messages.append({"role": m.role, "content": m.content})

        payload = {
            "model": model,
            "messages": groq_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.config.groq_api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.time()

        try:
            client = httpx.AsyncClient(timeout=httpx.Timeout(self.config.timeout))
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            await client.aclose()
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Cannot connect to Groq API: {e}",
                code="CONNECTION_FAILED",
            )
        except httpx.TimeoutException:
            raise LLMConnectionError(
                f"Groq request timed out after {self.config.timeout}s",
                code="TIMEOUT",
            )
        except httpx.HTTPError as e:
            raise LLMResponseError(
                f"Groq HTTP error: {e}",
                code="HTTP_ERROR",
            )

        duration_ms = (time.time() - start_time) * 1000

        choices = data.get("choices", [])
        if not choices:
            raise LLMResponseError("Empty response from Groq", code="EMPTY_RESPONSE")

        content = choices[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model", model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            duration_ms=duration_ms,
            raw_response=data,
        )

    async def _chat_gemini(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        system: str | None = None,
    ) -> LLMResponse:
        contents: list[dict] = []
        if system:
            contents.append({"role": "user", "parts": [{"text": f"System: {system}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        for m in messages:
            role = "model" if m.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m.content}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.config.gemini_api_key}"
        )

        start_time = time.time()

        try:
            client = httpx.AsyncClient(timeout=httpx.Timeout(self.config.timeout))
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            await client.aclose()
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Cannot connect to Gemini API: {e}",
                code="CONNECTION_FAILED",
            )
        except httpx.TimeoutException:
            raise LLMConnectionError(
                f"Gemini request timed out after {self.config.timeout}s",
                code="TIMEOUT",
            )
        except httpx.HTTPError as e:
            raise LLMResponseError(
                f"Gemini HTTP error: {e}",
                code="HTTP_ERROR",
            )

        duration_ms = (time.time() - start_time) * 1000

        candidates = data.get("candidates", [])
        if not candidates:
            raise LLMResponseError("Empty response from Gemini", code="EMPTY_RESPONSE")

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        text = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})

        return LLMResponse(
            content=text,
            model=data.get("modelVersion", model),
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
            total_tokens=usage.get("totalTokenCount", 0),
            duration_ms=duration_ms,
            raw_response=data,
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream a chat completion from Ollama.

        Yields LLMStreamChunk objects as the response is generated.
        """
        model_name = model or self.config.model
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens or self.config.max_tokens

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            "options": {
                "temperature": temp,
                "num_predict": max_tok,
            },
        }

        if system:
            payload["system"] = system

        try:
            client = await self._get_client()
            async with client.stream("POST", "/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        chunk_content = data.get("message", {}).get("content", "")
                        done = data.get("done", False)
                        yield LLMStreamChunk(content=chunk_content, done=done)
                    except json.JSONDecodeError:
                        continue
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self.config.host}: {e}",
                code="CONNECTION_FAILED",
                details={"host": self.config.host},
            )
        except httpx.TimeoutException:
            raise LLMConnectionError(
                "Ollama stream timed out",
                code="TIMEOUT",
                details={"timeout": self.config.timeout},
            )

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        """Send a single-prompt completion to Ollama (non-chat API).

        Args:
            prompt: The prompt text.
            model: Override the default model.
            temperature: Override the default temperature.
            max_tokens: Override the default max tokens.
            system: System prompt.

        Returns:
            LLMResponse with the generated content.
        """
        model_name = model or self.config.model
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens or self.config.max_tokens

        payload: dict[str, Any] = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": max_tok,
            },
        }

        if system:
            payload["system"] = system

        start_time = time.time()

        try:
            client = await self._get_client()
            response = await client.post("/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self.config.host}: {e}",
                code="CONNECTION_FAILED",
                details={"host": self.config.host},
            )
        except httpx.TimeoutException:
            raise LLMConnectionError(
                f"Ollama request timed out after {self.config.timeout}s",
                code="TIMEOUT",
            )
        except httpx.HTTPError as e:
            raise LLMResponseError(
                f"Ollama HTTP error: {e}",
                code="HTTP_ERROR",
            )

        duration_ms = (time.time() - start_time) * 1000

        content = data.get("response", "")
        if not content:
            raise LLMResponseError(
                "Empty response from LLM",
                code="EMPTY_RESPONSE",
            )

        return LLMResponse(
            content=content,
            model=data.get("model", model_name),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            duration_ms=duration_ms,
            raw_response=data,
        )

    async def chat_with_retry(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ) -> LLMResponse:
        """Chat with automatic retry on failure.

        Args:
            messages: Chat messages.
            model: Model override.
            temperature: Temperature override.
            max_tokens: Max tokens override.
            system: System prompt.
            max_retries: Maximum number of retry attempts.
            retry_delay: Delay between retries in seconds.

        Returns:
            LLMResponse.

        Raises:
            LLMConnectionError: If all retries are exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                return await self.chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    system=system,
                )
            except (LLMConnectionError, LLMResponseError) as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        "LLM request failed "
                        f"(attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {retry_delay}s",
                        extra={"error": str(e)},
                    )
                    await asyncio.sleep(retry_delay)

        raise LLMConnectionError(
            f"LLM request failed after {max_retries + 1} attempts",
            code="MAX_RETRIES",
            details={"last_error": str(last_error)} if last_error else {},
        )


class ResponseParser:
    """Parse and validate structured LLM responses.

    Handles extraction of JSON blocks from mixed text, validation
    against expected schemas, and fallback to raw text.
    """

    @staticmethod
    def extract_json(text: str) -> dict[str, Any] | None:
        """Extract a JSON object from text that may contain extra content.

        Handles JSON wrapped in ```json code blocks or standalone objects.
        """
        text = text.strip()

        import re

        code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if code_block:
            try:
                return json.loads(code_block.group(1))
            except json.JSONDecodeError:
                pass

        brace_start = text.find("{")
        brace_end = text.rfind("}")
        bracket_start = text.find("[")
        bracket_end = text.rfind("]")

        if brace_start != -1 and brace_end != -1 and brace_start < brace_end:
            try:
                return json.loads(text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass

        if bracket_start != -1 and bracket_end != -1 and bracket_start < bracket_end:
            try:
                return json.loads(text[bracket_start:bracket_end + 1])
            except json.JSONDecodeError:
                pass

        return None

    @staticmethod
    def parse_structured(
        response: LLMResponse,
        required_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """Parse an LLM response into a structured dictionary.

        Attempts JSON extraction first, falls back to treating the entire
        content as raw text if parsing fails.

        Args:
            response: The LLM response to parse.
            required_keys: Keys that must be present in the parsed output.

        Returns:
            Parsed dictionary.

        Raises:
            LLMResponseError: If required keys are missing after parsing.
        """
        data = ResponseParser.extract_json(response.content)

        if data is None:
            data = {"raw_content": response.content}

        if required_keys:
            missing = [k for k in required_keys if k not in data]
            if missing:
                raise LLMResponseError(
                    f"LLM response missing required keys: {missing}",
                    code="MISSING_KEYS",
                    details={"required": required_keys, "found": list(data.keys())},
                )

        return data


class ContextWindowManager:
    """Manages token budget for LLM context windows.

    Tracks approximate token counts and trims conversation history
    to fit within the model's context window limit.
    """

    CHARS_PER_TOKEN_ESTIMATE = 4

    def __init__(self, max_context_tokens: int = 4096):
        self.max_context_tokens = max_context_tokens
        self.reserved_for_response: int = max_context_tokens // 4

    def estimate_tokens(self, text: str) -> int:
        """Roughly estimate token count from character count."""
        return len(text) // self.CHARS_PER_TOKEN_ESTIMATE

    def estimate_messages_tokens(
        self, messages: list[ChatMessage], system: str = ""
    ) -> int:
        """Estimate total tokens for a list of messages."""
        total = self.estimate_tokens(system) if system else 0
        for msg in messages:
            total += self.estimate_tokens(msg.content) + 4
        return total

    def fit_messages(
        self,
        messages: list[ChatMessage],
        system: str = "",
    ) -> list[ChatMessage]:
        """Trim message history to fit within context window.

        Always preserves the first message (system/instruction context)
        and trims from the middle of the conversation.
        """
        if not messages:
            return messages

        available = self.max_context_tokens - self.reserved_for_response
        if system:
            available -= self.estimate_tokens(system)

        if self.estimate_messages_tokens(messages) <= available:
            return messages

        result = [messages[0]]
        remaining = available - self.estimate_tokens(messages[0].content)

        for msg in reversed(messages[1:]):
            msg_tokens = self.estimate_tokens(msg.content) + 4
            if msg_tokens <= remaining:
                result.append(msg)
                remaining -= msg_tokens
            else:
                break

        result.sort(key=lambda m: messages.index(m) if m in messages else -1)
        return result


_global_client: LlmClient | None = None


def get_llm_client() -> LlmClient:
    """Get or create the global LLM client instance."""
    global _global_client
    if _global_client is None:
        _global_client = LlmClient()
    return _global_client


async def close_llm_client() -> None:
    """Close the global LLM client."""
    global _global_client
    if _global_client is not None:
        await _global_client.close()
        _global_client = None
