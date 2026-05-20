"""Tests for the LLM client module (unit tests, no live server needed)."""

import asyncio

import pytest

from codeforge.core.llm_client import (
    ChatMessage,
    ContextWindowManager,
    LlmClient,
    ResponseParser,
    LLMResponse,
)
from codeforge.utils.config import LLMConfig


class TestChatMessage:
    def test_to_dict(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.to_dict() == {"role": "user", "content": "Hello"}

    def test_system_message(self):
        msg = ChatMessage(role="system", content="You are helpful")
        d = msg.to_dict()
        assert d["role"] == "system"


class TestLLMResponse:
    def test_default_values(self):
        resp = LLMResponse(content="test")
        assert resp.content == "test"
        assert resp.model == ""
        assert resp.prompt_tokens == 0
        assert resp.total_tokens == 0
        assert resp.duration_ms == 0.0

    def test_full_response(self):
        resp = LLMResponse(
            content="response",
            model="llama3.2",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            duration_ms=150.5,
        )
        assert resp.model == "llama3.2"
        assert resp.completion_tokens == 20
        assert resp.total_tokens == 30


class TestResponseParser:
    def test_extract_json_standalone(self):
        data = ResponseParser.extract_json('{"key": "value"}')
        assert data == {"key": "value"}

    def test_extract_json_in_code_block(self):
        text = 'Some text\n```json\n{"name": "test"}\n```\nMore text'
        data = ResponseParser.extract_json(text)
        assert data == {"name": "test"}

    def test_extract_json_with_surrounding_text(self):
        text = 'Here is the result: {"status": "ok"} and more'
        data = ResponseParser.extract_json(text)
        assert data == {"status": "ok"}

    def test_extract_json_returns_none_for_plain_text(self):
        data = ResponseParser.extract_json("Just plain text")
        assert data is None

    def test_extract_json_array(self):
        data = ResponseParser.extract_json('[1, 2, 3]')
        assert data == [1, 2, 3]

    def test_parse_structured_with_required_keys(self):
        resp = LLMResponse(content='{"name": "CodeForge", "version": "1.0"}')
        data = ResponseParser.parse_structured(resp, required_keys=["name"])
        assert data["name"] == "CodeForge"

    def test_parse_structured_missing_key_raises(self):
        from codeforge.utils.exceptions import LLMResponseError

        resp = LLMResponse(content='{"name": "test"}')
        with pytest.raises(LLMResponseError):
            ResponseParser.parse_structured(resp, required_keys=["missing_key"])

    def test_parse_structured_fallback_to_raw(self):
        resp = LLMResponse(content="No JSON here")
        data = ResponseParser.parse_structured(resp)
        assert data["raw_content"] == "No JSON here"


class TestContextWindowManager:
    def test_estimate_tokens(self):
        mgr = ContextWindowManager(max_context_tokens=4096)
        tokens = mgr.estimate_tokens("Hello world")
        assert tokens == 2

    def test_fit_messages_under_limit(self):
        mgr = ContextWindowManager(max_context_tokens=4096)
        msgs = [
            ChatMessage(role="user", content="First"),
            ChatMessage(role="assistant", content="Second"),
        ]
        result = mgr.fit_messages(msgs)
        assert len(result) == 2

    def test_fit_messages_over_limit_preserves_first(self):
        mgr = ContextWindowManager(max_context_tokens=100)
        first = ChatMessage(role="system", content="System prompt")
        long_msg = ChatMessage(role="user", content="x" * 500)
        msgs = [first, long_msg]
        result = mgr.fit_messages(msgs)
        assert result[0].role == "system"

    def test_estimate_messages_tokens(self):
        mgr = ContextWindowManager(max_context_tokens=4096)
        msgs = [ChatMessage(role="user", content="Hello")]
        tokens = mgr.estimate_messages_tokens(msgs)
        assert tokens > 0
