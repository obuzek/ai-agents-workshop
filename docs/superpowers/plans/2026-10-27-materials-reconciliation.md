# TXC 2026: reconciling the workshop materials with the IBM stack

Status: **plan for review**, 2026-10-27. Builds on the [student environment plan](2026-10-22-txc-student-environment.md) and the [IBM feature review](2026-10-22-ibm-feature-review.md).

The three questions this plan answers:

1. **Orchestrate vs LangGraph:** which runtime does each lab teach?
2. **Is the student-facing code simple enough?**
3. **What moves out of the labs?** The EHR now lives in the cloud, and what changes from lab to lab is the student's *agent*.

---

## 1. Where we are

**Runtime is split.** Lab 1 runs on watsonx Orchestrate (agent YAML + Python tools + runs API). Labs 2–4 still run LangGraph locally against Gemini, OpenAI or Anthropic. The IBM prerequisites still tell students to get an OpenAI key.

**Most lab code is harness, not agent.** Every lab folder carries the same scaffolding:

| File (per lab) | Lines | Changes between labs |
|---|---|---|
| `api.py` (agent API on :8001 for the UI) | 89–229 | Mostly additive endpoints (masking/grounding toggles, roles) |
| `run.py` (batch runner) | 55–87 | Nearly identical in Labs 1–3 |
| `store.py` (concern store) | 52 → 351 | Identical in Labs 1–3; Postgres in Lab 4 |
| `models.py` | 25 | Identical |
| `observability/masking.py` | 192 | Identical in Labs 2–4 |
| `grounding.py`, `critic.py` | 247 / 100 | Identical in Labs 3–4 |

What students actually learn from is much smaller: the agent definition (instructions, model, output format), the **tools**, and, from Lab 2 on, the guardrail layers. Today that's buried among ~600–1,100 lines per lab.

**The EHR is already out of the labs** (`app/`). Since the deploy, it runs once in the cloud as a multitenant service, and students' local EHR forwards to it. Students no longer need to read or touch it.

---

## 2. Recommendation: one Orchestrate agent that grows across the labs

**Teach one agent, hosted on Orchestrate, and have each lab change *the agent*, not the scaffolding around it.** Whatever can't run inside Orchestrate stays as a small local wrapper.

| Lab | Theme | What the student changes | Runs where |
|---|---|---|---|
| 1. Build | The naive agent | `agent.yaml` (instructions, model), `tools.py` (5 broad tools) | Orchestrate |
| 2. Observe | Traces + PII | Read the trace in Orchestrate; add the **PII Filter control** (input), the **post-invoke plug-in** (output), and **minimize fields in `tools.py`** (source) | Orchestrate |
| 3. Improve | Grounding + critic | Focused tools (`tools.py`); a **grounding/critic check** on the agent's answer | Agent on Orchestrate; checks in a local wrapper around the runs API (see decision D2) |
| 4. Secure | Data access | **Tool scoping by caller context** (the authorized patient comes from the run context, not the LLM); optional jailbreak guardrail control; RLS concern store stays local | Orchestrate + local Postgres |

Why Orchestrate throughout, rather than LangGraph locally:

- **One mental model.** "The agent is a definition you deploy; each lab changes the definition." No switching frameworks after Lab 1.
- **It's the simplest code.** A YAML file, a tools file, and one-file plug-ins, instead of graph wiring and callbacks.
- **The responsible-AI lessons get *more* concrete.** We verified each layer in traces (the student-environment plan, §5). The input control fires, the output plug-in fires, and the tool output stays raw. Students can see each layer, and each layer's gap, in the trace.
- **No third-party LLM keys.** Every lab uses the seat's IBM key.

What we give up, and how each loss is handled:

