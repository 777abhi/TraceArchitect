# Day 3 — Function Calling & Tool Use

> Part of the [Agentic AI & Generative AI Test Orchestration — Learning Roadmap](../LEARNING_ROADMAP.md).
> Prereq: [Day 1 setup](./day1-setup.md) complete (local Ollama with `llama3.2`).

A 30-minute lesson. Goal: let the model *do things* by calling functions you
control, instead of answering from memory.

## 10 min — Theory

Day 2 constrained the model's **output**. Day 3 gives the model **actions**.

With **function calling / tool use** you pass the model a list of tools — each a
function name, description, and a JSON-schema for its arguments. The model
replies not with prose but with a *tool call*: "call `get_locator` with
`{element: 'login button'}`". Your code executes the function, feeds the result
back, and the model continues until it produces a final answer. That
call → execute → feed-back loop is the essence of an **agent**.

Why it matters for QA: an LLM guessing a CSS selector is dangerous. An LLM that
*looks up* the real selector from a registry is useful. Tools ground the model
in reality.

Ollama supports this via the `tools` argument of `chat()`; the reply may contain
`message.tool_calls`:

```python
resp = client.chat(model=model, messages=msgs, tools=[tool.schema() for tool in tools])
for call in resp["message"]["tool_calls"] or []:
    name = call["function"]["name"]
    args = dict(call["function"]["arguments"])
    result = registry[name].run(args)          # execute the real function
    msgs.append({"role": "tool", "name": name, "content": result})  # feed back
```

The agent loop lives in `src/tracearchitect/tooluse.py` (`run_agent`), with a
tiny locator registry exposed as tools (`default_test_tools`).

## 15 min — Hands-on

1. Ensure Ollama is running with the model (from Day 1):

   ```bash
   ollama serve            # if not already running
   ollama pull llama3.2
   ```

2. Ask the agent a question that requires a tool:

   ```bash
   python scripts/tool_use_demo.py "What CSS selector should I use to click the login button?"
   ```

   Expected output shows the tool the model chose and the grounded answer:

   ```
   Tools called:
     - get_locator({'element': 'login button'})

   Answer (2 step(s)):
   Use the selector #login-btn to click the login button.
   ```

3. Try `"List all the UI elements you know about"` — the model should call
   `list_elements` instead. Try an unknown element and watch it get `NOT_FOUND`.

4. Run the offline tests (fake client, no Ollama needed):

   ```bash
   pytest tests/test_tooluse.py -q
   ```

### Adding your own tool

A tool is just a name, description, JSON-schema, and a function returning a
string:

```python
Tool(
    name="get_locator",
    description="Get the CSS selector for a named UI element.",
    parameters={"type": "object",
                "properties": {"element": {"type": "string"}},
                "required": ["element"]},
    func=get_locator,
)
```

The loop is defensive: unknown tools and tool exceptions are reported back to the
model as `ERROR: ...` (not crashes), and `max_steps` caps runaway loops.

### A note on small models

Function calling is only as reliable as the model. Small local models like
`llama3.2` *occasionally* emit the tool call as plain text instead of a proper
`tool_calls` field — you'll see the JSON in the answer and "Tools called:
(none)". Just re-run, phrase the request to explicitly mention using the tools,
or use a larger model. This is a model limitation, not a bug in the loop; the
offline tests exercise the loop deterministically.

## 5 min — Reflection

- What stops the model from hallucinating a selector now? (It must call the tool;
  unknown names return `NOT_FOUND`.)
- Why feed tool errors back to the model instead of raising immediately?
- Days 6–10 grow this loop into a self-healing test runner.

When the demo calls a tool and answers, and `pytest tests/test_tooluse.py`
passes, **Day 3 is complete.** Confirm before moving to Day 4.
