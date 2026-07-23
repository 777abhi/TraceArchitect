"""Offline tests for the Day 4 DOM / accessibility-tree extractor."""

from __future__ import annotations

from pathlib import Path

from tracearchitect.domtree import (
    accessibility_tree,
    flatten,
    interactive_elements,
    role_of,
    parse_dom,
    to_outline,
)

SAMPLE = (
    Path(__file__).resolve().parent.parent / "examples" / "sample_login.html"
).read_text(encoding="utf-8")


def _roles(nodes):
    return [(n.role, n.name) for n in nodes]


def test_script_and_style_are_pruned():
    outline = to_outline(accessibility_tree(SAMPLE))
    assert "noise the LLM does not need" not in outline
    assert "display: none" not in outline


def test_form_controls_have_roles_names_and_selectors():
    nodes = {n.selector: n for n in flatten(accessibility_tree(SAMPLE))}

    username = nodes["#username"]
    assert username.role == "textbox"
    # accessible name comes from the associated <label for="username">
    assert username.name == "Username"

    password = nodes["#password"]
    assert password.role == "textbox"
    assert password.name == "Password"

    login = nodes["#login-btn"]
    assert login.role == "button"
    assert login.name == "Log in"


def test_checkbox_value_and_name():
    remember = next(
        n for n in flatten(accessibility_tree(SAMPLE)) if n.selector == "#remember"
    )
    assert remember.role == "checkbox"
    assert remember.name == "Remember me"
    assert remember.value == "checked"


def test_landmarks_and_heading_present():
    roles = [n.role for n in flatten(accessibility_tree(SAMPLE))]
    assert "navigation" in roles
    assert "main" in roles
    assert "banner" in roles
    assert "contentinfo" in roles
    assert "heading" in roles


def test_links_kept_only_with_href():
    # <a href="/reset"> becomes a link; a bare <a> would not.
    dom_link = parse_dom('<a href="/x">go</a>').children[0]
    dom_anchor = parse_dom("<a>go</a>").children[0]
    assert role_of(dom_link) == "link"
    assert role_of(dom_anchor) is None


def test_interactive_elements_are_the_controls():
    controls = _roles(interactive_elements(SAMPLE))
    assert ("textbox", "Username") in controls
    assert ("textbox", "Password") in controls
    assert ("checkbox", "Remember me") in controls
    assert ("button", "Log in") in controls
    assert ("link", "Forgot password?") in controls
    # The footer paragraph is not interactive.
    assert all(role != "contentinfo" for role, _ in controls)


def test_outline_is_indented_and_compact():
    outline = to_outline(accessibility_tree(SAMPLE))
    assert 'heading "Sign in"' in outline
    assert 'textbox "Username"  [#username]' in outline
    # Nested under nav/main via indentation.
    assert any(line.startswith("  ") for line in outline.splitlines())
    # Much smaller than the raw HTML.
    assert len(outline) < len(SAMPLE)


def test_aria_label_overrides_name():
    ax = accessibility_tree('<button aria-label="Close dialog">x</button>')
    node = flatten(ax)[0]
    assert node.role == "button"
    assert node.name == "Close dialog"
