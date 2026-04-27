#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Load config ---
# 1. Source defaults from agent.conf (ships with this repo)
DEFAULTS_FILE="$SCRIPT_DIR/agent.conf"
if [ -f "$DEFAULTS_FILE" ]; then
  source "$DEFAULTS_FILE"
fi

# 2. Source user/agent overrides (--config flag or AI_GH_CONFIG env var)
CONFIG_FILE="${AI_GH_CONFIG:-}"

# Parse --config before other flags (so config values are available for defaults)
args=("$@")
for ((i=0; i<${#args[@]}; i++)); do
  if [[ "${args[$i]}" == --config=* ]]; then
    CONFIG_FILE="${args[$i]#--config=}"
  elif [[ "${args[$i]}" == --config ]] && ((i+1 < ${#args[@]})); then
    CONFIG_FILE="${args[$((i+1))]}"
  fi
done

if [ -n "$CONFIG_FILE" ]; then
  if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
  fi
  source "$CONFIG_FILE"
fi

# --- Git identity for agent ---
# If a gitconfig include is configured, export GIT_CONFIG_* env vars so the
# agent subprocess uses the correct signing key, name, and email — regardless
# of which shell (bash/fish/zsh) launched ai-gh.sh.
if [ -n "${AGENT_GIT_CONFIG_INCLUDE:-}" ]; then
  export GIT_CONFIG_COUNT=1
  export GIT_CONFIG_KEY_0="include.path"
  export GIT_CONFIG_VALUE_0="$AGENT_GIT_CONFIG_INCLUDE"
fi

if [ -n "${AGENT_EXTRA_PATH:-}" ]; then
  export PATH="$AGENT_EXTRA_PATH:$PATH"
fi

# --- GitHub host ---
# Tell gh CLI which GitHub instance to talk to (needed for GHE).
if [ -n "${GITHUB_HOST:-}" ] && [ "$GITHUB_HOST" != "github.com" ]; then
  export GH_HOST="$GITHUB_HOST"
fi

# --- Git repo checks ---
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
  echo "Error: Not inside a git repository."
  exit 1
fi

REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null || true)
if [ -z "$REPO" ]; then
  echo "Error: Could not determine GitHub repo. Are you in a repo with a remote?"
  exit 1
fi

WORKTREE_DIR="$REPO_ROOT/$WORKTREE_DIR_NAME"
DEFAULT_BRANCH=$(gh repo view -R "$REPO" --json defaultBranchRef -q '.defaultBranchRef.name' 2>/dev/null || echo "main")
POLL=false
ISSUE=""
POLL_INTERVAL=60
CLEANUP=false
CLEANUP_ISSUE=""
STATUS=false

usage() {
  echo "Usage: ai-gh.sh [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --config F     Path to agent config file (default: agent.conf)"
  echo "  --issue N      Work on a specific issue number"
  echo "  --poll         Continuously poll for $LABEL_READY issues"
  echo "  --interval S   Poll interval in seconds (default: 60)"
  echo "  --status       Show active worktrees and their lock status"
  echo "  --cleanup      Remove all finished worktrees"
  echo "  --cleanup N    Remove worktree for a specific issue"
  echo "  -h, --help     Show this help"
  echo ""
  echo "Agent: $AGENT_NAME ($AGENT_CMD)"
  echo "Config: ${CONFIG_FILE:-$DEFAULTS_FILE}"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config=*) shift ;;  # Already handled above
    --config) shift 2 ;;
    --issue) ISSUE="$2"; shift 2 ;;
    --poll) POLL=true; shift ;;
    --interval) POLL_INTERVAL="$2"; shift 2 ;;
    --cleanup)
      CLEANUP=true
      if [[ "${2:-}" =~ ^[0-9]+$ ]]; then
        CLEANUP_ISSUE="$2"; shift
      fi
      shift ;;
    --status) STATUS=true; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

