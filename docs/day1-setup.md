# Day 1 — Local Setup (Ollama edition)

> Part of the [Agentic AI & Generative AI Test Orchestration — Learning Roadmap](../LEARNING_ROADMAP.md).
> Goal: a reproducible, **fully offline** local dev environment using a local
> [Ollama](https://ollama.com) install as the LLM backend — no hosted or paid API key.

This is a 30-minute lesson. Work through the steps below, then run the
verification script at the end. When every check prints **PASS**, Day 1 is done.

---

## 1. Install Python 3.11+

Download and install Python **3.11 or newer** from
[python.org/downloads](https://www.python.org/downloads/) (macOS/Windows) or your
package manager (Linux). Verify:

```bash
python --version
# or, if your system uses `python3`:
python3 --version
```

You should see `Python 3.11.x` (or higher).

## 2. Create and activate a virtual environment

From the repository root:

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Your shell prompt should now be prefixed with `(.venv)`.

## 3. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs `playwright`, `python-dotenv`, and the official `ollama` client.

## 4. Install Playwright browsers

Playwright needs its browser binaries (we use headless Chromium):

```bash
playwright install
```

> On Linux you may also need system libraries: `playwright install-deps`
> (or `sudo playwright install-deps`).

## 5. Install and start Ollama

1. Install Ollama for macOS / Windows / Linux from
   [ollama.com/download](https://ollama.com/download).
2. Pull the small default model used for Day 1:

   ```bash
   ollama pull llama3.2
   ```

3. Make sure the Ollama server is running. On macOS/Windows the desktop app
   starts it automatically. On Linux (or if it is not already running) start it
   manually:

   ```bash
   ollama serve
   ```

   The server listens on `http://localhost:11434` by default.

## 6. Verify Ollama responds

```bash
ollama run llama3.2 "hello"
```

You should get a short text reply. This confirms the model is downloaded and the
local LLM backend works entirely offline.

## 7. Configure environment variables

Copy the example file and adjust if needed:

```bash
cp .env.example .env
```

Defaults:

| Variable       | Default                  | Description                     |
| -------------- | ------------------------ | ------------------------------- |
| `OLLAMA_HOST`  | `http://localhost:11434` | Base URL of your Ollama server. |
| `OLLAMA_MODEL` | `llama3.2`               | Model used for Day 1 checks.    |

## 8. VS Code recommended extensions

Open the repo in VS Code. It will offer to install the recommended extensions
(see [`.vscode/extensions.json`](../.vscode/extensions.json)):

- **Python** (`ms-python.python`)
- **Playwright Test for VS Code** (`ms-playwright.playwright`)

## 9. Run the verification script

```bash
python scripts/verify_setup.py
```

You should see a **PASS** for each check:

```
Python version >= 3.11 ......... PASS
Playwright (headless Chromium) . PASS
Ollama endpoint + model ........ PASS
```

When all three pass, **Day 1 is complete**. Confirm with your mentor / roadmap
before moving on to Day 2.

### Troubleshooting

- **Playwright fails to launch** — run `playwright install` (and on Linux
  `playwright install-deps`).
- **Ollama endpoint unreachable** — make sure `ollama serve` is running and
  `OLLAMA_HOST` matches (default `http://localhost:11434`).
- **Model not found** — run `ollama pull llama3.2` (or set `OLLAMA_MODEL` to a
  model you have pulled; list them with `ollama list`).
