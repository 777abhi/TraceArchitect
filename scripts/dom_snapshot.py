#!/usr/bin/env python3
"""Day 4 CLI — distill a web page's DOM into a compact accessibility outline.

Usage:
    # Local HTML file (no browser needed):
    python scripts/dom_snapshot.py examples/sample_login.html

    # Live/rendered page via Playwright (http(s):// or file://):
    python scripts/dom_snapshot.py https://example.com
    python scripts/dom_snapshot.py --render examples/sample_login.html

Prints the accessibility outline an LLM would consume, plus the token-ish size
reduction vs. the raw HTML.
"""

from __future__ import annotations

import sys
from pathlib import Path

from tracearchitect.domtree import (
    accessibility_tree,
    accessibility_tree_from_url,
    to_outline,
)


def main(argv: list[str]) -> int:
    render = False
    args = list(argv)
    if args and args[0] == "--render":
        render = True
        args = args[1:]

    if len(args) != 1:
        print(
            "usage: python scripts/dom_snapshot.py [--render] <file-or-url>",
            file=sys.stderr,
        )
        return 2

    target = args[0]
    is_url = target.startswith(("http://", "https://", "file://"))

    try:
        if render or is_url:
            url = target if is_url else Path(target).resolve().as_uri()
            ax = accessibility_tree_from_url(url)
            raw_len = None
        else:
            html = Path(target).read_text(encoding="utf-8")
            ax = accessibility_tree(html)
            raw_len = len(html)
    except Exception as exc:  # noqa: BLE001 - friendly CLI error
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    outline = to_outline(ax)
    print(outline)

    if raw_len is not None:
        reduction = 100 * (1 - len(outline) / raw_len) if raw_len else 0
        print(
            f"\n[{len(outline)} chars of outline vs {raw_len} chars of raw HTML "
            f"— {reduction:.0f}% smaller]",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