# --- Helper: expand template strings ---
# Replaces {id} in a string with a value
expand_template() {
  local template="$1" value="$2"
  echo "${template//\{id\}/$value}"
}

# Generate a deterministic UUID v5 from a string key.
# Uses the DNS namespace as a base; the result is stable across runs.
generate_uuid5() {
  python3 -c "import uuid; print(uuid.uuid5(uuid.NAMESPACE_DNS, '$1'))"
}

# Check whether a Claude Code session file exists for a given directory + UUID.
# Claude stores sessions at ~/.claude/projects/<mangled-path>/<uuid>.jsonl
# where <mangled-path> replaces / with - and strips the leading -.
session_exists() {
  local dir="$1" session_uuid="$2"
  local mangled
  mangled=$(echo "$dir" | tr '/.' '--')
  local session_dir="$HOME/.claude/projects/$mangled"
  [ -f "$session_dir/${session_uuid}.jsonl" ]
}

# --- Worktree management ---

ensure_worktree() {
  local num="$1"
  local branch="$BRANCH_PREFIX/$AGENT_NAME/issue-$num"
  local wt_path="$WORKTREE_DIR/$AGENT_NAME-issue-$num"

  if [ -d "$wt_path" ]; then
    echo "Worktree for issue #$num already exists at $wt_path"
    return 0
  fi

  mkdir -p "$WORKTREE_DIR"

  # Create the branch if it doesn't exist yet
  if git show-ref --verify --quiet "refs/heads/$branch" 2>/dev/null; then
    echo "Branch $branch exists, creating worktree..."
    git worktree add "$wt_path" "$branch"
  else
    echo "Creating branch $branch and worktree (from $DEFAULT_BRANCH)..."
    git fetch origin "$DEFAULT_BRANCH" 2>/dev/null || true
    git worktree add -b "$branch" "$wt_path" "origin/$DEFAULT_BRANCH"
  fi

  # Sync agent config files into the worktree.
  # We can't symlink the whole .claude/ dir because Claude Code creates
  # settings.local.json there on first run, causing the dir to already exist.
  # Instead, copy committed config files individually (skip settings.local.json
  # which is per-worktree state).
  if [ -d "$REPO_ROOT/$AGENT_CONFIG_DIR" ]; then
    mkdir -p "$wt_path/$AGENT_CONFIG_DIR"
    for f in "$REPO_ROOT/$AGENT_CONFIG_DIR"/*; do
      [ -f "$f" ] || continue
      local_name=$(basename "$f")
      # settings.local.json is per-worktree — never overwrite it
      [ "$local_name" = "settings.local.json" ] && continue
      cp "$f" "$wt_path/$AGENT_CONFIG_DIR/$local_name"
    done
    echo "Synced $AGENT_CONFIG_DIR/ config into worktree."
  fi

  # Sync .mcp.json so the worktree has the same MCP server config as the repo root
  if [ -f "$REPO_ROOT/.mcp.json" ]; then
    cp "$REPO_ROOT/.mcp.json" "$wt_path/.mcp.json"
  fi

  # Always sync instructions file from repo root (may have been updated since worktree creation)
  if [ -f "$REPO_ROOT/$AGENT_INSTRUCTIONS_FILE" ]; then
    cp "$REPO_ROOT/$AGENT_INSTRUCTIONS_FILE" "$wt_path/$AGENT_INSTRUCTIONS_FILE"
  fi

  echo "Worktree ready: $wt_path"
}

cleanup_worktree() {
  local wt="$1"
  local num
  num=$(basename "$wt" | sed "s/${AGENT_NAME}-issue-//")
  local lockfile="$wt/.agent-lock"

  # Skip if actively locked
  if [ -f "$lockfile" ]; then
    local lock_pid
    lock_pid=$(cat "$lockfile")
    if kill -0 "$lock_pid" 2>/dev/null; then
      echo "  Skipping issue #$num (active, PID $lock_pid)"
      return 1
    fi
  fi

  echo "  Removing worktree for issue #$num..."
  git worktree remove "$wt" --force 2>/dev/null || true
}

cleanup_worktrees() {
  echo "Cleaning up worktrees..."
  if [ -d "$WORKTREE_DIR" ]; then
    for wt in "$WORKTREE_DIR"/$AGENT_NAME-issue-*; do
      [ -d "$wt" ] || continue
      cleanup_worktree "$wt"
    done
    rmdir "$WORKTREE_DIR" 2>/dev/null || true
  fi
  git worktree prune
  echo "Done."
}

if [ "$STATUS" = true ]; then
  echo "=== Worktree Status ($AGENT_NAME) ==="
  if [ -d "$WORKTREE_DIR" ]; then
    for wt in "$WORKTREE_DIR"/$AGENT_NAME-issue-*; do
      [ -d "$wt" ] || continue
      local_num=$(basename "$wt" | sed "s/${AGENT_NAME}-issue-//")
      local_lock="$wt/.agent-lock"
      if [ -f "$local_lock" ]; then
        local_pid=$(cat "$local_lock")
        if kill -0 "$local_pid" 2>/dev/null; then
          echo "  #$local_num  ACTIVE (PID $local_pid)  $wt"
        else
          echo "  #$local_num  STALE  (PID $local_pid exited)  $wt"
        fi
      else
        echo "  #$local_num  IDLE   $wt"
      fi
    done
  else
    echo "  No worktrees."
  fi
  exit 0
fi

if [ "$CLEANUP" = true ]; then
  if [ -n "$CLEANUP_ISSUE" ]; then
    local_wt="$WORKTREE_DIR/$AGENT_NAME-issue-$CLEANUP_ISSUE"
    if [ -d "$local_wt" ]; then
      cleanup_worktree "$local_wt"
      git worktree prune
    else
      echo "No worktree found for issue #$CLEANUP_ISSUE."
    fi
  else
    cleanup_worktrees
  fi
  exit 0
fi

work_on_issue() {
  local num="$1"
  echo "=== Working on issue #$num ($AGENT_NAME) ==="

  # Set up isolated worktree for this issue
  ensure_worktree "$num"
  local wt_path="$WORKTREE_DIR/$AGENT_NAME-issue-$num"
  local lockfile="$wt_path/.agent-lock"

  # Prevent two agents from working the same issue
  if [ -f "$lockfile" ]; then
    local lock_pid
    lock_pid=$(cat "$lockfile")
    if kill -0 "$lock_pid" 2>/dev/null; then
      echo "Error: Issue #$num is already being worked on (PID $lock_pid)."
      return 1
    else
      echo "Stale lock found (PID $lock_pid no longer running). Removing."
      rm -f "$lockfile"
    fi
  fi
  echo $$ > "$lockfile"

  # Clean up lock when this function exits (not on global EXIT, which would
  # only clean up the last issue's lock in poll mode)
  cleanup_lock() {
    rm -f "$lockfile"
  }

  # Launch agent inside the worktree
  echo "Starting $AGENT_NAME in worktree: $wt_path"
  local branch="$BRANCH_PREFIX/$AGENT_NAME/issue-$num"

  # Derive session UUID from worktree path (stable — doesn't depend on
  # `gh repo view` which can vary with GH_HOST, auth, forks, or renames).
  local session_uuid
  session_uuid=$(generate_uuid5 "$wt_path")
  # Legacy key for backwards compat with sessions created before this change.
  local legacy_uuid
  legacy_uuid=$(generate_uuid5 "${REPO}#${num}")
  local prompt="You are working in a git worktree on branch $branch. Check GitHub issue #$num on $REPO for current state — read all comments — then follow the GitHub Issues Workflow Protocol in $AGENT_INSTRUCTIONS_FILE."

  echo "Session: $session_uuid (${wt_path})"

  # Run in a subshell with a trap so the lock is cleaned up on any exit
  # (normal return, Ctrl+C, or kill)
  (
    # Set iTerm background color and restore on exit
    if [ -n "${ITERM_BG_COLOR:-}" ]; then
      printf '\033]1337;SetColors=bg=%s\007' "$ITERM_BG_COLOR"
      restore_color() {
        printf '\033]1337;SetColors=bg=%s\007' "${ITERM_RESET_COLOR:-1a1a2e}"
      }
      trap 'cleanup_lock; restore_color' EXIT INT TERM
    else
      trap cleanup_lock EXIT INT TERM
    fi
    cd "$wt_path"

    # Check whether a session file exists on disk.  Try the current key
    # first, then the legacy key (repo#issue) for backwards compat.
    local session_flag=""
    if [ -n "$AGENT_RESUME_FLAG" ]; then
      if session_exists "$wt_path" "$session_uuid"; then
        echo "Resuming existing session."
        session_flag=$(expand_template "$AGENT_RESUME_FLAG" "$session_uuid")
      elif [ "$legacy_uuid" != "$session_uuid" ] && session_exists "$wt_path" "$legacy_uuid"; then
        echo "Resuming existing session (legacy key)."
        session_flag=$(expand_template "$AGENT_RESUME_FLAG" "$legacy_uuid")
      else
        echo "No existing session — starting new."
        if [ -n "${AGENT_NEW_SESSION_FLAG:-}" ]; then
          session_flag=$(expand_template "$AGENT_NEW_SESSION_FLAG" "$session_uuid")
        fi
      fi
    fi

    # Build permission mode flag if configured
    local permission_flag=""
    if [ -n "${AGENT_PERMISSION_MODE:-}" ]; then
      permission_flag="--permission-mode $AGENT_PERMISSION_MODE"
    fi

    # shellcheck disable=SC2086
    $AGENT_CMD $permission_flag $session_flag \
      $AGENT_PROMPT_FLAG "$prompt"
  )
  return $?
}

if [ -n "$ISSUE" ]; then
  work_on_issue "$ISSUE"
  exit 0
fi

find_next_issue() {
  # Exclude issues that already have a worktree or are in a later workflow stage
  local candidates
  candidates=$(gh issue list -R "$REPO" -l "$LABEL_READY" --json number,labels -q '.[].number' 2>/dev/null || true)
  for num in $candidates; do
    # Skip if a worktree already exists for this issue
    [ -d "$WORKTREE_DIR/$AGENT_NAME-issue-$num" ] && continue

    # Belt-and-suspenders: skip issues that also carry a later-stage label
    local labels
    labels=$(gh issue view "$num" -R "$REPO" --json labels -q '[.labels[].name] | join(",")' 2>/dev/null || true)
    case ",$labels," in
      *",$LABEL_WORKING,"*|*",$LABEL_AWAITING,"*|*",$LABEL_DONE,"*)
        continue ;;
    esac

    echo "$num"
    return
  done
}

if [ "$POLL" = true ]; then
  echo "Polling $REPO for $LABEL_READY issues every ${POLL_INTERVAL}s ($AGENT_NAME)..."
  echo "Press Ctrl+C to stop."
  echo ""
  while true; do
    NEXT=$(find_next_issue)
    if [ -n "$NEXT" ]; then
      work_on_issue "$NEXT"
    else
      echo "$(date '+%H:%M:%S') No $LABEL_READY issues found."
    fi
    sleep "$POLL_INTERVAL"
  done
else
  NEXT=$(find_next_issue)
  if [ -n "$NEXT" ]; then
    work_on_issue "$NEXT"
  else
    echo "No issues labeled '$LABEL_READY' found on $REPO."
    echo ""
    echo "To queue an issue:  gh issue edit <NUMBER> --add-label $LABEL_READY"
    echo "To work directly:   ./ai-gh.sh --issue <NUMBER>"
    echo "To poll:            ./ai-gh.sh --poll"
  fi
fi
