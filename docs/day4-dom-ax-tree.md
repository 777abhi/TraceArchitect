# Day 4 — Parsing DOM Trees & Accessibility Trees for LLM Context

> Part of the [Agentic AI & Generative AI Test Orchestration — Learning Roadmap](../LEARNING_ROADMAP.md).
> Prereq: [Day 1 setup](./day1-setup.md) (Playwright installed for the optional live-render step).

A 30-minute lesson. Goal: turn a noisy web page into a small, stable
representation an LLM can actually reason about.

## 10 min — Theory

If you paste raw HTML into a prompt you waste thousands of tokens on `<div>`
soup, inline styles, and `<script>` noise — and the model still struggles to
find "the login button". The fix is to give the model an **accessibility tree**:
the same semantic model screen readers use. Each meaningful element becomes a
node with:

- **role** — `button`, `textbox`, `link`, `heading`, `navigation`, ...
- **accessible name** — how a user refers to it ("Username", "Log in")
- **value** — e.g. a checkbox's `checked` state
- a **selector** — so the agent can act on it later (Day 6+)

Two important rules this module follows:

1. **Prune the noise.** `<script>`, `<style>`, and non-semantic wrappers are
   dropped; their interesting descendants are hoisted up.
2. **Accessible name depends on role.** Buttons/links/headings take their name
   from text content; form controls from their `<label for=...>` /
   `placeholder`; landmarks (`main`, `nav`, `form`) are named *only* by
   `aria-label` — not their concatenated text.

`src/tracearchitect/domtree.py` implements this with the **standard library
only** (`html.parser`), so it's deterministic and offline. A lazily-imported
Playwright helper (`accessibility_tree_from_url`) renders a live page first, when
you need the *rendered* DOM (post-JavaScript).

## 15 min — Hands-on

1. Distill the bundled sample page (no browser needed):

   ```bash
   python scripts/dom_snapshot.py examples/sample_login.html
   ```

   Output — the compact outline an LLM would consume:

   ```
   banner  [header]
     navigation "Primary"  [nav]
       link "Home"  [a[href='/']]
       link "Help"  [a[href='/help']]
   main  [main]
     heading "Sign in"  [h1]
     form  [#login-form]
       textbox "Username"  [#username]
       textbox "Password"  [#password]
       checkbox "Remember me" (value: checked)  [#remember]
       button "Log in"  [#login-btn]
       link "Forgot password?"  [a[href='/reset']]
   contentinfo  [footer]

   [560 chars of outline vs 1187 chars of raw HTML — 53% smaller]
   ```

2. Render a live/JS page through Playwright instead (needs `playwright install`):

   ```bash
   python scripts/dom_snapshot.py https://example.com
   python scripts/dom_snapshot.py --render examples/sample_login.html
   ```

3. Use it from Python:

   ```python
   from tracearchitect.domtree import accessibility_tree, interactive_elements, to_outline

   ax = accessibility_tree(html)
   print(to_outline(ax))                       # LLM-friendly outline
   for el in interactive_elements(html):       # just the controls to act on
       print(el.role, el.name, el.selector)
   ```

4. Run the offline tests:

   ```bash
   pytest tests/test_domtree.py -q
   ```

## 5 min — Reflection

- Why is the accessibility tree more robust for an LLM than a CSS/XPath dump of
  every node? (Fewer, semantic, human-meaningful nodes.)
- Notice landmarks have no name unless you add `aria-label` — that's real ARIA
  behavior, and a hint about writing accessible apps.
- This feeds Day 5 (generate Playwright tests from a page) and the Day 6+
  agent loop, which needs `role + name + selector` to decide what to click.

When the CLI prints the outline and `pytest tests/test_domtree.py` passes,
**Day 4 is complete.** Confirm before moving to Day 5.
