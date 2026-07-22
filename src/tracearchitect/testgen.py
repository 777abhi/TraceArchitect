"""Day 2 — Structured Outputs & JSON Mode for test-case generation.

Turn a plain-English user story into a *validated*, structured test case by
asking a local Ollama model to reply in JSON that matches a schema, then
parsing that JSON with Pydantic. This is the core "structured outputs" pattern:
constrain the model to a schema instead of free-form text, so downstream code
can rely on the shape.

Example:
    from tracearchitect.testgen import generate_test_case

    tc = generate_test_case("As a user I can reset my password via email")
    print(tc.title, tc.priority, len(tc.steps))

The Ollama call is isolated behind a small ``ChatClient`` protocol so the
parsing/validation logic can be unit-tested offline with a fake client.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

from pydantic import BaseModel, Field

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"

Priority = str  # constrained below via Field pattern/enum in the schema

_SYSTEM_PROMPT = (
    "You are a senior QA engineer. Given a user story, produce a single, "
    "concrete test case as JSON that strictly matches the provided schema. "
    "Write clear, atomic steps; each step has an action and its expected "
    "result. Choose priority from: low, medium, high, critical. "
    "Respond with JSON only — no prose, no markdown."
)


class TestStep(BaseModel):
    """One atomic step of a test case."""

    action: str = Field(..., description="The action the tester performs.")
    expected_result: str = Field(..., description="The observable expected outcome.")


class GeneratedTestCase(BaseModel):
    """A structured test case generated from a user story."""

    title: str = Field(..., description="Short, descriptive test-case title.")
    summary: str = Field(..., description="One-sentence summary of what is verified.")
    priority: str = Field(
        ...,
        pattern="^(low|medium|high|critical)$",
        description="One of: low, medium, high, critical.",
    )
    tags: list[str] = Field(default_factory=list, description="Optional labels.")
    steps: list[TestStep] = Field(..., min_length=1, description="Ordered steps.")


class ChatClient(Protocol):
    """Minimal interface we need from an Ollama-like client."""

    def chat(self, *, model: str, messages: list[dict[str, str]], format: Any) -> Any:
        ...


def _extract_content(response: Any) -> str:
    """Pull the assistant message text out of an Ollama chat response.

    Works with both the ollama ``ChatResponse`` object (mapping + attribute
    access) and a plain dict used in tests.
    """
    message = response["message"]
    content = message["content"]
    if not isinstance(content, str):
        raise TypeError(f"expected string content, got {type(content).__name__}")
    return content


def build_client(host: str | None = None) -> ChatClient:
    """Create a real Ollama client. Imported lazily so tests can stay offline."""
    import ollama

    return ollama.Client(host=host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST))


def generate_test_case(
    user_story: str,
    *,
    model: str | None = None,
    host: str | None = None,
    client: ChatClient | None = None,
) -> GeneratedTestCase:
    """Generate and validate a structured test case from a user story.

    Args:
        user_story: Plain-English story, e.g. "As a user I can log in".
        model: Ollama model tag; defaults to ``OLLAMA_MODEL`` or ``llama3.2``.
        host: Ollama base URL; defaults to ``OLLAMA_HOST`` or localhost.
        client: Optional pre-built chat client (used for testing).

    Returns:
        A validated :class:`GeneratedTestCase`.

    Raises:
        pydantic.ValidationError: if the model's JSON does not match the schema.
    """
    if not user_story or not user_story.strip():
        raise ValueError("user_story must be a non-empty string")

    model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    client = client or build_client(host)

    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"User story:\n{user_story.strip()}"},
        ],
        # JSON mode: constrain the model's output to this JSON schema.
        format=GeneratedTestCase.model_json_schema(),
    )

    content = _extract_content(response)
    return GeneratedTestCase.model_validate_json(content)
