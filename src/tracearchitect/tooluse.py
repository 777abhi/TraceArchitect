"""Day 3 — Function Calling & Tool Use in test automation.

Instead of answering from memory, the model is given a set of *tools* (functions
with JSON-schema signatures). It decides which tool to call and with what
arguments; we execute the tool and feed the result back until the model produces
a final answer. This is the foundation of an "agent".

QA angle: we expose a tiny **locator registry** as tools, so an LLM test agent
can look up real selectors instead of hallucinating them.

Example:
    from tracearchitect.tooluse import run_agent, default_test_tools

    answer = run_agent(
        "What CSS selector should I use to click the login button?",
        tools=default_test_tools(),
    )

The Ollama call is isolated behind a ``ChatClient`` protocol so the agent loop
can be unit-tested offline with a fake client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

DEFAULT_OLLAMA_MODEL = "llama3.2"

_SYSTEM_PROMPT = (
    "You are a test-automation assistant. Use the provided tools to look up "
    "real information (such as element selectors) instead of guessing. "
    "When you have enough information, answer the user concisely."
)


@dataclass
class Tool:
    """A callable tool the model can invoke.

    ``func`` receives keyword arguments matching ``parameters`` and returns a
    string (what the model sees as the tool's result).
    """

    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., str]

    def schema(self) -> dict[str, Any]:
        """The tool definition in the shape Ollama expects."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def run(self, arguments: dict[str, Any]) -> str:
        return self.func(**arguments)


class ChatClient(Protocol):
    """Minimal interface we need from an Ollama-like client."""

    def chat(self, *, model: str, messages: list[dict[str, Any]], tools: Any) -> Any:
        ...


def _field(obj: Any, name: str, default: Any = None) -> Any:
    """Read a field from either a Mapping-like object or an attribute object."""
    try:
        return obj[name]
    except (KeyError, TypeError, IndexError):
        return getattr(obj, name, default)


def _parse_tool_calls(message: Any) -> list[tuple[str, dict[str, Any]]]:
    """Return [(tool_name, arguments), ...] from a chat message, if any."""
    raw = _field(message, "tool_calls") or []
    calls: list[tuple[str, dict[str, Any]]] = []
    for call in raw:
        fn = _field(call, "function")
        name = _field(fn, "name")
        args = _field(fn, "arguments") or {}
        calls.append((str(name), dict(args)))
    return calls


def build_client(host: str | None = None) -> ChatClient:
    """Create a real Ollama client. Imported lazily so tests stay offline."""
    import os

    import ollama

    return ollama.Client(
        host=host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    )


@dataclass
class AgentResult:
    """Outcome of an agent run."""

    answer: str
    tool_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    steps: int = 0


def run_agent(
    prompt: str,
    tools: list[Tool],
    *,
    model: str | None = None,
    host: str | None = None,
    client: ChatClient | None = None,
    max_steps: int = 5,
) -> AgentResult:
    """Run a tool-using agent loop until the model returns a final answer.

    Args:
        prompt: The user's request.
        tools: Tools the model may call.
        model: Ollama model tag; defaults to ``OLLAMA_MODEL`` env or ``llama3.2``.
        host: Ollama base URL.
        client: Optional pre-built chat client (used for testing).
        max_steps: Safety cap on tool-call rounds.

    Returns:
        An :class:`AgentResult` with the final answer and the tools invoked.

    Raises:
        RuntimeError: if the model keeps calling tools past ``max_steps``.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    import os

    model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    client = client or build_client(host)
    registry = {t.name: t for t in tools}
    schemas = [t.schema() for t in tools]

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt.strip()},
    ]

    invoked: list[tuple[str, dict[str, Any]]] = []

    for step in range(1, max_steps + 1):
        response = client.chat(model=model, messages=messages, tools=schemas)
        message = _field(response, "message")
        content = _field(message, "content", "") or ""
        calls = _parse_tool_calls(message)

        if not calls:
            return AgentResult(answer=content, tool_calls=invoked, steps=step)

        # Record the assistant's tool-calling turn so the model keeps context.
        messages.append({"role": "assistant", "content": content})

        for name, arguments in calls:
            invoked.append((name, arguments))
            tool = registry.get(name)
            if tool is None:
                result = f"ERROR: unknown tool {name!r}"
            else:
                try:
                    result = tool.run(arguments)
                except Exception as exc:  # noqa: BLE001 - report tool errors to model
                    result = f"ERROR: {type(exc).__name__}: {exc}"
            messages.append({"role": "tool", "name": name, "content": result})

    raise RuntimeError(f"agent exceeded max_steps ({max_steps}) without answering")


# --- Example tools: a small UI locator registry for a login page -------------

_LOCATORS: dict[str, str] = {
    "login button": "#login-btn",
    "username field": "input[name='username']",
    "password field": "input[name='password']",
    "submit button": "button[type='submit']",
    "forgot password link": "a.forgot-password",
}


def get_locator(element: str) -> str:
    """Return the CSS selector for a named UI element, or NOT_FOUND."""
    return _LOCATORS.get(element.strip().lower(), "NOT_FOUND")


def list_elements() -> str:
    """Return the comma-separated names of known UI elements."""
    return ", ".join(sorted(_LOCATORS))


def default_test_tools() -> list[Tool]:
    """A ready-made toolset exposing the locator registry."""
    return [
        Tool(
            name="get_locator",
            description="Get the CSS selector for a named UI element.",
            parameters={
                "type": "object",
                "properties": {
                    "element": {
                        "type": "string",
                        "description": "Human name of the element, e.g. 'login button'.",
                    }
                },
                "required": ["element"],
            },
            func=get_locator,
        ),
        Tool(
            name="list_elements",
            description="List the names of all known UI elements.",
            parameters={"type": "object", "properties": {}},
            func=lambda: list_elements(),
        ),
    ]
