#!/usr/bin/env python3
"""Day 2 CLI — generate a structured test case from a user story via local Ollama.

Usage:
    python scripts/generate_testcase.py "As a user I can reset my password via email"

Reads OLLAMA_HOST / OLLAMA_MODEL from a local .env (see .env.example).
Prints the validated test case as pretty JSON. Requires a running Ollama with
the configured model pulled (see docs/day1-setup.md).
"""

from __future__ import annotations

import sys

from tracearchitect.testgen import generate_test_case


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not argv[0].strip():
        print(
            'usage: python scripts/generate_testcase.py "<user story>"',
            file=sys.stderr,
        )
        return 2

    _load_env()

    try:
        test_case = generate_test_case(argv[0])
    except Exception as exc:  # noqa: BLE001 - surface a friendly CLI error
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(
            "hint: is Ollama running and the model pulled? See docs/day1-setup.md",
            file=sys.stderr,
        )
        return 1

    print(test_case.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
