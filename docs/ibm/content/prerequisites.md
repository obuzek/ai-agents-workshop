# Prerequisites

Complete these steps **before the workshop** to make sure your environment is ready.

## 1. IBM Cloud: log in

The workshop runs on IBM Cloud. Your agent is deployed to **watsonx Orchestrate**, and watsonx.governance evaluates it. Your code talks to IBM Cloud with an **API key**: a long secret string that acts on your behalf. You'll create it in step 3, right before the installer asks for it.

### Log in to IBM Cloud

1. Open the **login link** from your instructor.
2. Sign in with the **username and password** for your workshop seat.
3. You land on the IBM Cloud dashboard at [cloud.ibm.com](https://cloud.ibm.com).

### Open watsonx once

The labs use watsonx.governance to evaluate your agent. Its features need a watsonx user profile, and IBM creates that profile the first time you open watsonx. Do this once, before the workshop:

1. In the menu on the left, open the **Resource list**.
2. Expand **AI / Machine Learning** and click the workshop's **watsonx.ai Studio** instance. Its name starts with `ws-`.
3. Click **Launch** and choose **IBM watsonx**.
4. Accept the terms if asked, and wait for the watsonx home page to load. You can close it afterwards.

!!! warning "Skip this and Lab 3 won't work"
    Without this one-time visit, watsonx.governance calls fail with an authorization error ("Failed to verify user profile existence").

---

## 2. Set up IBM Bob

You'll work in **IBM Bob**, IBM's AI-powered IDE, and run every command in Bob's built-in terminal. On Windows, Bob connects to a Linux environment (WSL), so everyone runs the same commands.

=== "macOS"

    1. Download and install [IBM Bob](https://bob.ibm.com/?lnk=hpfp2us), open it, and log in to your Bob account.
    2. Open a terminal inside Bob: **Terminal → New Terminal** (or <kbd>Ctrl</kbd>+<kbd>`</kbd>).

    Use this terminal for **3. Run the installer** below and every command in the labs.

    !!! tip "If macOS asks to install the Command Line Tools"
        The installer needs `git`, which comes with Apple's Command Line Tools. If a window pops up asking to install them, click **Install**, wait for it to finish, then run the installer again.

=== "Windows"

    On Windows, the workshop runs inside **WSL** (Windows Subsystem for Linux), using the **FedoraLinux-44** distribution, which is already installed on the workshop machines. Bob connects to it, so your terminal and files are in Linux.

    **Open FedoraLinux-44**

    1. Open the Start menu, search for **FedoraLinux-44**, and open it. This starts Fedora; when you see a prompt, you can close the window.

    **Connect IBM Bob to WSL**

    2. Open **IBM Bob** and log in to your Bob account.
    3. Open the **Extensions** view (the icon of four squares in the left bar), search for **Open Remote - WSL**, and install the extension by **jeanp413**.
    4. Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> to open the command palette, type **WSL**, and choose **Remote-WSL: Connect to WSL**. A new Bob window opens, connected to FedoraLinux-44. Use this new window from here on.
    5. In the new window, open a terminal: **Terminal → New Terminal**. It runs inside Fedora. Use it for **3. Run the installer** below and every command in the labs.

    ??? tip "On a VPN or behind a corporate proxy?"
        If downloads fail inside Fedora but work in Windows, see Microsoft's [WSL networking troubleshooting](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting).

=== "Linux"

    1. Download and install [IBM Bob](https://bob.ibm.com/?lnk=hpfp2us), open it, and log in to your Bob account.
    2. Open a terminal inside Bob: **Terminal → New Terminal** (or <kbd>Ctrl</kbd>+<kbd>`</kbd>).

    The installer uses your package manager (`dnf`, `apt` or `zypper`) with `sudo` for anything missing, so it may ask for your password.

---

## 3. Run the installer

### Create your API key

Keep Bob open, and in your browser at [cloud.ibm.com](https://cloud.ibm.com):

1. In the **top menu bar**, open the **Manage** dropdown and choose **Access (IAM)**.
2. In the **IAM menu on the left**, find the **Manage identities** heading and click **API keys** underneath it.
3. Click **Create**.
4. Give the key a name, such as `ai-agents-workshop`, and click **Create**.
5. Click **Copy** to copy the key. Leave this browser tab open until the installer has accepted it.

!!! warning "You only see the key once"
    IBM Cloud shows the key only when you create it. If you close the dialog before the installer accepts it, delete that key and create a new one.

### Run it

In Bob's terminal from step 2 (on Windows, the Bob window connected to WSL), run:

```bash
curl -LsSf https://raw.githubusercontent.com/obuzek/ai-agents-workshop/txc-2026-ibm/scripts/install.sh | bash
```

You don't need Homebrew or a preinstalled Python. The installer:

1. Installs `git`, `curl`, `tar` and `gzip` if they're missing (on Fedora that's usually just `git`), using your package manager with `sudo`, which may ask for your Linux password.
2. Installs [uv](https://docs.astral.sh/uv/), which also downloads Python 3.12 for the workshop.
3. Downloads the workshop into `~/ai-agents-workshop`.
4. Installs the workshop's Python packages.
5. Installs the watsonx Orchestrate command-line tool, `orchestrate`.
6. Connects you to IBM Cloud with your API key (see below).

It's safe to run again at any time: it skips what's already done and updates the workshop files.

When it finishes, open the workshop in Bob: **File → Open Folder…**, then choose `ai-agents-workshop` in your home folder.

### Connecting to IBM Cloud

At the end, the installer asks you to **paste your API key**. Paste it and press Enter; it won't show on screen as you paste. Everything else, including finding the workshop's watsonx Orchestrate instance, happens automatically.

You should see:

```text
✓ API key works: <your workshop username> (account <account id>)
✓ Found your watsonx Orchestrate instance: <instance name>
✓ Saved WXO_API_KEY and WXO_INSTANCE_URL to …/ai-agents-workshop/.env
✓ Your agent and tools will be named with the prefix 'student0_'
✓ Orchestrate instance is reachable with this key
✓ Orchestrate CLI environment 'workshop' is active
```

??? tip "Running the IBM Cloud step on its own"
    To change your API key later, without reinstalling:

    ```bash
    cd ~/ai-agents-workshop
    uv run python scripts/ibm_cloud_login.py
    ```

    It asks you to paste a key again; use a new one if your old one has expired.

??? tip "Open a new terminal afterwards"
    The installer adds `uv` and `orchestrate` to your shell's PATH for **new** terminals. In the terminal you ran it from, run `source $HOME/.local/bin/env` once.

??? tip "Using the `ibmcloud` CLI too?"
    You don't need the IBM Cloud CLI for the labs. If you want it, log in with the same API key:

    ```bash
    ibmcloud login --apikey <your API key>
    ```

    Plain `ibmcloud login` with your workshop username and password won't work, because workshop seats sign in through the instructor's login link, not with an IBMid.

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
    cd ~/ai-agents-workshop
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

---

## 5. Start the EHR Inbox

The workshop uses a simulated Electronic Health Record (EHR) inbox — a patient portal for **Lakeview Family Medicine**. Start it from the workshop folder:

```bash
cd ~/ai-agents-workshop
uv run streamlit run app/ui.py --server.port 8501
```

The EHR API server starts automatically in the background on port 8000.

Open [http://localhost:8501](http://localhost:8501) in your browser. You should see the inbox with 12 patients and their portal messages.

!!! info "Your patients live in the shared workshop EHR"
    The patient records come from one EHR server shared by the whole workshop. You get your **own private copy** of the 12 patients, keyed to your API key (step 3 saved the link in `.env`). Replies you send are visible only to you and to your agent. Pages load in about a second, because each one fetches from the cloud.

    If you create a new API key and re-run the setup script, you start over with a fresh copy of the patients.

Until you start a lab's agent, the **Concerns** panel tells you your agent isn't running yet and disables **Run Agent**. That's expected: each lab starts its agent in a second terminal.

??? tip "Changing ports"
    The API and UI ports are configurable:

    ```bash
    # Use a different API port
    API_PORT=9000 uv run streamlit run app/ui.py --server.port 9501
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
