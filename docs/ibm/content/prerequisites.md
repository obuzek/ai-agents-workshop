# Prerequisites

Complete these steps **before the workshop** to make sure your environment is ready.

## 1. IBM Cloud: log in and create your API key

The workshop runs on IBM Cloud. Your agent is deployed to **watsonx Orchestrate**, and watsonx.governance evaluates it. Your code talks to IBM Cloud with an **API key**: a long secret string that acts on your behalf. You create it in the IBM Cloud web console, and the installer in step 3 saves it for you.

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

### Create an API key

1. In the **top menu bar**, open the **Manage** dropdown and choose **Access (IAM)**.
2. In the **IAM menu on the left**, find the **Manage identities** heading and click **API keys** underneath it.
3. Click **Create**.
4. Give the key a name, such as `ai-agents-workshop`, and click **Create**.
5. Click **Download**. This saves a file called `apikey.json` to your Downloads folder.

!!! warning "You only see the key once"
    IBM Cloud shows the key only when you create it. If you close the dialog without downloading it, delete that key and create a new one.

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

    On Windows, the workshop runs inside **WSL** (Windows Subsystem for Linux), using the **FedoraLinux-44** distribution. Bob connects to it, so your terminal and files are in Linux.

    !!! tip "On a TechXchange workshop machine?"
        WSL and FedoraLinux-44 are already installed. Skip **Install WSL with Fedora** and start at **Connect IBM Bob to WSL**.

    !!! info "What you need"
        Windows 11 (recommended), or Windows 10 version 2004 (build 19041) or later, with hardware virtualization turned on. On a managed work laptop, WSL may be blocked by policy; check with your IT team before the workshop.

    **Install WSL with Fedora** (once; needs administrator rights and a restart)

    1. Right-click **Windows Terminal** (or **PowerShell**) and choose **Run as administrator**, then run:

        ```powershell
        wsl --install -d FedoraLinux-44
        ```

        If you already use WSL, run `wsl --update` first.

    2. Restart Windows when asked.
    3. Open PowerShell again (administrator not needed) and check that Fedora is installed, with **VERSION 2**:

        ```powershell
        wsl -l -v
        ```

        If `FedoraLinux-44` isn't listed, run `wsl --install -d FedoraLinux-44` once more.

    4. Start Fedora once to create your Linux user, either from the Start menu (**FedoraLinux-44**) or with:

        ```powershell
        wsl -d FedoraLinux-44
        ```

        It asks you to **create a default Unix user account**: type a username (it doesn't need to match your Windows name). It doesn't ask for a password; your user can already run `sudo` without one. Type `exit` to close it.

    ??? warning "Error 0x80370102, or the install stuck at 0.0%"
        **0x80370102** means virtualization is off: turn it on in your BIOS/UEFI settings (usually under CPU), make sure the **Virtual Machine Platform** Windows feature is on, and restart.

        **Stuck at 0.0%?** Cancel and run `wsl --install --web-download -d FedoraLinux-44` instead.

    **Connect IBM Bob to WSL**

    5. Download and install the latest [IBM Bob](https://bob.ibm.com/?lnk=hpfp2us), open it, and log in to your Bob account. If you already have Bob, update it: older versions can't set up WSL.
    6. Open the **Extensions** view (the icon of four squares in the left bar), search for **Open Remote - WSL**, and install the one by **jeanp413**. (Don't use Microsoft's "WSL" extension; its licence only allows it in Microsoft's VS Code.)
    7. Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd>, type **WSL**, choose **Remote-WSL: Connect to WSL using Distro...**, and pick **FedoraLinux-44**. The first time, Bob takes a minute to set itself up inside Fedora. Use this window from now on.

        Picking the distro matters if you have another one, like Ubuntu, installed: plain **Remote-WSL: Connect to WSL** opens your *default* distro.

    8. In that window, open a terminal: **Terminal → New Terminal**. It runs inside Fedora. Use it for **3. Run the installer** below and every command in the labs.

    !!! tip "Your browser downloads still go to Windows"
        The API key you download in your Windows browser lands in your Windows **Downloads** folder. The installer looks there too, so you don't need to move it.

    ??? tip "On a VPN or behind a corporate proxy?"
        If downloads fail inside Fedora but work in Windows, see Microsoft's [WSL networking troubleshooting](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting). On Windows 11, *mirrored* networking often helps with VPNs.

=== "Linux"

    1. Download and install [IBM Bob](https://bob.ibm.com/?lnk=hpfp2us), open it, and log in to your Bob account.
    2. Open a terminal inside Bob: **Terminal → New Terminal** (or <kbd>Ctrl</kbd>+<kbd>`</kbd>).

    The installer uses your package manager (`dnf`, `apt` or `zypper`) with `sudo` for anything missing, so it may ask for your password.

---

## 3. Run the installer

In Bob's terminal from step 2 (on Windows, Bob connected to WSL), run:

```bash
curl -LsSf https://raw.githubusercontent.com/obuzek/ai-agents-workshop/txc-2026-ibm/scripts/install.sh | bash
```

You don't need Homebrew or a preinstalled Python. The installer:

1. Installs `git`, `curl`, `tar` and `gzip` if they're missing, using your package manager with `sudo`. (On Fedora WSL only `git` is missing, and `sudo` doesn't ask for a password. On other Linux systems it may.)
2. Installs [uv](https://docs.astral.sh/uv/), which also downloads Python 3.12 for the workshop.
3. Downloads the workshop into `~/ai-agents-workshop`.
4. Installs the workshop's Python packages.
5. Installs the watsonx Orchestrate command-line tool, `orchestrate`.
6. Connects you to IBM Cloud with your API key (see below).

It's safe to run again at any time: it skips what's already done and updates the workshop files.

When it finishes, open the workshop in Bob: **File → Open Folder…**, then choose `ai-agents-workshop` in your home folder.

### Connecting to IBM Cloud

At the end, the installer asks a few questions:

- **Your API key.** It finds the `apikey.json` you downloaded in step 1 and asks you to confirm. On Windows it also looks in your Windows Downloads folder. If it can't find the file, paste the key when asked; it won't appear on screen.
- **The watsonx Orchestrate instance.** In cloud.ibm.com, open the **Resource list**, expand **AI / Machine Learning**, click the workshop's **watsonx Orchestrate** instance, and copy its **CRN** (it starts with `crn:v1:`; there's a copy button next to it). Paste it at the prompt.

You should see:

```text
✓ API key works: <your workshop username> (account <account id>)
✓ Saved WXO_API_KEY and WXO_INSTANCE_URL to …/ai-agents-workshop/.env
✓ Your agent and tools will be named with the prefix 'student0_'
✓ Orchestrate instance is reachable with this key
✓ Orchestrate CLI environment 'workshop' is active
```

??? tip "Running the IBM Cloud step on its own"
    To change your key or instance later, without reinstalling:

    ```bash
    cd ~/ai-agents-workshop
    uv run python scripts/ibm_cloud_login.py
    ```

    Pass a path if your key file is somewhere unusual: `uv run python scripts/ibm_cloud_login.py path/to/apikey.json`.

??? tip "Open a new terminal afterwards"
    The installer adds `uv` and `orchestrate` to your shell's PATH for **new** terminals. In the terminal you ran it from, run `source $HOME/.local/bin/env` once.

??? tip "Using the `ibmcloud` CLI too?"
    You don't need the IBM Cloud CLI for the labs. If you want it, log in with the same key file:

    ```bash
    ibmcloud login --apikey @~/Downloads/apikey.json
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
