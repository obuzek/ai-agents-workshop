# Prerequisites

Complete these steps **before the workshop** to make sure your environment is ready.

## 1. Install Tools

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

---

## 2. Clone and Install

```bash
git clone https://github.com/obuzek/ai-agents-workshop.git
cd ai-agents-workshop
uv sync
```

---

## 3. LLM Provider Setup

The labs call LLMs via API. You need an API key from **one** provider. Labs 1 and 2 work on the Gemini free tier, but **Labs 3 and 4 make 10-15+ LLM calls per run** — more than free-tier rate limits allow. We recommend getting your own paid API key (OpenAI is the cheapest option — the entire workshop costs under $5).

=== "OpenAI (recommended)"
    The best option for the full workshop. Cheap, fast, high rate limits.

    1. Sign up at [platform.openai.com](https://platform.openai.com/)
    2. Add a payment method (credit card required) and set a **usage limit** — $5 is more than enough for the entire workshop
    3. Go to [API Keys](https://platform.openai.com/api-keys) and create a new secret key
    4. Install dependencies and configure your key:

    ```bash
    uv sync --extra openai
    cp .env-example .env
    # Edit .env → uncomment the OpenAI section, set OPENAI_API_KEY=your-key
    ```

    | | |
    |---|---|
    | **Model** | `gpt-4o-mini` (default) |
    | **Cost** | ~$0.15 per 1M input tokens — the entire workshop costs under $5 |
    | **Rate limits** | 500+ requests/min (pay-as-you-go Tier 1) |
    | **Works for** | All labs |

=== "Google Gemini (free)"
    **Free tier, no credit card required** — just a Google account. Good for Labs 1 and 2.

    1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
    2. When prompted to select a project, use the **default project** (usually called "Default Gemini Project" or "Generative Language Client"). Don't create a new project — the Gemini API is already enabled on the default one.
    3. Click **Create API key** and copy it
    4. Install dependencies and configure your key:

    ```bash
    uv sync --extra gemini
    cp .env-example .env
    # Edit .env → set GOOGLE_API_KEY=your-key
    ```

    | | |
    |---|---|
    | **Model** | `gemini-2.5-flash-lite` (default) |
    | **Cost** | Free |
    | **Rate limits** | 15 requests/min, 1,000 requests/day |
    | **Works for** | Labs 1-2 |

    !!! warning "Created a new Google Cloud project?"
        If you created your key in a new project, you'll get an `API_KEY_INVALID` error. Either recreate the key in the default project, or enable the [Generative Language API](https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com) on your project.

    !!! warning "Rate limits for Labs 3+"
        The free tier allows 15 requests per minute. Lab 3's multi-node agent (ReAct + grounding + critic) makes 10-15+ LLM calls per patient, so you'll hit rate limits. For Lab 3 onward, switch to a paid provider (OpenAI is recommended).

=== "Anthropic"
    1. Sign up at [console.anthropic.com](https://console.anthropic.com/)
    2. Add a payment method and go to [API Keys](https://console.anthropic.com/settings/keys) to create a key
    3. Install dependencies and configure your key:

    ```bash
    uv sync --extra anthropic
    cp .env-example .env
    # Edit .env → uncomment the Anthropic section, set ANTHROPIC_API_KEY=your-key
    ```

    | | |
    |---|---|
    | **Model** | `claude-haiku-4-5-20251001` (default) |
    | **Cost** | ~$1 per 1M input tokens — the entire workshop should cost under $5 |
    | **Rate limits** | 50+ requests/min (pay-as-you-go) |
    | **Works for** | All labs |

The total LLM cost for the entire workshop should not exceed **$5** on any paid provider. The workshop uses cheap, fast models — not frontier models — because the goal is learning agent patterns, not benchmarking LLM quality.

See `.env-example` for all available configuration options.

### Verify your API key

After setting up your `.env` file, confirm the LLM is reachable:

```bash
uv run python scripts/check_llm.py
```

You should see a short greeting. If you get an authentication error, double-check your API key in `.env`.

!!! tip "Switching providers mid-workshop"
    Change `LLM_PROVIDER` and the API key in your `.env` file, then restart the agent. No code changes needed.

???+ note "Other free-tier options"
    If you don't want to pay for an API key, these providers offer free tiers with tool calling and structured output. They aren't pre-configured in `app/llm.py` but could be added.

    | Provider | Free RPM | Free RPD | Best model | Catches |
    |----------|---------|---------|------------|---------|
    | [Groq](https://console.groq.com/) | 30 | 1,000 | `llama-4-scout-17b-16e-instruct` | 30K token/min limit; no credit card needed |
    | [Cerebras](https://cloud.cerebras.ai/) | 30 | 14,400 | `llama-3.3-70b` | 8K context window cap — test whether your prompts fit |

---

## 4. Later-Lab Prerequisites

### Docker (Labs 2, 3, 4)

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

### Ollama + Granite Guardian (Lab 3 — optional)

Lab 3 includes a grounding check that compares LLM-as-judge vs. [Granite Guardian](https://www.ibm.com/granite/docs/models/guardian/). The Guardian path is **optional** — the lab works out of the box with LLM-as-judge grounding. If you want to compare both approaches:

1. Install [Ollama](https://ollama.com/)
2. Pull the Granite Guardian model (the `:3b` tag is required — the model has no default tag):

```bash
ollama pull ibm/granite3.2-guardian:3b
```

3. Install the optional Python dependency:

```bash
uv sync --all-extras
```

Verify Ollama has the model:

```bash
ollama list | grep guardian
```

!!! warning "Don't toggle without installing"
    The **Grounding** toggle in Lab 3's UI will switch to Guardian mode, but the agent will crash if `ollama` isn't installed or the model isn't pulled. Only flip the toggle if you completed these steps.

???+ tip "Why Ollama?"
    Granite Guardian runs locally — no API keys, no cloud dependency. Your patient data never leaves your machine, which matters when you're building hallucination detection for healthcare data.

### Postgres via Docker (Lab 4)

Lab 4 stores agent concerns in Postgres with Row-Level Security. The database runs in Docker — no local Postgres installation needed.

```bash
# Start the Lab 4 Postgres database
docker compose up -d

# Verify it's running
docker compose exec postgres psql -U agent -d agent_store -c "SELECT id, display_name FROM providers;"
```

You should see three providers: Dr. Sarah Kim, MD; Rachel Torres, NP; and Maria Gonzalez.

```bash
# Install the Python Postgres driver
uv sync --all-extras
```

???+ tip "Pre-pull the Postgres image"
    ```bash
    docker pull postgres:16
    ```

???+ note "No Docker? Lab 4 still works"
    Without Docker, Lab 4 falls back to the same JSON file store used in Labs 1-3. You'll miss the RLS demo and role switching, but the concern stability and tool scoping features still work. Just skip the `DATABASE_URL` environment variable.

---

## 5. Start the EHR Inbox

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
