"""Offline tests for the Day 3 tool-using agent.

A scripted fake client emits tool calls then a final answer, so the agent loop
is exercised without a live Ollama server.
"""

from __future__ import annotations

from typing import Any

import pytest

from tracearchitect.tooluse import (
    Tool,
    default_test_tools,
    get_locator,
    run_agent,
)


class ScriptedClient:
    """Returns a queued sequence of messages, one per chat() call."""

    def __init__(self, responses: list[dict[str, Any]]):
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    def chat(self, *, model: str, messages: list[dict[str, Any]], tools: Any) -> Any:
        self.calls.append({"model": model, "messages": list(messages), "tools": tools})
        return {"message": self._responses.pop(0)}


def _tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {"function": {"name": name, "arguments": arguments}}


def test_agent_executes_tool_then_answers():
    client = ScriptedClient(
        [
            {"content": "", "tool_calls": [_tool_call("get_locator", {"element": "login button"})]},
            {"content": "Use the selector #login-btn.", "tool_calls": None},
        ]
    )

    result = run_agent(
        "What selector clicks the login button?",
        tools=default_test_tools(),
        client=client,
    )

    assert result.tool_calls == [("get_locator", {"element": "login button"})]
    assert result.answer == "Use the selector #login-btn."
    assert result.steps == 2

    # The tool's real result must have been fed back to the model as a tool message.
    second_call_messages = client.calls[1]["messages"]
    tool_msgs = [m for m in second_call_messages if m.get("role") == "tool"]
    assert tool_msgs == [{"role": "tool", "name": "get_locator", "content": "#login-btn"}]


def test_unknown_tool_reported_to_model_not_crash():
    client = ScriptedClient(
        [
            {"content": "", "tool_calls": [_tool_call("does_not_exist", {})]},
            {"content": "done", "tool_calls": None},
        ]
    )
    result = run_agent("hi", tools=default_test_tools(), client=client)
    fed_back = client.calls[1]["messages"][-1]
    assert fed_back["role"] == "tool"
    assert "unknown tool" in fed_back["content"]
    assert result.answer == "done"


def test_tool_exception_is_caught_and_reported():
    def boom(**_: Any) -> str:
        raise RuntimeError("kaboom")

    bad_tool = Tool(
        name="boom",
        description="always fails",
        parameters={"type": "object", "properties": {}},
        func=boom,
    )
    client = ScriptedClient(
        [
            {"content": "", "tool_calls": [_tool_call("boom", {})]},
            {"content": "handled", "tool_calls": None},
        ]
    )
    result = run_agent("go", tools=[bad_tool], client=client)
    assert "ERROR: RuntimeError: kaboom" in client.calls[1]["messages"][-1]["content"]
    assert result.answer == "handled"


def test_max_steps_guard_raises():
    # Always returns a tool call → never terminates on its own.
    class Loop:
        def chat(self, *, model: str, messages: list[dict[str, Any]], tools: Any) -> Any:
            return {"message": {"content": "", "tool_calls": [_tool_call("list_elements", {})]}}

    with pytest.raises(RuntimeError, match="max_steps"):
        run_agent("loop", tools=default_test_tools(), client=Loop(), max_steps=3)


def test_empty_prompt_rejected():
    with pytest.raises(ValueError):
        run_agent("  ", tools=default_test_tools(), client=ScriptedClient([]))


def test_get_locator_registry():
    assert get_locator("Login Button") == "#login-btn"
    assert get_locator("nonexistent") == "NOT_FOUND"
