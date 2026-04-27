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

Labs 2, 3, and 4 use Docker Compose for various services (Langfuse, Postgres). Install Docker before the workshop.

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
    The Langfuse and Postgres stacks pull container images on first run. To avoid waiting during the labs:

    ```bash
    cd ai-agents-workshop
    docker compose -f docker-compose.langfuse.yml pull  # Lab 2
    docker pull postgres:16                              # Lab 4
    ```

## Optional for Lab 3

### Ollama + Granite Guardian

Lab 3 includes a grounding check that compares LLM-as-judge vs. [Granite Guardian](https://www.ibm.com/granite/docs/models/guardian/). The Guardian path is **optional** — the lab works out of the box with LLM-as-judge grounding. If you want to compare both approaches:

1. Install [Ollama](https://ollama.com/)
2. Pull the Granite Guardian model (the `:3b` tag is required — the model has no default tag):

```bash
ollama pull ibm/granite3.2-guardian:3b
```

3. Install the optional Python dependency:

```bash
uv sync --extra guardian
```

Verify Ollama has the model:

```bash
ollama list | grep guardian
```

!!! warning "Don't toggle without installing"
    The **Grounding** toggle in Lab 3's UI will switch to Guardian mode, but the agent will crash if `ollama` isn't installed or the model isn't pulled. Only flip the toggle if you completed these steps.

???+ tip "Why Ollama?"
    Granite Guardian runs locally — no API keys, no cloud dependency. Your patient data never leaves your machine, which matters when you're building hallucination detection for healthcare data.

## Required for Lab 4

### Postgres (via Docker)

Lab 4 stores agent concerns in Postgres with Row-Level Security. The database runs in Docker — no local Postgres installation needed.

```bash
# Start the Lab 4 Postgres database
docker compose up -d

# Verify it's running
docker compose exec postgres psql -U agent -d agent_store -c "SELECT id, display_name FROM providers;"
```

You should see three providers: Dr. Sarah Kim, Nurse Jordan Lopez, and MA Riley Davis.

```bash
# Install the Python Postgres driver
uv sync --extra postgres
```

???+ tip "Pre-pull the Postgres image"
    ```bash
    docker pull postgres:16
    ```

???+ note "No Docker? Lab 4 still works"
    Without Docker, Lab 4 falls back to the same JSON file store used in Labs 1-3. You'll miss the RLS demo and role switching, but the concern stability and tool scoping features still work. Just skip the `DATABASE_URL` environment variable.

---

## Clone and Install

```bash
git clone https://github.com/obuzek/ai-agents-workshop.git
cd ai-agents-workshop
```

### LLM Provider Setup

The labs need an LLM API key. Pick **one** provider and install its dependencies:

=== "Google Gemini (recommended)"
    **Free tier, no credit card required** — just a Google account.

    1. Go to [Google AI Studio](https://aistudio.google.com/apikey) and create an API key
    2. Install dependencies and configure your key:

    ```bash
    uv sync --extra gemini
    cp .env-example .env
    # Edit .env → set GOOGLE_API_KEY=your-key
    ```

    The free tier is generous enough for a classroom of 30+ concurrent users.

=== "OpenAI"
    Requires an [OpenAI Platform](https://platform.openai.com/) account (pay-as-you-go).

    ```bash
    uv sync --extra openai
    cp .env-example .env
    # Edit .env → uncomment the OpenAI section, set OPENAI_API_KEY=your-key
    ```

=== "Anthropic"
    Requires an [Anthropic Console](https://console.anthropic.com/) account (pay-as-you-go).

    ```bash
    uv sync --extra anthropic
    cp .env-example .env
    # Edit .env → uncomment the Anthropic section, set ANTHROPIC_API_KEY=your-key
    ```

See `.env-example` for all available configuration options.

!!! tip "Switching providers mid-workshop"
    Change `LLM_PROVIDER` and the API key in your `.env` file, then restart the agent. No code changes needed.

???+ note "Instructor note: rate limits"
    The Gemini free tier handles 30-40 concurrent users comfortably. If you hit rate limits mid-session, have attendees switch to a different provider — changing `LLM_PROVIDER` in `.env` is all it takes.

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
