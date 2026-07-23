"""Day 4 — Parsing DOM Trees & Accessibility Trees for LLM context.

Raw HTML is huge and noisy — a poor way to give an LLM "what's on the page".
This module distills HTML into a compact **accessibility tree**: only the
elements that matter (interactive controls, headings, landmarks, images), each
with its ARIA-style role, accessible name, value, and a usable CSS selector.
That representation is small, stable, and easy for a model to reason over.

The parser is pure standard library (``html.parser``), so it is fully offline
and deterministic — ideal for unit tests. A separate, lazily-imported Playwright
helper (:func:`accessibility_tree_from_url`) renders a live page first.

Example:
    from tracearchitect.domtree import accessibility_tree, to_outline

    ax = accessibility_tree(html)
    print(to_outline(ax))
    # heading "Sign in"
    # textbox "Username"  [input[name='username']]
    # textbox "Password"  [input[name='password']]
    # button "Log in"  [#login-btn]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

# Tags that carry no semantics we want to keep; children are hoisted up.
_VOID_TAGS = {"br", "hr", "meta", "link", "source", "track", "wbr", "col"}
_SKIP_SUBTREE = {"script", "style", "template", "noscript", "head"}

_LANDMARK_ROLES = {
    "nav": "navigation",
    "main": "main",
    "header": "banner",
    "footer": "contentinfo",
    "aside": "complementary",
    "form": "form",
}

_INPUT_TYPE_ROLES = {
    "text": "textbox",
    "email": "textbox",
    "password": "textbox",
    "search": "searchbox",
    "tel": "textbox",
    "url": "textbox",
    "number": "spinbutton",
    "checkbox": "checkbox",
    "radio": "radio",
    "range": "slider",
    "submit": "button",
    "button": "button",
    "reset": "button",
}

# Roles we keep in the accessibility tree (everything else is pruned/flattened).
_INTERESTING_ROLES = {
    "link",
    "button",
    "textbox",
    "searchbox",
    "spinbutton",
    "checkbox",
    "radio",
    "slider",
    "combobox",
    "heading",
    "img",
    "navigation",
    "main",
    "banner",
    "contentinfo",
    "complementary",
    "form",
}


@dataclass
class DomNode:
    """A raw parsed HTML element (or text)."""

    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["DomNode"] = field(default_factory=list)
    text: str = ""  # only set for text nodes (tag == "#text")

    def is_text(self) -> bool:
        return self.tag == "#text"


@dataclass
class AxNode:
    """A node in the distilled accessibility tree."""

    role: str
    name: str = ""
    value: str = ""
    selector: str = ""
    children: list["AxNode"] = field(default_factory=list)


class _DomBuilder(HTMLParser):
    """Builds a DomNode tree from HTML using a stack."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = DomNode(tag="#root")
        self._stack: list[DomNode] = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _VOID_TAGS:
            node = DomNode(tag=tag, attrs={k: v or "" for k, v in attrs})
            self._stack[-1].children.append(node)
            return
        node = DomNode(tag=tag, attrs={k: v or "" for k, v in attrs})
        self._stack[-1].children.append(node)
        self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = DomNode(tag=tag, attrs={k: v or "" for k, v in attrs})
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        # Close back to the matching open tag, tolerating unclosed tags.
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._stack[-1].children.append(DomNode(tag="#text", text=data))


def parse_dom(html: str) -> DomNode:
    """Parse HTML into a DomNode tree rooted at a ``#root`` node."""
    builder = _DomBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


def _text_content(node: DomNode) -> str:
    """Concatenated, whitespace-normalized visible text under a node."""
    parts: list[str] = []
    for child in node.children:
        if child.is_text():
            parts.append(child.text)
        elif child.tag not in _SKIP_SUBTREE:
            parts.append(_text_content(child))
    return " ".join(" ".join(parts).split())


def role_of(node: DomNode) -> str | None:
    """Map an element to an ARIA-style role, or None if uninteresting."""
    if node.is_text() or node.tag in _VOID_TAGS:
        return None
    explicit = node.attrs.get("role")
    if explicit:
        return explicit
    tag = node.tag
    if tag in _LANDMARK_ROLES:
        return _LANDMARK_ROLES[tag]
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return "heading"
    if tag == "a":
        return "link" if node.attrs.get("href") else None
    if tag == "button":
        return "button"
    if tag == "select":
        return "combobox"
    if tag == "textarea":
        return "textbox"
    if tag == "img":
        return "img"
    if tag == "input":
        input_type = node.attrs.get("type", "text").lower()
        if input_type == "hidden":
            return None
        return _INPUT_TYPE_ROLES.get(input_type, "textbox")
    return None


