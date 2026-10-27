"""End-to-end check: two simulated students sharing the workshop EHR at once, no seat keys needed.

Instructor/testing only. NOT part of the default `pytest tests` run (the file name
doesn't start with test_, and it talks to real cloud services).

What it does
------------
setup    Clone the branch twice (student A and B), `uv sync` each, and run
         scripts/ibm_cloud_login.py in each with the --dev-* flags, so one IBM
         Cloud key acts as two students with distinct EHR tenants and name
         prefixes. A gets the full student path (orchestrate CLI env "workshop"
         in an isolated HOME) and deploys its Lab 1 agent with prefix devA_;
         B is EHR-only (--dev-skip-cli, no deploy).
run      Start each student's local EHR API (remote mode, own .env, own port)
         and A's Lab 1 agent API, then:
           1. both students post replies at the same time through their own
              local EHR APIs;
           2. each sees only its own replies (local API and the shared EHR);
           3. A's Orchestrate agent runs on a patient both replied to: its tool
              output contains A's reply and not B's, concerns land in A's
              checkout only, and B's tenant data and B's concern store are
              untouched.
         Servers are stopped at the end, pass or fail.
cleanup  Remove the devA_ agent, tools and connection from the Orchestrate instance.
all      setup, run, cleanup.

How to rerun
------------
Needs an IBM Cloud API key (JSON file with an "apikey" field) for a user with
access to an Orchestrate instance that can run the workshop model, and the
`orchestrate` CLI on PATH. From the repo root:

    uv run python tests/e2e/two_students.py all \\
        --key-file /path/to/apikey.json \\
        --instance https://api.<region>.watson-orchestrate.cloud.ibm.com/instances/<guid> \\
        --workdir /some/scratch/dir

`--workdir` gets studentA/, studentB/ and devA-home/ (A's isolated HOME holding
its orchestrate CLI config). Re-running `setup` on an existing workdir reuses
the checkouts. Tenants default to e2e-devA / e2e-devB so reruns don't add
tenants to the shared EHR (it holds at most MAX_TENANTS in memory); each run
replies to messages that are still unanswered, so after ~6 runs pass new
--tenant-a/--tenant-b values. The API key is read by the login script from the
file and never printed.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EHR = "https://workshop-ehr.2g7six4hbjvx.us-south.codeengine.appdomain.cloud"
BRANCH = "txc-2026-ibm"
PORTS = {"A": {"ehr": 8101, "agent": 8111}, "B": {"ehr": 8102, "agent": 8112}}
# Inherited values would beat each checkout's .env (load_dotenv doesn't override).
SCRUB = ("EHR_", "WXO_", "AGENT_", "API_URL", "API_PORT", "COS_", "SHARED_EHR_URL", "VIRTUAL_ENV")
AGENT_PREFIX = "devA_"
TOOLS = ["list_patients", "get_patient_record", "get_messages", "search_labs", "get_inbox"]

failures: list[str] = []


def check(ok: bool, what: str, evidence: str = ""):
    print(f"  {'PASS' if ok else 'FAIL'}  {what}" + (f"  [{evidence}]" if evidence else ""))
    if not ok:
        failures.append(what)


def student_env(home: Path | None = None) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(SCRUB)}
    env["PATH"] = f"{Path.home() / '.local' / 'bin'}:{env.get('PATH', '')}"
    if home is not None:
        env["HOME"] = str(home)
    return env


def run(cmd: list[str], cwd: Path, env: dict | None = None, timeout: int = 900) -> str:
    print(f"$ {' '.join(cmd)}   (in {cwd.name})")
    res = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        sys.exit(f"command failed ({res.returncode}):\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}")
    return res.stdout


def dotenv(checkout: Path) -> dict:
    out = {}
    for line in (checkout / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# --- setup ---------------------------------------------------------------------


def setup(a):
    wd = Path(a.workdir)
    wd.mkdir(parents=True, exist_ok=True)
    home_a = wd / "devA-home"
    home_a.mkdir(exist_ok=True)
    for name, prefix, tenant in (("A", AGENT_PREFIX, a.tenant_a), ("B", "devB_", a.tenant_b)):
        co = wd / f"student{name}"
        if not co.exists():
            run(["git", "clone", "-q", "--branch", BRANCH, "--single-branch", a.source, str(co)], wd)
        run(["uv", "sync", "-q"], co)
        login = [str(co / ".venv/bin/python"), "scripts/ibm_cloud_login.py", a.key_file, "--instance", a.instance,
                 "--dev-prefix", prefix, "--dev-tenant", tenant]
        if name == "B":
            login.append("--dev-skip-cli")
        print(run(login, co, student_env(home_a if name == "A" else None)))
    # Only A deploys an agent; B stays EHR-only.
    co_a = wd / "studentA"
    run([str(co_a / ".venv/bin/python"), "-m", "lab1.agent.deploy"], co_a, student_env(home_a))
    print("Deployed devA_ agent. New tools can take a few minutes before they answer.")


# --- run -----------------------------------------------------------------------


def start(cmd: list[str], cwd: Path, env: dict, log: Path) -> subprocess.Popen:
    return subprocess.Popen(cmd, cwd=cwd, env=env, stdout=log.open("w"), stderr=subprocess.STDOUT)


def wait_up(url: str, timeout: float = 60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=3).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    sys.exit(f"{url} didn't come up")


def records_text(ehr: str, tenant: str) -> str:
    resp = requests.get(f"{ehr}/records", headers={"X-Tenant": tenant}, timeout=60)
    resp.raise_for_status()
    return json.dumps(resp.json(), sort_keys=True)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def file_sha(p: Path) -> str:
    return sha(p.read_text()) if p.exists() else "absent"


TRACE_SNIPPET = r"""
import json, sys
from lab1.agent import agent
seen = []
orig = agent._log_tool_calls
def capture(reply):
    seen.append(reply)
    orig(reply)
