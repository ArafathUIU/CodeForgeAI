"""LLM integration mixin for CodeForge agents.

Provides a shared interface for agents to call the LLM with proper
prompt construction, response parsing, and graceful fallback to
deterministic rules when the LLM is unavailable.
"""

from __future__ import annotations

import json
from typing import Any

from codeforge.core.llm_client import (
    ChatMessage,
    LlmClient,
    LLMResponse,
    ResponseParser,
)
from codeforge.utils.logging import get_logger

logger = get_logger(__name__)


class LLMMixin:
    """Mixin that gives any agent optional LLM reasoning capabilities.

    Usage:
        class MyAgent(LLMMixin, BaseAgent):
            async def process_message(self, msg):
                result = await self.llm_reason(system_prompt, user_prompt)
                data = self.parse_json_response(result)
    """

    def __init__(self, llm_client: LlmClient | None = None, **kwargs):
        self._llm = llm_client
        self._llm_available: bool | None = None

    async def _check_llm(self) -> bool:
        if self._llm_available is not None:
            return self._llm_available
        if self._llm is None:
            self._llm_available = False
            return False
        self._llm_available = await self._llm.health_check()
        return self._llm_available

    async def llm_reason(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse | None:
        if not await self._check_llm():
            return None

        messages = [
            ChatMessage(role="user", content=user_prompt),
        ]

        try:
            response = await self._llm.chat(
                messages=messages,
                system=system_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info(
                f"LLM response received: {len(response.content)} chars, "
                f"{response.total_tokens} tokens"
            )
            return response
        except Exception as e:
            logger.warning(f"LLM call failed, falling back: {e}")
            return None

    def parse_json_response(
        self, response: LLMResponse | None, required_keys: list[str] | None = None
    ) -> dict[str, Any] | None:
        if response is None:
            return None
        try:
            data = ResponseParser.extract_json(response.content)
            if data is None:
                return {"raw_content": response.content}
            if isinstance(data, str):
                return {"raw_content": data}
            if not isinstance(data, dict):
                return {"raw_content": response.content}
            if required_keys:
                missing = [k for k in required_keys if k not in data]
                if missing:
                    logger.warning(f"LLM response missing keys: {missing}")
                    return None
            return data
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return None

    def format_artifact_json(self, data: dict[str, Any]) -> str:
        return json.dumps(data, indent=2, default=str)

    async def generate_collab_message(
        self,
        my_role: str,
        target_role: str,
        context: str,
    ) -> str | None:
        """Generate a natural group-chat message using LLM."""
        if not await self._check_llm():
            return None
        prompt = (
            f"You are the {my_role} agent on a software development team. "
            f"You are chatting directly with the {target_role} agent in a "
            f"group chat. Be concise, natural, and professional. "
            f"Mention @{target_role} in your message. "
            f"Keep it 1-3 sentences.\n\n"
            f"Context about what to communicate:\n{context}"
        )
        try:
            messages = [ChatMessage(role="user", content=prompt)]
            response = await self._llm.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=300,
            )
            return response.content.strip().replace('\"', '')
        except Exception:
            return None
