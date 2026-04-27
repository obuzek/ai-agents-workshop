# Prerequisites

Complete these steps **before the workshop** to make sure your environment is ready.

## Required for All Labs

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

=== "macOS/Linux"
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    uv --version
    ```

=== "macOS (Homebrew)"
    ```bash
    brew install uv
    uv --version
    ```

=== "Windows"
    <!-- TODO: verify Windows uv install instructions (see issue) -->
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    uv --version
    ```
    Alternatively: `winget install --id=astral-sh.uv -e`

## Required for Lab 2

### Docker

Lab 2 uses [Langfuse](https://langfuse.com/) for LLM observability, running locally via Docker Compose. You don't need Docker for Labs 1, 3, or 4.

=== "macOS"
    Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) or via Homebrew:
    ```bash
    brew install --cask docker
    ```

=== "Linux"
    ```bash
    sudo apt install docker.io docker-compose-plugin
    sudo systemctl enable --now docker
    sudo usermod -aG docker $USER  # log out and back in after this
    ```

=== "Windows"
    Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).

Verify it's working:

```bash
docker compose version
```

???+ tip "Pre-pull the images"
    The Langfuse stack pulls several container images on first run. To avoid waiting during the lab:

    ```bash
    cd ai-agents-workshop
    docker compose -f docker-compose.langfuse.yml pull
    ```

## Optional for Lab 3

### Ollama + Granite Guardian

Lab 3 includes a grounding check that compares LLM-as-judge vs. [Granite Guardian](https://www.ibm.com/granite/docs/models/guardian/). The Guardian path is **optional** — the lab works out of the box with LLM-as-judge grounding. If you want to compare both approaches:

1. Install [Ollama](https://ollama.com/)
2. Pull the Granite Guardian model (the `:3b` tag is required — the model has no default tag):

```bash
ollama pull ibm/granite3.2-guardian:3b
```

Verify it's working:

```bash
ollama list | grep guardian
```

???+ tip "Why Ollama?"
    Granite Guardian runs locally — no API keys, no cloud dependency. Your patient data never leaves your machine, which matters when you're building hallucination detection for healthcare data.

---

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
