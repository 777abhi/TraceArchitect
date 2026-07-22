"""Offline tests for Day 2 structured-output test-case generation.

These use a fake chat client so they run in CI without a live Ollama server.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from tracearchitect.testgen import (
    GeneratedTestCase,
    generate_test_case,
)


class FakeClient:
    """Stands in for ollama.Client, returning a canned response."""

    def __init__(self, content: str):
        self._content = content
        self.calls: list[dict[str, Any]] = []

    def chat(self, *, model: str, messages: list[dict[str, str]], format: Any) -> Any:
        self.calls.append({"model": model, "messages": messages, "format": format})
        return {"message": {"content": self._content}}


VALID_JSON = json.dumps(
    {
        "title": "Password reset via email",
        "summary": "User can reset their password using an emailed link.",
        "priority": "high",
        "tags": ["auth", "email"],
        "steps": [
            {"action": "Click 'Forgot password'", "expected_result": "Reset form shown"},
            {"action": "Submit registered email", "expected_result": "Email sent banner"},
        ],
    }
)


def test_generate_test_case_parses_and_validates():
    client = FakeClient(VALID_JSON)
    tc = generate_test_case(
        "As a user I can reset my password via email",
        model="test-model",
        client=client,
    )

    assert isinstance(tc, GeneratedTestCase)
    assert tc.title == "Password reset via email"
    assert tc.priority == "high"
    assert len(tc.steps) == 2
    assert tc.steps[0].expected_result == "Reset form shown"


def test_schema_is_passed_as_format_and_model_forwarded():
    client = FakeClient(VALID_JSON)
    generate_test_case("story", model="my-model", client=client)

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["model"] == "my-model"
    # JSON mode: the request must carry the JSON schema as `format`.
    assert call["format"] == GeneratedTestCase.model_json_schema()
    assert call["format"]["properties"]["priority"]["pattern"] == "^(low|medium|high|critical)$"


def test_invalid_priority_raises_validation_error():
    bad = json.dumps(
        {
            "title": "x",
            "summary": "y",
            "priority": "urgent",  # not in the allowed set
            "steps": [{"action": "a", "expected_result": "b"}],
        }
    )
    with pytest.raises(ValidationError):
        generate_test_case("story", client=FakeClient(bad))


def test_missing_steps_raises_validation_error():
    bad = json.dumps(
        {"title": "x", "summary": "y", "priority": "low", "steps": []}
    )
    with pytest.raises(ValidationError):
        generate_test_case("story", client=FakeClient(bad))


def test_empty_user_story_rejected():
    with pytest.raises(ValueError):
        generate_test_case("   ", client=FakeClient(VALID_JSON))