agent._log_tool_calls = capture
text, _ = agent._client.run("Call get_messages for patient %s and list each message id. One line, no analysis.")
outs = [d.get("content", "") for r in seen for s in (r.get("step_history") or [])
        for d in s.get("step_details", []) if d.get("type") == "tool_response"]
print(json.dumps({"answer": text, "tool_outputs": outs}))
"""


def run_phase(a):
    wd = Path(a.workdir)
    co = {s: wd / f"student{s}" for s in "AB"}
    env_a, env_b = dotenv(co["A"]), dotenv(co["B"])
    tenant = {"A": env_a["EHR_TENANT"], "B": env_b["EHR_TENANT"]}
    ehr = env_a["EHR_API_URL"].rstrip("/")
    print(f"\nTenants: A={tenant['A']} B={tenant['B']}  shared EHR={ehr}")
    check(tenant["A"] != tenant["B"], "students have distinct EHR tenants")
    check(env_a["WXO_NAME_PREFIX"] == AGENT_PREFIX and env_b["WXO_NAME_PREFIX"] == "devB_", "dev prefixes written")

    procs, logs = [], wd / "logs"
    logs.mkdir(exist_ok=True)
    try:
        for s in "AB":
            env = student_env()
            env["AGENT_API_URL"] = f"http://127.0.0.1:{PORTS[s]['agent']}"
            procs.append(start([str(co[s] / ".venv/bin/python"), "-m", "uvicorn", "app.api:app",
                                "--port", str(PORTS[s]["ehr"])], co[s], env, logs / f"ehr{s}.log"))
        procs.append(start([str(co["A"] / ".venv/bin/python"), "-m", "uvicorn", "lab1.agent.api:app",
                            "--port", str(PORTS["A"]["agent"])], co["A"], student_env(), logs / "agentA.log"))
        local = {s: f"http://127.0.0.1:{PORTS[s]['ehr']}" for s in "AB"}
        for url in (*local.values(), f"http://127.0.0.1:{PORTS['A']['agent']}/status"):
            wait_up(url if url.endswith("/status") else f"{url}/health")
        for s in "AB":
            mode = requests.get(f"{local[s]}/health", timeout=5).json()["mode"]
            check(mode == "remote", f"student {s}'s local EHR API is in remote mode", mode)

        # Pick a patient with >= 2 unanswered messages for both, plus one other message each.
        inbox = {s: requests.get(f"{local[s]}/inbox", timeout=60).json() for s in "AB"}
        open_ids = {s: {(m["patient_id"], m["message_id"]) for m in inbox[s]} for s in "AB"}
        both = sorted(open_ids["A"] & open_ids["B"])
        by_patient: dict[str, list[str]] = {}
        for pid, mid in both:
            by_patient.setdefault(pid, []).append(mid)
        target = max(by_patient, key=lambda p: len(by_patient[p]))
        if len(by_patient[target]) < 2 or len(both) < 4:
            sys.exit("Not enough unanswered messages left in these tenants; pass new --tenant-a/--tenant-b.")
        others = [m for m in both if m[0] != target]
        plan = {"A": [(target, by_patient[target][0]), others[0]],
                "B": [(target, by_patient[target][1]), others[-1]]}
        run_id = uuid.uuid4().hex[:8]
        marker = {s: f"E2E-{s}-{run_id}" for s in "AB"}
        print(f"Target patient {target}; replies: {plan}")

        store = {s: co[s] / "data" / "agent_output.json" for s in "AB"}
        b_store_before = file_sha(store["B"])

        # 1. Both students reply at the same time, each through their own local EHR API.
        def reply(s, pid, mid):
            r = requests.post(f"{local[s]}/patients/{pid}/messages/{mid}/reply",
                              json={"body": f"{marker[s]} reply to {mid}"}, timeout=60)
            return s, mid, r.status_code
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            jobs = [pool.submit(reply, s, pid, mid) for s in "AB" for pid, mid in plan[s]]
            results = [j.result() for j in jobs]
        check(all(code == 200 for *_, code in results), "concurrent replies accepted", str(results))

        # 2. Each sees only its own progress.
        after = {s: {(m["patient_id"], m["message_id"]) for m in requests.get(f"{local[s]}/inbox", timeout=60).json()}
                 for s in "AB"}
        recs = {s: records_text(ehr, tenant[s]) for s in "AB"}
        for s, o in (("A", "B"), ("B", "A")):
            mine, theirs = set(plan[s]), set(plan[o])
            check(not (mine & after[s]), f"{s}'s inbox no longer lists the messages {s} answered")
            check(theirs <= after[s], f"{s}'s inbox still lists the messages only {o} answered")
            check(marker[s] in recs[s] and marker[o] not in recs[s],
                  f"shared EHR tenant {s} has {s}'s replies and none of {o}'s")
        msgs = {s: json.dumps(requests.get(f"{local[s]}/patients/{target}/messages", timeout=60).json()) for s in "AB"}
        check(marker["A"] in msgs["A"] and marker["B"] not in msgs["A"], f"A's local API shows only A's reply on {target}")
        check(marker["B"] in msgs["B"] and marker["A"] not in msgs["B"], f"B's local API shows only B's reply on {target}")

        # 3. A's Orchestrate agent moves only A's data.
        b_recs_before = sha(recs["B"])
        a_store_before = file_sha(store["A"])
        last = requests.get(f"{local['A']}/agent/status", timeout=10).json().get("last_run")
        r = requests.post(f"{local['A']}/patients/{target}/run", timeout=30)
        check(r.ok and r.json().get("status") == "started", "agent run started via A's local EHR API", r.text[:100])
        deadline = time.time() + 600
        while time.time() < deadline:
            st = requests.get(f"{local['A']}/agent/status", timeout=10).json()
            if not st.get("running") and st.get("last_run") != last or st.get("error"):
                break
            time.sleep(5)
        check(not st.get("error") and st.get("last_run") != last, "A's agent run finished without error",
              str(st.get("error"))[:300])
        concerns = requests.get(f"{local['A']}/patients/{target}/concerns", timeout=10).json()
        check(len(concerns) > 0, f"A's concerns for {target} served by A's local API", f"{len(concerns)} concerns")
        saved = json.loads(store["A"].read_text()) if store["A"].exists() else {}
        check(target in saved.get("patients", {}) and file_sha(store["A"]) != a_store_before,
              f"concerns stored in A's checkout ({store['A'].relative_to(wd)})")
        a_mid = plan["A"][0][1]
        flagged = [c["title"] for c in concerns if a_mid in json.dumps(c.get("related", {}))]
        print(f"  info  concerns linked to A's answered message {a_mid}: {flagged or 'none'}")

        trace = subprocess.run([str(co["A"] / ".venv/bin/python"), "-c", TRACE_SNIPPET % target], cwd=co["A"],
                               env=student_env(), capture_output=True, text=True, timeout=600)
        out = json.loads(trace.stdout.strip().splitlines()[-1]) if trace.returncode == 0 else {"tool_outputs": []}
        tool_text = "\n".join(out["tool_outputs"])
        check(trace.returncode == 0 and tool_text, "A's agent called get_messages on Orchestrate", trace.stderr[-300:])
        check(marker["A"] in tool_text, "A's agent tools read A's tenant (A's reply in tool output)")
        check(marker["B"] not in tool_text, "A's agent tools don't see B's reply")

        check(sha(records_text(ehr, tenant["B"])) == b_recs_before, "B's tenant records unchanged by A's agent")
        check(file_sha(store["B"]) == b_store_before, "B's local concern store untouched", file_sha(store["B"]))
        b_concerns = requests.get(f"{local['B']}/patients/{target}/concerns", timeout=10).json()
        check(b_concerns == [], "B's local API serves no concerns (B runs no agent)")
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()
        print(f"Stopped {len(procs)} local servers (logs in {logs})")


# --- cleanup -------------------------------------------------------------------


def cleanup(a):
    wd = Path(a.workdir)
    env = student_env(wd / "devA-home")
    co = wd / "studentA"
    orch = shutil.which("orchestrate", path=env["PATH"]) or "orchestrate"
    steps = [["agents", "remove", "-n", f"{AGENT_PREFIX}lakeview_inbox_agent", "-k", "native"]]
    steps += [["tools", "remove", "-n", f"{AGENT_PREFIX}{t}"] for t in TOOLS]
    steps += [["connections", "remove", "-a", f"{AGENT_PREFIX}lakeview_ehr"]]
    for step in steps:
        res = subprocess.run([orch, *step], cwd=co, env=env, capture_output=True, text=True, timeout=120)
        print(f"$ orchestrate {' '.join(step)} -> {res.returncode}")
    listing = subprocess.run([orch, "tools", "list"], cwd=co, env=env, capture_output=True, text=True, timeout=120)
    agents = subprocess.run([orch, "agents", "list"], cwd=co, env=env, capture_output=True, text=True, timeout=120)
    check(AGENT_PREFIX not in listing.stdout + agents.stdout, "no devA_ tools or agents left on the instance")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("phase", choices=["setup", "run", "cleanup", "all"])
    p.add_argument("--workdir", required=True, help="scratch dir for the two checkouts")
    p.add_argument("--key-file", help="JSON file with an IBM Cloud 'apikey' (setup)")
    p.add_argument("--instance", help="Orchestrate instance URL or CRN (setup)")
    p.add_argument("--source", default=str(REPO_ROOT), help="repo to clone (default: this checkout's committed HEAD)")
    p.add_argument("--tenant-a", default="e2e-devA")
    p.add_argument("--tenant-b", default="e2e-devB")
    a = p.parse_args()
    if a.phase in ("setup", "all") and not (a.key_file and a.instance):
        p.error("setup needs --key-file and --instance")
    if a.phase in ("setup", "all"):
        setup(a)
    if a.phase in ("run", "all"):
        run_phase(a)
    if a.phase in ("cleanup", "all"):
        cleanup(a)
    print(f"\n{'ALL CHECKS PASSED' if not failures else f'{len(failures)} FAILED: {failures}'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