| LangGraph feature the labs use | On Orchestrate | How the materials handle it |
|---|---|---|
| Constrained decoding (`response_format`) | Not available on `react_core` | Lab 1 teaches "prompt for the schema → validate → retry". This is already built and verified (5 of 6 valid on the first try). It's a better production lesson anyway. |
| Langfuse custom spans, tags, cost | Built-in traces: no custom spans, no cost | Lab 2 reads Orchestrate's traces; cost becomes tokens × price (one table). |
| Presidio NER masking before export | No export hook; traces keep raw tool I/O | Lab 2's three layers. "Only the source layer keeps PHI out of the trace store" becomes the punchline. |
| The critic/grounding loop *inside* the graph | No custom graph nodes | Lab 3 wraps the hosted agent locally (D2). |
| Granite Guardian via Ollama | Hosted Guardian withdrawn | Keep Ollama as the optional path (unchanged). |

---

## 3. Simplifying the code: move the harness out of the labs

### Target layout

```text
workshop/                   ← shared harness, never edited by students (renamed from app/ + the per-lab copies)
  ehr/                      EHR API + store (local / server / remote modes)    — today app/api.py, app/store.py
  ui.py                     Streamlit inbox                                      — today app/ui.py
  runner.py                 calls the student's Orchestrate agent, validates, stores concerns
                            (one copy of today's lab1/agent/agent.py + run.py + api.py + store.py)
  deploy.py                 deploys a lab's agent: connection, tools, plug-ins, controls, agent (with the seat prefix)
  login.py                  today scripts/ibm_cloud_login.py
lab1/   agent.yaml  tools.py
lab2/   agent.yaml  tools.py  plugins/pii_output.py  controls.yaml
lab3/   agent.yaml  tools.py  plugins/…  checks/grounding.py  checks/critic.py
lab4/   agent.yaml  tools.py  plugins/…  controls.yaml   (+ db/init.sql for RLS)
```

Student commands become the same in every lab:

```bash
uv run workshop deploy lab2      # deploy this lab's agent definition under your seat prefix
uv run workshop ui --lab lab2    # the inbox, wired to your agent
```

Each lab folder holds only the agent definition. Students diff `lab1/` against `lab2/` and see exactly what changed (a few YAML lines, a plug-in, a tools edit), not 1,000 lines of scaffolding.

**One conflict with a standing rule:** your memory notes say "each lab is fully self-contained; never import from another lab." This layout keeps the *letter* of that rule (labs never import each other) but changes its *spirit*: labs now depend on a shared `workshop/` harness, much as they already depend on `app/`. **Decision D3.**

**Open-source edition:** this restructure would touch shared code. Options: (a) do it only on the IBM branch (`txc-2026-ibm`) and leave `main` and the open-source edition as they are; (b) bring it to both later. Given the time, I recommend (a). **Decision D4.**

---

## 4. Per-artifact change list

### Docs (IBM edition, `docs/ibm/content/`)

| Page | Change | Size |
|---|---|---|
| `prerequisites.md` | Already has the IBM key + login script (✅). Add: `uv tool install ibm-watsonx-orchestrate`; remove LLM provider keys (§3) and Langfuse/Ollama pre-pulls; keep Docker only for Lab 4 Postgres | M |
| `lab-1.md` | Rewrite "Understand the agent code" for `agent.yaml` + `tools.py` + validate/retry; the run step becomes `workshop deploy` + run a patient; add "open your trace in Orchestrate"; keep "What's broken" | L |
| `lab-2.md` | Replace Langfuse with Orchestrate traces; three PII layers with the verified trace evidence; PII diagram (feature review §C1); a shared-tenant visibility note | L |
| `lab-3.md` | Focused tools; grounding/critic as a local wrapper (D2); Guardian via Ollama optional; prompt-injection section unchanged in substance | M |
| `lab-4.md` | Context-scoped tools; RLS stays; controls/gateway diagram (§C2) as "infrastructure-layer controls"; note that controls don't inspect tool output | M |
| `environment-topology.md` | Replace the VSI picture with the verified topology (shared TechZone account, shared EHR on Code Engine, student laptops) | S |
| `index.md` | Event framing: TechXchange, what you'll use (Orchestrate, watsonx) | S |

### Slides (`docs/ibm/content/slides.md`)

