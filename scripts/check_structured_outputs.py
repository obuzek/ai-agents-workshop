"""
Live check: does the workshop model on watsonx Orchestrate produce the structured
output every phase of the workshop needs?

Phases and schemas checked (the labs' own prompts and Pydantic models):
  main agent   PatientConcerns   your deployed inbox agent (Labs 1-4), with tools
  extraction   ExtractedClaims   Lab 3/4 grounding: pull claims out of a concern
  judge        ClaimVerdicts     Lab 3/4 grounding: LLM-as-judge against the record
  critic       CriticResult      Lab 3/4 critic: approve or send back each concern

Orchestrate's react_core agents don't support constrained decoding, so every
step uses the workshop's approach: the JSON Schema goes in the instructions, the
reply is validated with Pydantic, and on failure the model gets the error and
one more try. This script reports how often the first reply is valid, how often
the retry rescues it, and what still fails.

The extraction, judge and critic steps run as small tool-less Orchestrate
agents (<prefix>claim_extractor, <prefix>grounding_judge, <prefix>critic),
which this script creates or updates through the Orchestrate API.

Prerequisites: run scripts/install.sh (or ibm_cloud_login.py) and deploy your
agent (uv run python -m lab1.agent.deploy).

Usage:
    uv run python scripts/check_structured_outputs.py                 # all 12 patients, 1 round
    uv run python scripts/check_structured_outputs.py --patients 4 --rounds 2
    uv run python scripts/check_structured_outputs.py --ibmcloud-session --instance <url> --main-agent <name>
"""

import argparse
import ast
import concurrent.futures as cf
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lab1.agent.models import PatientConcerns  # noqa: E402

PREFIX = os.environ.get("WXO_NAME_PREFIX", "")
INSTANCE = os.environ.get("WXO_INSTANCE_URL", "").rstrip("/")
API_KEY = os.environ.get("WXO_API_KEY", "")
EHR_URL = os.environ.get("EHR_API_URL", "").rstrip("/")
EHR_TENANT = os.environ.get("EHR_TENANT", "")
MODEL = os.environ.get("WXO_JUDGE_MODEL", "virtual-model/anthropic/claude-sonnet-5-5")  # same model as agent.yaml
MAIN_AGENT = os.environ.get("WXO_AGENT_NAME") or PREFIX + "lakeview_inbox_agent"


# --- Lab 3's grounding / critic schemas (same fields as lab3/agent/grounding.py, critic.py) ---


class ExtractedClaims(BaseModel):
    claims: list[str]


class ClaimVerdict(BaseModel):
    claim: str
    supported: bool
    reason: str


class ClaimVerdicts(BaseModel):
    verdicts: list[ClaimVerdict]


class ConcernFeedback(BaseModel):
    concern_title: str
    on_task: bool
    grounded: bool
    revision_needed: bool
    feedback: str


class CriticResult(BaseModel):
    concern_feedback: list[ConcernFeedback]
    approved: bool
    summary: str


