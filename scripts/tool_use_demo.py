#!/usr/bin/env python3
"""Day 3 CLI — a tool-using agent that looks up UI selectors via local Ollama.

Usage:
    python scripts/tool_use_demo.py "What selector clicks the login button?"

The model is given locator-lookup tools and decides when to call them. Reads
OLLAMA_HOST / OLLAMA_MODEL from a local .env (see .env.example). Requires a
running Ollama with the configured model (see docs/day1-setup.md).
"""

from __future__ import annotations

import sys

from tracearchitect.tooluse import default_test_tools, run_agent


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def main(argv: list[str]) -> int:
    prompt = " ".join(argv).strip()
    if not prompt:
        print('usage: python scripts/tool_use_demo.py "<question>"', file=sys.stderr)
        return 2

    _load_env()

    try:
        result = run_agent(prompt, tools=default_test_tools())
    except Exception as exc:  # noqa: BLE001 - friendly CLI error
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(
            "hint: is Ollama running and the model pulled? See docs/day1-setup.md",
            file=sys.stderr,
        )
        return 1

    if result.tool_calls:
        print("Tools called:")
        for name, args in result.tool_calls:
            print(f"  - {name}({args})")
    else:
        print("Tools called: (none)")
    print(f"\nAnswer ({result.steps} step(s)):\n{result.answer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