def _collect_labels(root: DomNode, into: dict[str, str]) -> None:
    """Map form-control id -> its <label for=id> text."""
    if root.tag == "label":
        target = root.attrs.get("for")
        if target:
            into[target] = _text_content(root)
    for child in root.children:
        if not child.is_text():
            _collect_labels(child, into)


# Roles whose accessible name comes from their text content. Landmarks
# (navigation, main, banner, form, ...) are named only via aria-label.
_NAME_FROM_CONTENT_ROLES = {"link", "button", "heading"}


def _accessible_name(node: DomNode, role: str, labels: dict[str, str]) -> str:
    aria = node.attrs.get("aria-label")
    if aria:
        return aria.strip()
    if node.tag == "img":
        return node.attrs.get("alt", "").strip()
    if node.tag in ("input", "select", "textarea"):
        node_id = node.attrs.get("id")
        if node_id and node_id in labels:
            return labels[node_id]
        return (
            node.attrs.get("placeholder")
            or node.attrs.get("title")
            or node.attrs.get("name", "")
        ).strip()
    if role in _NAME_FROM_CONTENT_ROLES:
        return _text_content(node)
    return ""


def _control_value(node: DomNode) -> str:
    if node.tag == "input":
        input_type = node.attrs.get("type", "text").lower()
        if input_type in ("checkbox", "radio"):
            return "checked" if "checked" in node.attrs else "unchecked"
        return node.attrs.get("value", "")
    return ""


def _selector_for(node: DomNode, role: str) -> str:
    node_id = node.attrs.get("id")
    if node_id:
        return f"#{node_id}"
    name = node.attrs.get("name")
    if name:
        return f"{node.tag}[name='{name}']"
    if node.tag == "a" and node.attrs.get("href"):
        return f"a[href='{node.attrs['href']}']"
    if role == "heading":
        return node.tag  # h1..h6
    return node.tag


def _build_ax(node: DomNode, labels: dict[str, str]) -> list[AxNode]:
    """Recursively distill children into interesting AxNodes (pruning wrappers)."""
    out: list[AxNode] = []
    for child in node.children:
        if child.is_text() or child.tag in _SKIP_SUBTREE:
            continue
        role = role_of(child)
        sub = _build_ax(child, labels)
        if role in _INTERESTING_ROLES:
            ax = AxNode(
                role=role,
                name=_accessible_name(child, role, labels),
                value=_control_value(child),
                selector=_selector_for(child, role),
                children=sub,
            )
            out.append(ax)
        else:
            # Uninteresting wrapper: hoist its interesting descendants up.
            out.extend(sub)
    return out


def accessibility_tree(html: str) -> AxNode:
    """Distill HTML into a compact accessibility tree under a ``document`` root."""
    dom = parse_dom(html)
    labels: dict[str, str] = {}
    _collect_labels(dom, labels)
    return AxNode(role="document", children=_build_ax(dom, labels))


def flatten(ax: AxNode) -> list[AxNode]:
    """Depth-first list of all nodes except the synthetic document root."""
    out: list[AxNode] = []

    def walk(node: AxNode) -> None:
        for child in node.children:
            out.append(child)
            walk(child)

    walk(ax)
    return out


def interactive_elements(html: str) -> list[AxNode]:
    """Flat list of the interactive controls on the page."""
    interactive = {
        "link",
        "button",
        "textbox",
        "searchbox",
        "spinbutton",
        "checkbox",
        "radio",
        "slider",
        "combobox",
    }
    return [n for n in flatten(accessibility_tree(html)) if n.role in interactive]


def to_outline(ax: AxNode) -> str:
    """Render the accessibility tree as a compact indented outline for an LLM."""
    lines: list[str] = []

    def render(node: AxNode, depth: int) -> None:
        for child in node.children:
            indent = "  " * depth
            piece = f'{child.role} "{child.name}"' if child.name else child.role
            if child.value:
                piece += f" (value: {child.value})"
            if child.selector:
                piece += f"  [{child.selector}]"
            lines.append(indent + piece)
            render(child, depth + 1)

    render(ax, 0)
    return "\n".join(lines)


def accessibility_tree_from_url(
    url: str, *, timeout_ms: int = 15000
) -> AxNode:
    """Render a page with headless Chromium (Playwright), then distill its DOM.

    Playwright is imported lazily so the rest of this module stays dependency-free
    and offline-testable.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=timeout_ms, wait_until="load")
            html = page.content()
        finally:
            browser.close()
    return accessibility_tree(html)
