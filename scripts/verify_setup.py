#!/usr/bin/env python3
"""Day 1 setup verification for the Ollama-based learning environment.

Runs a small set of independent checks and prints a clear PASS/FAIL summary:

1. Python version >= 3.11
2. Playwright can launch headless Chromium and load a simple page
3. The Ollama endpoint is reachable and the configured model responds

Configuration is loaded from a local ``.env`` file (see ``.env.example``) via
python-dotenv. The script always runs every check and exits non-zero if any
check fails, so it is safe to use in CI or a pre-flight step.

Usage:
    python scripts/verify_setup.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

MIN_PYTHON = (3, 11)
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def _load_env() -> None:
    """Load variables from a local .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        print(
            "note: python-dotenv not installed; "
            "reading configuration from the environment only.",
            file=sys.stderr,
        )
        return
    load_dotenv()


def check_python_version() -> CheckResult:
    name = f"Python version >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
    current = sys.version_info[:3]
    ok = sys.version_info[:2] >= MIN_PYTHON
    detail = "found {}.{}.{}".format(*current)
    return CheckResult(name, ok, detail)


def check_playwright() -> CheckResult:
    name = "Playwright (headless Chromium)"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return CheckResult(
            name, False, "playwright not installed (pip install -r requirements.txt)"
        )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.set_content("<h1>ok</h1>")
                heading = page.inner_text("h1")
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001 - report any launch/render failure
        hint = "run `playwright install` (and `playwright install-deps` on Linux)"
        return CheckResult(name, False, f"{type(exc).__name__}: {exc} — {hint}")

    if heading.strip() != "ok":
        return CheckResult(name, False, f"unexpected page content: {heading!r}")
    return CheckResult(name, True, "launched Chromium and rendered a page")


def check_ollama() -> CheckResult:
    name = "Ollama endpoint + model"
    host = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
    model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

    try:
        import ollama
    except ImportError:
        return CheckResult(
            name, False, "ollama client not installed (pip install -r requirements.txt)"
        )

    client = ollama.Client(host=host)

    try:
        available = client.list().get("models", [])
    except Exception as exc:  # noqa: BLE001 - connection/other errors
        hint = f"is `ollama serve` running at {host}?"
        return CheckResult(name, False, f"cannot reach {host}: {exc} — {hint}")

    def _model_name(entry: object) -> str:
        if isinstance(entry, dict):
            return str(entry.get("model") or entry.get("name") or "")
        return str(getattr(entry, "model", "") or getattr(entry, "name", ""))

    names = [_model_name(m) for m in available]
    # Ollama reports tagged names like "llama3.2:latest"; match the base too.
    has_model = any(n == model or n.split(":", 1)[0] == model for n in names)
    if not has_model:
        listed = ", ".join(n for n in names if n) or "none"
        return CheckResult(
            name,
            False,
            f"model {model!r} not found (available: {listed}) — run `ollama pull {model}`",
        )

    try:
        resp = client.chat(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
        )
        content = resp["message"]["content"]
    except Exception as exc:  # noqa: BLE001 - generation errors
        return CheckResult(name, False, f"model {model!r} did not respond: {exc}")

    if not content.strip():
        return CheckResult(name, False, f"model {model!r} returned an empty response")
    return CheckResult(name, True, f"{model} responded at {host}")


def main() -> int:
    _load_env()

    checks = [
        check_python_version,
        check_playwright,
        check_ollama,
    ]

    results = [check() for check in checks]

    width = max(len(r.name) for r in results)
    print("\nDay 1 setup verification\n" + "=" * 40)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        line = f"{r.name.ljust(width)} : {status}"
        if r.detail:
            line += f"  ({r.detail})"
        print(line)

    passed = sum(1 for r in results if r.passed)
    print("=" * 40)
    print(f"{passed}/{len(results)} checks passed.")

    if passed == len(results):
        print("\nAll checks passed — Day 1 setup is complete!")
        return 0
    print("\nSome checks failed — see docs/day1-setup.md for help.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
