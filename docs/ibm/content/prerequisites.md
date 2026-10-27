# Prerequisites

Complete these steps **before the workshop** to make sure your environment is ready.

## 1. IBM Cloud: log in

The workshop runs on IBM Cloud. Your agent is deployed to **watsonx Orchestrate**. Your code talks to IBM Cloud with an **API key**: a long secret string that acts on your behalf. You'll create it in step 3, right before the installer asks for it.

### Log in to IBM Cloud

You log in to IBM Cloud with a **workshop seat login**, not your own IBMid (that one is for Bob). Follow **[IBM Cloud login](ibm-cloud-login.md)**: it has the seat logins, the access link ([ibm.biz/txc26-4217](https://ibm.biz/txc26-4217)), and the steps to get your API key.

---

## 2. Set up IBM Bob

<div class="admonition tip" id="bob-access" hidden markdown>
<p class="admonition-title">Today's workshop links</p>
<p>Workshop guide: <a href="https://ibm.biz/txc-26-ai-agents-workshop">ibm.biz/txc-26-ai-agents-workshop</a></p>
<p>IBM Bob not working? Get access here: <a id="bob-access-url" href="#" target="_blank" rel="noopener"></a><br>
Access code: <code id="bob-access-code"></code></p>
</div>
<script>
  // Day-of details come from the workshop backend, not from this page, and stop being served after the workshop.
  fetch("https://workshop-ehr.2g7six4hbjvx.us-south.codeengine.appdomain.cloud/workshop/bob-access", { cache: "no-store" })
    .then(r => (r.ok ? r.json() : null))
    .then(info => {
      if (!info || !info.url || !info.code) return;
      const link = document.getElementById("bob-access-url");
      link.href = info.url;
      link.textContent = info.url;
      document.getElementById("bob-access-code").textContent = info.code;
      document.getElementById("bob-access").hidden = false;
    })
    .catch(() => {});
</script>

You'll work in **IBM Bob**, IBM's AI-powered IDE, and run every command in Bob's built-in terminal. On Windows, Bob connects to a Linux environment (WSL), so everyone runs the same commands.

=== "macOS"

    1. Download and install [IBM Bob](https://bob.ibm.com/?lnk=hpfp2us), open it, and log in to your Bob account.
    2. Open a terminal inside Bob: **Terminal → New Terminal** (or <kbd>Ctrl</kbd>+<kbd>`</kbd>).

    Use this terminal for **3. Install the workshop** below and every command in the labs.

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
    5. In the new window, open a terminal: **Terminal → New Terminal**. It runs inside Fedora. Use it for **3. Install the workshop** below and every command in the labs.

    ??? tip "On a VPN or behind a corporate proxy?"
        If downloads fail inside Fedora but work in Windows, see Microsoft's [WSL networking troubleshooting](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting).

=== "Linux"

    1. Download and install [IBM Bob](https://bob.ibm.com/?lnk=hpfp2us), open it, and log in to your Bob account.
    2. Open a terminal inside Bob: **Terminal → New Terminal** (or <kbd>Ctrl</kbd>+<kbd>`</kbd>).

    The installer uses your package manager (`dnf`, `apt` or `zypper`) with `sudo` for anything missing, so it may ask for your password.

---

## 3. Install the workshop

### Create your API key

Create your API key in the IBM Cloud tab you logged in with, following **[IBM Cloud login → Create your API key](ibm-cloud-login.md#3-create-your-api-key)**. Keep that tab open until the installer accepts the key.

### Run the installer

In Bob's terminal from step 2 (on Windows, the Bob window connected to WSL), run:

```bash
curl -LsSf https://raw.githubusercontent.com/obuzek/ai-agents-workshop/txc-2026-ibm/scripts/install.sh | bash
```

You don't need Homebrew or a preinstalled Python. The installer:

1. Installs `git`, `tar` and `gzip` if they're missing (on Fedora that's usually just `git`), using your package manager with `sudo`, which may ask for your Linux password.
2. Installs [uv](https://docs.astral.sh/uv/), which also downloads Python 3.12 for the workshop.
3. Downloads the workshop into `~/ai-agents-workshop`.
4. Installs the workshop's Python packages.
5. Installs the watsonx Orchestrate command-line tool, `orchestrate`, with `uv tool install ibm-watsonx-orchestrate`. uv puts it in `~/.local/bin` and adds that folder to your PATH.
6. Asks for your API key and connects you to IBM Cloud.
7. Checks the setup.

It's safe to run again at any time: it skips what's already done and updates the workshop files.

### Paste your API key

When the installer reaches `[6/7] Connect to IBM Cloud`, paste the key you copied in the browser and press Enter. Nothing appears as you paste; that's on purpose. The script checks the key with IBM Cloud, finds the workshop's watsonx Orchestrate instance, saves your settings to `.env`, and connects the `orchestrate` CLI. Then it checks the whole setup.

You'll see:

```text
[6/7] Connect to IBM Cloud
Created .env from .env-example
Paste your IBM Cloud API key (it won't show as you paste), then press Enter:
✓ API key works: <your workshop username> (account <account id>)
✓ Found your watsonx Orchestrate instance: <instance name>
✓ Saved WXO_API_KEY and WXO_INSTANCE_URL to …/ai-agents-workshop/.env
✓ Your agent and tools will be named with the prefix 'student0_'
✓ Orchestrate instance is reachable with this key
✓ Orchestrate CLI environment 'workshop' is active (deploy with: uv run python -m lab1.agent.deploy)

[7/7] Check the setup
✓ Python environment: Python 3.12.13, workshop packages installed
✓ Orchestrate CLI: ADK 2.19.1
✓ .env settings: WXO_API_KEY, WXO_INSTANCE_URL, WXO_NAME_PREFIX, EHR_TENANT, EHR_API_URL are set
✓ IBM Cloud API key: IBM Cloud accepts it
✓ Orchestrate instance: reachable with your key
✓ Orchestrate CLI environment: 'workshop' is active
✓ Shared workshop EHR: your copy has 12 patients

All checks passed.
```

Your prefix, Python and ADK versions may differ.

If you see `IBM Cloud rejected that API key`, copy the key again from the browser, or create a new one, and run the IBM Cloud step on its own:

```bash
cd ~/ai-agents-workshop
uv run python scripts/ibm_cloud_login.py
```

Use the same command later if your key expires.

When the installer finishes:

- Open a new terminal in Bob (**Terminal → New Terminal**) so `uv` and `orchestrate` are on your PATH. Or, in the terminal you ran the installer from, run `export PATH="$HOME/.local/bin:$PATH"`.
- Open the workshop in Bob: **File → Open Folder…**, then choose `ai-agents-workshop` in your home folder.

---

## 4. Start the EHR inbox

The workshop uses a simulated Electronic Health Record (EHR) inbox, a patient portal for **Lakeview Family Medicine**. Start it from the workshop folder:

```bash
cd ~/ai-agents-workshop
uv run streamlit run app/ui.py --server.port 8501
```

The EHR API server starts automatically in the background on port 8000. Open [http://localhost:8501](http://localhost:8501) in your browser (on Windows, your normal Windows browser). You'll see:

- A **patient dropdown** at the top (12 patients, some with unread messages)
- **Medical records** with tabs for Conditions, Medications, Labs, History
- A **Concerns** panel. It says your agent isn't running yet and **Run Agent** is disabled; each lab starts its agent in a second terminal.
- An **Inbox** with patient messages and a conversation viewer

Each page takes about a second to load, because it fetches from the cloud.

!!! info "Your patients live in the shared workshop EHR"
    The patient records come from one EHR server shared by the whole workshop. You get your own copy of the 12 patients, tied to your API key. Replies you send are visible only to you and your agent. If you create a new API key and run `scripts/ibm_cloud_login.py` again, you start over with a fresh copy.

??? tip "Port 8501, 8000 or 8001 already in use?"
    Pick other ports. Start the inbox with:

    ```bash
    API_PORT=8010 uv run streamlit run app/ui.py --server.port 8511
    ```

    and open http://localhost:8511. In Lab 1, start the agent service on another port too, and tell the inbox where it is:

    ```bash
    uv run uvicorn lab1.agent.api:app --port 8011
    API_PORT=8010 AGENT_API_URL=http://localhost:8011 uv run streamlit run app/ui.py --server.port 8511
    ```

---

## 5. Verify it works

Leave the inbox running. In a second terminal, run the setup check:

```bash
cd ~/ai-agents-workshop
uv run python scripts/check_setup.py
```

It changes nothing. It prints the same list you saw at the end of the installer: one ✓ or ✗ per part of the setup, and for each ✗ a line starting with `Fix:` that says what to do.

You're ready when every line has a ✓ and you can browse patients and read their messages in the inbox.

## Next Steps

Proceed to [Lab 1: The Naive Agent](./lab-1.md) to start building.
