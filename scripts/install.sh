#!/usr/bin/env bash
# AI Agents Workshop (IBM TechXchange edition): one-line setup.
#
#   curl -LsSf https://raw.githubusercontent.com/obuzek/ai-agents-workshop/txc-2026-ibm/scripts/install.sh | bash
#
# Works on macOS, Linux, and Windows via WSL (run it inside your WSL Linux shell,
# e.g. FedoraLinux-44). Doesn't need Homebrew. Safe to re-run: every step checks
# what's already there.
#
# What it does:
#   1. Installs missing system tools (git, tar, gzip) with your package manager
#   2. Installs uv (Python package manager), which also provides Python
#   3. Clones the workshop (branch txc-2026-ibm) into ~/ai-agents-workshop, or updates it
#   4. Installs the workshop's Python dependencies
#   5. Installs the watsonx Orchestrate CLI (`orchestrate`)
#   6. Connects you to IBM Cloud: runs scripts/ibm_cloud_login.py with your API key
#   7. Checks the setup: runs scripts/check_setup.py (read-only)
#
# Settings (environment variables):
#   WORKSHOP_DIR     where to put the workshop   (default: ~/ai-agents-workshop)
#   WORKSHOP_BRANCH  which branch to use          (default: txc-2026-ibm)
#   SKIP_LOGIN=1     skip the IBM Cloud login step (and check only the local setup)
#   WXO_INSTANCE     the workshop's Orchestrate instance CRN or URL (found from your key otherwise)