def lab_prompt(path: str, name: str) -> str:
    """Read a prompt constant from a lab file without importing the lab (no LangChain/Langfuse needed)."""
    tree = ast.parse((ROOT / path).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(f"{name} not found in {path}")


def instructions_from(prompt: str, input_marker: str) -> str:
    """The prompt's guidance, minus its {placeholder} section, which arrives as the user message instead."""
    return prompt.split(input_marker)[0].strip()


def format_suffix(model: type[BaseModel]) -> str:
    """The same "answer with JSON matching this schema" instruction lab1/agent/deploy.py appends."""
    schema = model.model_json_schema()
    return (
        "\nFINAL ANSWER FORMAT:\n"
        "Reply with ONLY a JSON object (no prose, no markdown, no code fences) that "
        "validates against this JSON Schema:\n" + json.dumps(schema, separators=(",", ":")) + "\n"
    )


# --- Orchestrate client (IAM token + runs API) ---


class Orchestrate:
    def __init__(self, use_ibmcloud_session: bool = False):
        self._token, self._expires, self._ids = "", 0.0, {}
        self._session = use_ibmcloud_session

    def _headers(self):
        if self._session:
            # Your own user, via `ibmcloud login`; the CLI refreshes the token as needed.
            out = subprocess.run(["ibmcloud", "iam", "oauth-tokens", "--output", "json"],
                                 capture_output=True, text=True, check=True).stdout
            return {"Authorization": json.loads(out)["iam_token"]}
        if time.time() > self._expires - 60:
            r = requests.post("https://iam.cloud.ibm.com/identity/token",
                              data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": API_KEY}, timeout=30)
            r.raise_for_status()
            self._token, self._expires = r.json()["access_token"], r.json()["expiration"]
        return {"Authorization": f"Bearer {self._token}"}

    def agent_id(self, name: str) -> str:
        if name not in self._ids:
            agents = requests.get(f"{INSTANCE}/v1/orchestrate/agents", headers=self._headers(), timeout=30).json()
            matches = [a["id"] for a in agents if a["name"] == name]
            if not matches:
                sys.exit(f"Agent '{name}' isn't deployed on {INSTANCE}.")
            self._ids[name] = matches[0]
        return self._ids[name]

    def run(self, agent: str, message: str, thread_id: str | None = None) -> tuple[str, str, int]:
        """Returns (reply text, thread id, number of tool calls)."""
        payload = {"agent_id": self.agent_id(agent), "message": {"role": "user", "content": message}}
        if thread_id:
            payload["thread_id"] = thread_id
        r = requests.post(f"{INSTANCE}/v1/orchestrate/runs", headers=self._headers(), json=payload, timeout=60)
        r.raise_for_status()
        run = r.json()
        deadline = time.time() + 300
        while True:
            s = requests.get(f"{INSTANCE}/v1/orchestrate/runs/{run['run_id']}", headers=self._headers(), timeout=30).json()
            if s.get("status") in {"completed", "failed", "cancelled", "expired", "requires_input"}:
                break
            if time.time() > deadline:
                raise TimeoutError("run timed out")
            time.sleep(2)
        if s["status"] != "completed":
            raise RuntimeError(f"run {s['status']}: {s.get('last_error')}")
        msg = s["result"]["data"]["message"]
        text = "".join(p.get("text", "") for p in msg["content"] if p.get("response_type") == "text")
        tool_calls = sum(1 for step in msg.get("step_history", []) for d in step.get("step_details", [])
                         if d.get("type") == "tool_calls" for _ in d.get("tool_calls", []))
        return text, run["thread_id"], tool_calls


def strip_fence(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    return m.group(1) if m else text


@dataclass
class Result:
    phase: str
    item: str
    first_try_valid: bool = False
    valid: bool = False
    seconds: float = 0.0
    tool_calls: int = 0
    error: str = ""
    value: BaseModel | None = field(default=None, repr=False)


def ask(wxo: Orchestrate, phase: str, item: str, agent: str, message: str, model: type[BaseModel]) -> Result:
    """One structured-output request with the workshop's validate-and-retry-once policy."""
    res, t0 = Result(phase, item), time.time()
    try:
        text, thread, res.tool_calls = wxo.run(agent, message)
        for attempt in range(2):
            try:
                res.value = model.model_validate_json(strip_fence(text))
                res.valid, res.first_try_valid = True, attempt == 0
                break
            except ValidationError as e:
                res.error = str(e).splitlines()[0][:160] + f" | reply starts: {text[:80]!r}"
                if attempt == 0:
                    text, thread, _ = wxo.run(agent, "Your reply was not valid JSON for the required schema. Error:\n"
                                              f"{e}\nReply again with ONLY the corrected JSON object.", thread)
    except Exception as e:  # network/run failures count as invalid, with the reason
        res.error = f"{type(e).__name__}: {e}"[:200]
    res.seconds = time.time() - t0
    return res


def deploy_judges(wxo: Orchestrate):
    """Create (or update) the three tool-less judge agents through the Orchestrate API."""
    specs = [
        ("claim_extractor", "Extracts verifiable medical claims from one concern.",
         instructions_from(lab_prompt("lab3/agent/grounding.py", "_EXTRACT_PROMPT"), "CONCERN:")
         + "\nThe concern to process is in the user message.\n" + format_suffix(ExtractedClaims)),
        ("grounding_judge", "Judges whether each claim is supported by the source data.",
         instructions_from(lab_prompt("lab3/agent/grounding.py", "_JUDGE_PROMPT"), "SOURCE DATA")
         + "\nThe source data and the claims are in the user message.\n" + format_suffix(ClaimVerdicts)),
        ("critic", "Reviews concerns from the inbox assistant against the quality bar.",
         instructions_from(lab_prompt("lab3/agent/critic.py", "_CRITIC_PROMPT"), "CONCERNS:")
         + "\nThe concerns and grounding results are in the user message.\n" + format_suffix(CriticResult)),
    ]
    existing = {a["name"]: a["id"] for a in
                requests.get(f"{INSTANCE}/v1/orchestrate/agents", headers=wxo._headers(), timeout=30).json()}
    for name, description, instructions in specs:
        payload = {"additional_properties": {}, "spec_version": "v1", "kind": "native", "name": PREFIX + name,
                   "description": description, "style": "react_intrinsic", "llm": MODEL,  # the API name for react_core
                   "instructions": instructions, "tools": []}
        if PREFIX + name in existing:
            r = requests.patch(f"{INSTANCE}/v1/orchestrate/agents/{existing[PREFIX + name]}",
                               headers=wxo._headers(), json=payload, timeout=60)
        else:
            r = requests.post(f"{INSTANCE}/v1/orchestrate/agents", headers=wxo._headers(), json=payload, timeout=60)
        if not r.ok:
            sys.exit(f"Couldn't deploy {PREFIX + name}: HTTP {r.status_code} {r.text[:300]}")
    print(f"Deployed judge agents: {', '.join(PREFIX + s[0] for s in specs)}")


def summarize(results: list[Result]):
    print("\n=== Summary ===")
    print(f"{'phase':12} {'n':>3} {'1st-try valid':>14} {'valid after retry':>18} {'median s':>9}  failures")
    for phase in ("main agent", "extraction", "judge", "critic"):
        rs = [r for r in results if r.phase == phase]
        if not rs:
            continue
        first = sum(r.first_try_valid for r in rs)
        valid = sum(r.valid for r in rs)
        print(f"{phase:12} {len(rs):>3} {first:>9}/{len(rs):<4} {valid:>13}/{len(rs):<4} "
              f"{statistics.median(r.seconds for r in rs):>9.1f}  {len(rs) - valid}")
    failures = [r for r in results if not r.valid]
    if failures:
        print("\nFailures:")
        for r in failures:
            print(f"  {r.phase} / {r.item}: {r.error}")
    main = [r for r in results if r.phase == "main agent" and r.valid]
    if main:
        counts = [len(r.value.concerns) for r in main]
        zero = sum(1 for c in counts if c == 0)
        print(f"\nMain agent: concerns per patient {counts} (zero for {zero}/{len(main)}); "
              f"tool calls per run median {statistics.median(r.tool_calls for r in main)}")


def main():
    global INSTANCE, MAIN_AGENT, PREFIX, EHR_URL
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--patients", type=int, default=12, help="how many patients (from patient-001)")
    parser.add_argument("--rounds", type=int, default=1, help="repeat the main-agent pass this many times")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--skip-judges", action="store_true", help="only check the main agent")
    parser.add_argument("--ibmcloud-session", action="store_true",
                        help="authenticate as your logged-in `ibmcloud` user instead of WXO_API_KEY")
    parser.add_argument("--instance", help="Orchestrate instance URL (default: WXO_INSTANCE_URL)")
    parser.add_argument("--main-agent", help=f"main agent name (default: {MAIN_AGENT})")
    parser.add_argument("--prefix", help="name prefix for the judge agents (default: WXO_NAME_PREFIX)")
    parser.add_argument("--ehr-url", help="EHR the main agent's tools read, for grounding (default: EHR_API_URL)")
    args = parser.parse_args()

    INSTANCE = (args.instance or INSTANCE).rstrip("/")
    MAIN_AGENT = args.main_agent or MAIN_AGENT
    PREFIX = args.prefix if args.prefix is not None else PREFIX
    EHR_URL = (args.ehr_url or EHR_URL).rstrip("/")
    if not INSTANCE or not (API_KEY or args.ibmcloud_session):
        sys.exit("Missing WXO_INSTANCE_URL / WXO_API_KEY in .env. Run scripts/install.sh first.")
    wxo = Orchestrate(use_ibmcloud_session=args.ibmcloud_session)
    patients = [f"patient-{i:03d}" for i in range(1, args.patients + 1)]
    results: list[Result] = []

    # 1. Main agent, PatientConcerns: the exact message lab1/agent/agent.py sends.
    print(f"Main agent: {MAIN_AGENT} ({len(patients)} patients x {args.rounds} round(s))")
    jobs = [(p, r) for r in range(args.rounds) for p in patients]
    msg = ("Please review patient {}. Start by looking at their messages and record, then investigate "
           "any concerns you find. When done, output your findings.")
    with cf.ThreadPoolExecutor(args.workers) as ex:
        for res in ex.map(lambda j: ask(wxo, "main agent", f"{j[0]} r{j[1] + 1}", MAIN_AGENT, msg.format(j[0]),
                                        PatientConcerns), jobs):
            print(f"  {res.item}: {'ok' if res.valid else 'FAIL'}{'' if res.first_try_valid else ' (retry)' if res.valid else ''}"
                  f" {res.seconds:.0f}s, {res.tool_calls} tool calls"
                  + (f", {len(res.value.concerns)} concerns" if res.valid else f" — {res.error}"))
            results.append(res)

    # 2-4. Grounding and critic on the concerns the main agent produced.
    if not args.skip_judges:
        deploy_judges(wxo)
        time.sleep(10)
        concern_jobs = []
        for res in results:
            if res.valid and res.value.concerns and res.item.endswith("r1"):
                pid = res.item.split()[0]
                record = requests.get(f"{EHR_URL}/patients/{pid}", headers={"X-Tenant": EHR_TENANT}, timeout=30).json()
                concern_jobs.append((pid, res.value, record))

        def grounding_and_critic(job):
            pid, concerns, record = job
            out, grounding = [], []
            for c in concerns.concerns[:3]:
                concern_text = (f"Title: {c.title}\nSummary: {c.summary}\nAction: {c.action or '(none)'}\nEvidence:\n"
                                + "\n".join(f"- {e}" for e in c.evidence))
                ex_ = ask(wxo, "extraction", f"{pid} {c.title[:30]}", PREFIX + "claim_extractor", concern_text, ExtractedClaims)
                out.append(ex_)
                if ex_.valid and ex_.value.claims:
                    jd = ask(wxo, "judge", f"{pid} {c.title[:30]}", PREFIX + "grounding_judge",
                             "SOURCE DATA (tool call results):\n" + json.dumps(record)[:60000]
                             + "\n\nCLAIMS TO VERIFY:\n" + json.dumps(ex_.value.claims), ClaimVerdicts)
                    out.append(jd)
                    if jd.valid:
                        grounding.append({"concern_title": c.title, "verdicts": [v.model_dump() for v in jd.value.verdicts]})
            out.append(ask(wxo, "critic", pid, PREFIX + "critic",
                           "CONCERNS:\n" + concerns.model_dump_json() + "\n\nGROUNDING RESULTS:\n"
                           + (json.dumps(grounding) or "(no grounding results)"), CriticResult))
            return out

        print(f"\nGrounding + critic on {len(concern_jobs)} patients (up to 3 concerns each)")
        with cf.ThreadPoolExecutor(args.workers) as ex:
            for batch in ex.map(grounding_and_critic, concern_jobs):
                for res in batch:
                    print(f"  {res.phase:10} {res.item}: {'ok' if res.valid else 'FAIL'}"
                          f"{'' if res.first_try_valid or not res.valid else ' (retry)'} {res.seconds:.0f}s"
                          + ("" if res.valid else f" — {res.error}"))
                results.extend(batch)

    summarize(results)


if __name__ == "__main__":
    main()
