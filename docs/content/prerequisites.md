# Prerequisites

Complete these steps **before the workshop** to make sure your environment is ready.

## Required Software

### Python 3.11+

=== "macOS"
    ```bash
    brew install python@3.11
    python3 --version
    ```

=== "Linux"
    ```bash
    sudo apt update
    sudo apt install python3.11 python3.11-venv
    python3 --version
    ```

=== "Windows"
    Download from [python.org](https://www.python.org/downloads/). Check "Add Python to PATH" during installation.

### Git

=== "macOS"
    ```bash
    brew install git
    ```

=== "Linux"
    ```bash
    sudo apt install git
    ```

=== "Windows"
    Download from [git-scm.com](https://git-scm.com/download/win).

### uv (Python package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

## Clone and Install

```bash
git clone https://github.com/obuzek/ai-agents-workshop.git
cd ai-agents-workshop
uv sync
```

## Start the EHR Inbox

The workshop uses a simulated Electronic Health Record (EHR) inbox — a patient portal for **Lakeview Family Medicine**. Start it by running two commands in separate terminals:

**Terminal 1 — API server:**

```bash
uv run uvicorn app.api:app --reload --port 8000
```

**Terminal 2 — Inbox UI:**

```bash
uv run streamlit run app/ui.py --server.port 8501
```

Open [http://localhost:8501](http://localhost:8501) in your browser. You should see the inbox with 12 patients and their portal messages.

??? tip "Changing ports"
    The API and UI ports are configurable:

    ```bash
    # Use different ports
    uv run uvicorn app.api:app --reload --port 9000
    API_URL=http://localhost:9000 uv run streamlit run app/ui.py --server.port 9501
    ```

## Verify It Works

You should see:

- A **patient dropdown** at the top (12 patients, some with unread messages)
- **Medical records** with tabs for Conditions, Medications, Labs, History
- A **Concerns** panel (empty for now — the agent will populate this)
- An **Inbox** with patient messages and a conversation viewer

If you can browse patients and read their messages, you're ready.

## Next Steps

Proceed to [Lab 1: The Naive Agent](./lab-1.md) to start building.