# Everything lives in main(), called on the last line, so a download cut off
# halfway through runs nothing.
main() {
    set -euo pipefail

    local repo_url="https://github.com/obuzek/ai-agents-workshop.git"
    local branch="${WORKSHOP_BRANCH:-txc-2026-ibm}"
    local dir="${WORKSHOP_DIR:-$HOME/ai-agents-workshop}"
    local python_version="3.12"  # the Orchestrate CLI supports 3.11-3.14

    say "AI Agents Workshop setup"
    detect_platform

    step 1 "System tools"
    ensure_system_tools

    step 2 "uv and Python"
    ensure_uv
    uv python install "$python_version" >/dev/null 2>&1 || die "uv couldn't install Python $python_version."
    ok "uv $(uv --version | awk '{print $2}'), Python $python_version"

    step 3 "Workshop files"
    ensure_repo "$repo_url" "$branch" "$dir"

    step 4 "Python dependencies"
    (cd "$dir" && uv sync --python "$python_version" --quiet)
    ok "Installed into $dir/.venv"

    step 5 "watsonx Orchestrate CLI"
    if uv tool list 2>/dev/null | grep -q '^ibm-watsonx-orchestrate '; then
        uv tool upgrade ibm-watsonx-orchestrate --quiet || warn "Couldn't upgrade the Orchestrate CLI; keeping the installed version"
    else
        uv tool install --python "$python_version" ibm-watsonx-orchestrate --quiet
    fi
    uv tool update-shell >/dev/null 2>&1 || true  # puts ~/.local/bin on PATH in new shells
    # `orchestrate --version` prints the version but exits non-zero, so don't trust its status.
    local adk_version
    adk_version="$(orchestrate --version 2>/dev/null | grep -m1 '^ADK Version' || true)"
    command -v orchestrate >/dev/null 2>&1 || die "The Orchestrate CLI didn't install."
    ok "Orchestrate CLI installed${adk_version:+ ($adk_version)}"
    # Make sure new terminals find uv and orchestrate in ~/.local/bin, even when uv came from elsewhere.
    uv tool update-shell >/dev/null 2>&1 || true

    step 6 "Connect to IBM Cloud"
    local logged_in=0
    if [[ "${SKIP_LOGIN:-}" == "1" ]]; then
        warn "Skipped (SKIP_LOGIN=1). When you're ready: cd $dir && uv run python scripts/ibm_cloud_login.py"
    elif [[ -r /dev/tty ]]; then
        # This script arrives on stdin (curl | bash), so give the login script the
        # keyboard explicitly; it asks for your API key.
        local login_args=()
        [[ -n "${WXO_INSTANCE:-}" ]] && login_args=(--instance "$WXO_INSTANCE")
        if (cd "$dir" && uv run python scripts/ibm_cloud_login.py ${login_args[@]+"${login_args[@]}"} </dev/tty); then
            logged_in=1
        else
            warn "IBM Cloud setup didn't finish. Fix the issue above, then run: cd $dir && uv run python scripts/ibm_cloud_login.py"
        fi
    else
        warn "No terminal to ask questions in. Run: cd $dir && uv run python scripts/ibm_cloud_login.py"
    fi

    step 7 "Check the setup"
    local check=(uv run python scripts/check_setup.py)
    if [[ "${SKIP_LOGIN:-}" == "1" ]]; then
        check+=(--offline)  # no API key yet, so check only what's on this machine
    elif [[ "$logged_in" != "1" ]]; then
        check=()
        warn "Skipped until you're connected. Afterwards run: cd $dir && uv run python scripts/check_setup.py"
    fi
    if [[ ${#check[@]} -gt 0 ]] && ! (cd "$dir" && "${check[@]}"); then
        warn "Fix what's marked ✗ above, then check again: cd $dir && uv run python scripts/check_setup.py"
    fi

    say ""
    say "Done. Next:"
    say "  cd $dir"
    say "  uv run streamlit run app/ui.py --server.port 8501"
    say "Then open http://localhost:8501 in your browser."
    if [[ "$PLATFORM" == "wsl" ]]; then
        say "(On Windows, open that address in your normal Windows browser; WSL forwards it.)"
    fi
    say "Open a new terminal (or run: export PATH=\"\$HOME/.local/bin:\$PATH\") so 'uv' and 'orchestrate' are on your PATH."
}

say()  { printf '%s\n' "$*"; }
step() { printf '\n[%s/7] %s\n' "$1" "$2"; }
ok()   { printf '      ✓ %s\n' "$*"; }
warn() { printf '      ! %s\n' "$*" >&2; }
die()  { printf '\n✗ %s\n' "$*" >&2; exit 1; }

detect_platform() {
    case "$(uname -s)" in
        Darwin) PLATFORM="macos" ;;
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then PLATFORM="wsl"; else PLATFORM="linux"; fi ;;
        *) die "Unsupported system: $(uname -s). On Windows, run this inside WSL (see the prerequisites page)." ;;
    esac
    say "Platform: $PLATFORM"
}

# Run as root if we are root, otherwise through sudo (which may ask for your password).
as_root() {
    if [[ "$(id -u)" == "0" ]]; then "$@"; else sudo "$@"; fi
}

ensure_system_tools() {
    # curl is a given: it's how this script was downloaded.
    local needed=(git tar gzip) missing=() tool
    for tool in "${needed[@]}"; do
        command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
    done
    if [[ ${#missing[@]} -eq 0 ]]; then
        ok "git, tar, gzip already installed"
        return
    fi

    say "      Installing: ${missing[*]} (you may be asked for your password)"
    case "$PLATFORM" in
        macos)
            # git ships with Apple's Command Line Tools; tar and gzip are built in.
            xcode-select --install >/dev/null 2>&1 || true
            die "macOS is installing the Command Line Tools (for git) in a separate window. When that finishes, run this command again."
            ;;
        *)
            if command -v dnf >/dev/null 2>&1; then
                as_root dnf install -y "${missing[@]}"
            elif command -v apt-get >/dev/null 2>&1; then
                as_root apt-get update -y && as_root apt-get install -y "${missing[@]}"
            elif command -v zypper >/dev/null 2>&1; then
                as_root zypper --non-interactive install "${missing[@]}"
            else
                die "Please install ${missing[*]} with your system's package manager, then run this again."
            fi
            ;;
    esac
    for tool in "${missing[@]}"; do
        command -v "$tool" >/dev/null 2>&1 || die "$tool still isn't available after installing."
    done
    ok "Installed ${missing[*]}"
}

ensure_uv() {
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
        # shellcheck disable=SC1091
        [[ -f "$HOME/.local/bin/env" ]] && source "$HOME/.local/bin/env"
        command -v uv >/dev/null 2>&1 || die "uv didn't install. See https://docs.astral.sh/uv/getting-started/installation/"
    fi
}

ensure_repo() {
    local url="$1" branch="$2" dir="$3"
    if [[ -d "$dir/.git" ]]; then
        cd "$dir"
        git fetch --quiet origin "$branch"
        if [[ "$(git rev-parse --abbrev-ref HEAD)" != "$branch" ]]; then
            git checkout --quiet "$branch" 2>/dev/null || git checkout --quiet -b "$branch" "origin/$branch"
        fi
        if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
            warn "You have local changes in $dir; leaving them alone (not updating)."
        else
            git merge --quiet --ff-only "origin/$branch" || warn "Couldn't fast-forward $dir; leaving it as is."
        fi
        cd - >/dev/null
        ok "Up to date: $dir ($branch)"
    elif [[ -e "$dir" ]]; then
        die "$dir exists but isn't the workshop repo. Move it aside or set WORKSHOP_DIR, then run this again."
    else
        git clone --quiet --branch "$branch" --single-branch "$url" "$dir"
        ok "Cloned into $dir ($branch)"
    fi
}

main "$@"