| Slide id | Change |
|---|---|
| `lab1-langgraph` | → "Agents on watsonx Orchestrate": the definition (YAML) + tools + runs API; the ReAct loop is still the same idea |
| `lab1-structured-output` | → "No constrained decoding: validate and retry" |
| `lab2-langfuse`, `lab2-presidio` | → "Traces in Orchestrate" + the three PII layers (the diagram) |
| `lab2-what-traces-show` | Use a real Orchestrate trace screenshot (the student0 run) |
| `lab3-why-guardian`, `lab3-guardian` | Keep; note "hosted Guardian was withdrawn; we run it locally" |
| `lab4-production` | Add the controls/gateway diagram and the "shared tenant: everyone is admin" point |
| New | Architecture slide: the student's laptop ↔ shared EHR ↔ Orchestrate (from the environment plan §2) |

### Code

| Item | Size | Notes |
|---|---|---|
| Create `workshop/` (harness) from `app/` + `lab1/agent/{agent,api,run,store,models}.py` | M | Mostly moves; one runner for all labs |
| Generalize `deploy.py`: per-lab agent.yaml, tools, plug-ins (prefixed like tools), controls.yaml | M | Prefix rendering already works for tools |
| `lab2/`: plug-in (✅ written), `controls.yaml`, minimized `tools.py` | S | |
| `lab3/`: local wrapper calling the runs API, then grounding + critic (reuse today's code) | M–L | The judge LLM is the open question (D2) |
| `lab4/`: tools that read the authorized patient from the run context; RLS store via the harness | M | Context variables untested; spike first |

---

## 5. Decisions needed

- **D1. Orchestrate throughout?** (Recommended.) The alternative: Orchestrate for Lab 1 only, and LangGraph locally with an IBM model for Labs 2–4.
- **D2. Lab 3's judge model.** The grounding and critic checks need an LLM outside the agent. Options:
  - (a) a second Orchestrate agent as the judge, called through the runs API; this needs no new credentials and keeps "a different model judges";
  - (b) watsonx.ai directly, which needs a project/space per seat and a first Studio login;
  - (c) `ChatWxO`, untested.
  
  Recommended: **(a)**.
- **D3. A shared `workshop/` harness** instead of fully self-contained labs?
- **D4. Restructure on the IBM branch only?** (Recommended for the time available.)
- **D5. Scope for the event.** If time runs short: Labs 1–2 fully on Orchestrate; Labs 3–4 presented hybrid, with "on IBM, this maps to…" boxes.

---

## 6. Suggested order of work

1. **Decide D1–D5** (15 minutes together).
2. **Harness + generalized deploy** (`workshop/`), with Lab 1 moved onto it. Verify as a seat end to end: login → deploy → UI → reply → re-run.
3. **Lab 2**, code then docs, because it's the strongest IBM story (traces + three PII layers).
4. **Slides**: Lab 1–2 slides and the architecture slide.
5. **Lab 3 and Lab 4** to the depth time allows (D5).
6. **Second-seat dry run** of the whole student path, then branch/merge decisions for `txc-2026-ibm`.

---

## 7. Status of what's deployed (as of this writing)

- ✅ Live docs site with `/ibm/` and `/oss/` (PR #33 merged; ibm.biz link resolves).
- ✅ Shared multitenant EHR: `https://workshop-ehr.2g7six4hbjvx.us-south.codeengine.appdomain.cloud`. Code Engine, instructor account, one always-on copy, `EHR_MODE=server`. Isolation was verified with two tenants in the cloud.
- ✅ The login script sets the API key, instance, seat prefix, EHR tenant (a key fingerprint) and shared EHR URL, and activates the student's Orchestrate CLI environment.
- ⚠️ **Seat API keys expire within days.** `student0`'s key from 10-22 was rejected on 10-27 as "expired". Students must create keys *during* the workshop. A new key means a new EHR tenant (fresh data).
- ⏳ The student0 end-to-end run against the shared EHR is waiting on a fresh key.
