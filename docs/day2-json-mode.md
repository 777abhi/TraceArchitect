# Day 2 — Structured Outputs & JSON Mode

> Part of the [Agentic AI & Generative AI Test Orchestration — Learning Roadmap](../LEARNING_ROADMAP.md).
> Prereq: [Day 1 setup](./day1-setup.md) complete (local Ollama running with `llama3.2`).

A 30-minute lesson. Goal: stop treating the LLM as a free-text oracle and start
getting **structured, validated output** you can build on.

## 10 min — Theory

LLMs love prose. Automation hates prose. If you ask a model "write a test case"
you get paragraphs you have to parse by hand — brittle and unreliable.

**Structured outputs / JSON mode** fix this: you give the model a *schema* and
constrain it to emit JSON that matches. Ollama supports this via the `format`
parameter of `chat()`:

- `format="json"` — "reply with any valid JSON".
- `format=<json-schema-dict>` — "reply with JSON matching this exact schema"
  (what we use here).

We define the schema with **Pydantic**, pass `Model.model_json_schema()` as
`format`, then validate the reply with `Model.model_validate_json(...)`. If the
model drifts from the schema, validation raises instead of silently returning
garbage.

Our schema (`src/tracearchitect/testgen.py`):

```python
class TestStep(BaseModel):
    action: str
    expected_result: str

class GeneratedTestCase(BaseModel):
    title: str
    summary: str
    priority: str  # ^(low|medium|high|critical)$
    tags: list[str] = []
    steps: list[TestStep]  # at least one
```

## 15 min — Hands-on

1. Make sure Ollama is running and the model is pulled (from Day 1):

   ```bash
   ollama serve            # if not already running
   ollama pull llama3.2
   ```

2. Activate your venv and generate a test case from a user story:

   ```bash
   python scripts/generate_testcase.py "As a user I can reset my password via email"
   ```

   You should get pretty-printed JSON like:

   ```json
   {
     "title": "Password reset via email",
     "summary": "User can reset their password using an emailed link.",
     "priority": "high",
     "tags": ["auth", "email"],
     "steps": [
       { "action": "Click 'Forgot password'", "expected_result": "Reset form is shown" },
       { "action": "Submit registered email", "expected_result": "'Email sent' banner appears" }
     ]
   }
   ```

3. Try a few different user stories and notice the output *always* has the same
   shape — that's the point.

4. Run the offline tests (these use a fake client, so no Ollama needed):

   ```bash
   pytest tests/test_testgen.py -q
   ```

### How it works in code

`generate_test_case()` isolates the network call behind a small `ChatClient`
protocol, so the parsing/validation logic is unit-testable without a live model:

```python
tc = generate_test_case("As a user I can log in", client=my_client)
```

In production `client` defaults to a real `ollama.Client`; in tests we inject a
fake that returns canned JSON.

## 5 min — Reflection

- What happens if the model returns `"priority": "urgent"`? (Try it — validation
  rejects it, because the schema only allows low/medium/high/critical.)
- Why is validating the output just as important as requesting JSON?
- Where could a structured test case feed next? (Day 5 turns these into runnable
  Playwright tests.)

When the CLI produces valid JSON and `pytest tests/test_testgen.py` passes,
**Day 2 is complete.** Confirm before moving to Day 3.
