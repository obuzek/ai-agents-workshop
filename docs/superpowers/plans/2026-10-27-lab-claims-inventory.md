# Lab claims inventory: pre-change (LangGraph) vs IBM edition

Generated 2026-10-27 from `origin/main` (pre-change OSS text, slides, code) and `origin/txc-2026-ibm`.
Status key: Verified = tested live; Built-unverified; None; Reframed.

---

# LAB 1

# Lab 1 ("The Naive Agent"): claims inventory against pre-change code and the IBM edition

Sources: `origin/main:docs/oss/content/lab-1.md` (cited as `L1:<line>`), `origin/main:docs/oss/content/slides.md` (cited by slide id), `origin/main:lab1/agent/*`, `origin/main:app/llm.py`, and `origin/txc-2026-ibm:lab1/agent/*`.

**The IBM docs have not been converted.** `origin/txc-2026-ibm:docs/ibm/content/lab-1.md` is byte-identical to the OSS lab-1.md (`git diff --stat` shows no difference). The IBM `slides.md` still has the "Why LangGraph?" slide (line 489), shows `create_react_agent` (line 496), and says "Lab 1: LangGraph + constrained decoding" (line 897). Only an architecture slide (around line 358) was added.

## 1. Claims inventory

| # | Claim (short) | Where | Pre-change implementation | Simplicity before | IBM-side equivalent | IBM status |
|---|---|---|---|---|---|---|
| 1 | Agents are a ReAct loop: Observe → Reason → Act, repeated | L1:38-57; slide `what-is-an-agent` | `agent.py:_build_agent` via `create_react_agent` (agent.py:83-93) | Simple: one library call | `agent.yaml` `style: react_core`; Orchestrate runs the loop | Verified (deploys and runs) |
| 2 | Learning objective: the ReAct loop "maps to LangGraph's `create_react_agent`" | L1:112 | agent.py:26,83 | Simple | Maps to `agent.yaml` + `deploy.py` instead. Text not updated | Verified code; docs wrong |
| 3 | "The core is surprisingly short"; "That's the whole agent" (7-line `_build_agent`) | L1:177-188; `lab1-langgraph` | agent.py:74-93, body is 7 lines | Simple: whole agent fits on one slide | agent.yaml (57) + deploy.py (151) + agent.py client (193) | False on IBM (see §3) |
| 4 | `create_react_agent` handles the loop, then makes one final Structured Outputs call | L1:190-194; `lab1-langgraph` | LangGraph internal (`generate_structured_response`, a separate extra LLM call) | Simple, but hidden | No final constrained call. JSON schema is appended to the instructions (deploy.py:64-81) | None (cannot exist on react_core) |
| 5 | Lab 3 reuses the same `StateGraph` primitives for the critic loop | `lab1-langgraph` (last line) | lab3 code (not checked here) | — | Critic/revision loop on Orchestrate | None |
| 6 | The `@tool` decorator registers the function, builds a JSON schema from type hints and docstring, and exposes it to the LLM | L1:152-168; `lab1-tools-and-schema` | tools.py:22,34-94 (`langchain_core.tools.tool`) | Simple: plain functions plus a decorator | ADK `@tool(expected_credentials=...)` (IBM tools.py:27,50-110) | Verified (tools import and are called) |
| 7 | Five tools: list_patients, get_patient_record, get_messages, search_labs, get_inbox | L1:170 | tools.py:34-99, about 60 lines | Simple: each is 3 lines of `requests.get`, except search_labs (about 20) | Same five, through a connection-backed `_get` with an `X-Tenant` header (IBM tools.py:39-42) | Verified to exist. Median 1 tool call per run (mostly get_patient_record) |
| 8 | "Agent decides which tools to call and in what order — we don't script that" | `lab1-tools-and-schema`; L1:286 | Emergent behaviour of the LLM. Text only (no measurement pre-change) | n/a | Same claim on react_core | Contradicted by data: median 1 call |
| 9 | Tools can read any patient, not just the one under review ("What could go wrong?") | L1:172-173, L1:300-302; tools.py:9-11 | Text plus the deliberate design of tools.py | Simple | Still true within a tenant (list_patients, get_inbox are unscoped) | Built; cross-patient access not exercised |
| 10 | `response_format=PatientConcerns` uses Structured Outputs / constrained decoding | L1:196-202; `lab1-structured-output` | agent.py:92. Gemini default `method="json_schema"` (constrained); OpenAI `json_schema`; **Anthropic defaults to `function_calling`, which is not token masking** | Simple: one kwarg. The claim was provider-dependent even pre-change | None: `response_format` makes react_core runs fail | None (verified impossible) |
| 11 | "The model literally cannot produce malformed JSON"; not try-and-retry | L1:200; `lab1-structured-output` | Same as row 10 | — | Prompt for JSON, Pydantic validation, one retry (IBM agent.py:42-45,165-178) | Verified: 20/24 valid on first try, 24/24 after one retry |
| 12 | No parsing code, no code-fence stripping, no manual mapping | L1:204,288; agent.py:122-124 | agent.py:124, `result["structured_response"]` | Simple | IBM agent.py has `_strip_code_fence` (138-144) and a retry loop | False on IBM |
| 13 | Fewer tokens and lower cost: the schema replaces 200-400 prompt tokens and avoids retries | L1:206,288 | Text only. Pre-change also added an extra final LLM call (row 4), never measured | — | IBM appends the full inlined JSON schema to the prompt and retries on failure: the exact anti-pattern the text describes | False on IBM; unmeasured before |
| 14 | "Asking nicely" (prompting for structure) is unreliable; speed-governor analogy | L1:210-213; `lab1-structured-output` | Text only | — | The IBM agent *is* "asking nicely". 17% first-try failure is direct evidence for the claim | Verified (as a counter-example) |
| 15 | Background agents need guaranteed output ("fails silently at 3 AM") | L1:208; `lab1-structured-output` | Text only | — | Validate plus retry; raises after the retry fails | Verified 24/24 in the test, not guaranteed |
| 16 | `Concern` is the explicit agent↔UI contract (fields listed) | L1:215-233; `lab1-tools-and-schema` | models.py (25 lines) + app/models.py:288-301 | Simple: Pydantic models | Same models.py; deploy.py generates the prompt schema from it | Verified |
| 17 | "The doctor never sees raw LLM output" | L1:233; `lab1-tools-and-schema` | UI renders only stored `Concern`s (app/ui.py:482-560) | Moderate: the UI is 760 lines but not student-facing | Same UI path. But Orchestrate traces and the agent's chat in Orchestrate expose raw output to the seat owner | Verified for the UI path only |
| 18 | Chat agent vs background agent (trigger, session, end, UI table) | L1:59-72; `lab1-background-vs-chat` | Text, plus the Run Agent button → api.py:63-81 background thread | Simple | Same local api.py, now starting an Orchestrate run | Verified (Lab 1 API works with the Orchestrate backend) |
| 19 | The UI is the constraint: no chat box, so no drafting or diagnosis requests | L1:74-75,290; `lab1-background-vs-chat`; `our-approach-2` | Design of app/ui.py (no chat input) | Simple | Weaker: the deployed agent is a native Orchestrate agent that seat users can open in Orchestrate's chat UI | Partly true; not tested |
| 20 | Backgrounding "prevents feedback loops on jailbreaking and prompt injection" | intro `our-approach-2` | Text only | — | Orchestrate Content Guardrails exist; chat exposure (row 19) undercuts the claim | None (controls untested) |
| 21 | "We are not building a drafting/diagnosing agent"; surface and organize only | L1:31-34; `our-approach` | SYSTEM_PROMPT agent.py:69-70 (2 lines) | Simple | Same lines in agent.yaml:50-51 | Built; behaviour unmeasured |
| 22 | Synthetic data: 12 patients, 3 providers, Lakeview; sections table; 10 unresolved messages for Dr. Kim | L1:18-19,79-96 | `data/patients/*.json` served by app/api.py | Simple: local JSON | Shared multitenant EHR on Code Engine, private copy per student | Verified (tenant isolation, restart survival) |
| 23 | Data generation methodology (diversity matrix, decoupling, isolated subagents, real codes) | L1:98-104 | `data/README.md`, `patient_specs.json` | n/a | n/a (conceptual, same data) | n/a |
| 24 | Step 1: the EHR viewer runs with no API key | L1:124 | `streamlit run app/ui.py` + local data | Simple | UI plus local EHR in remote mode. Tenant is a SHA-256 fingerprint of the API key (IBM slides.md:441), so a key is now needed | Verified UI; "no key" claim likely false |
| 25 | UI features: patient selector with emoji status, record tabs, empty Concerns panel, inbox | L1:132-137 | app/ui.py | Not student-facing | Same UI | Verified (Playwright) |
| 26 | Step 3: configure the LLM provider in `.env`, start `lab1.agent.api` | L1:239-245 | app/llm.py (78 lines, `LLM_PROVIDER`); api.py | Simple: one env var plus one uvicorn command | `WXO_*` env vars, `orchestrate env add/activate`, `deploy.py`, wait minutes for tools. **None of this is in the lab text** | Verified code; docs missing |
| 27 | After Run Agent, concerns are sorted by urgency, each has an action, Related links jump to sources, dropdown shows urgency indicators | L1:250-263 | app/ui.py:448-560 | Not student-facing | Same UI | Verified; thin when a patient returns 0 concerns |
| 28 | Step 4: write down right / wrong / missing per patient | L1:267-278 | Text only (exercise) | Simple | Same exercise | Runnable; output quality changes the findings |
| 29 | What's working: the ReAct loop works and the agent investigates based on what it finds | L1:286 | Text only | — | react_core | Contradicted: median 1 tool call |
| 30 | What's working: background processing writes to a store | L1:292 | store.py (52 lines, flat JSON) + run.py | Simple | Unchanged store.py / run.py | Verified via the API path; run.py batch mode unverified |
| 31 | Broken: no access controls / HIPAA minimum necessary | L1:300-302 | tools.py:9-11 | Simple | Lab 4 fix reframed as discussion; caller-scoped tools untested | Reframed |
| 32 | Broken: concerns unstable; store overwritten every run, no history | L1:304-306 | store.py:25-29, run.py:27-35 | Simple | Same store code | Built; instability not measured on gpt-oss |
| 33 | Broken: no hallucination checks | L1:308-310 | Text only | — | Lab 3 judge agents exist only in a test harness | None in lab code |
| 34 | Broken: agent oversteps despite the prompt (suggests diagnoses such as "possible hypothyroidism" and treatments such as "consider levothyroxine") | L1:312-320 | Text only (asserted observation) | — | Same prompt, different model | Unverified on gpt-oss-120b |
| 35 | Broken: no completeness checks | L1:322-324 | Text only | — | n/a; 0-concern runs make this visible | True |
| 36 | Up Next: Lab 2 tracing, logging, cost; Lab 3 validation, grounding, guardrails; Lab 4 scoped tools, access control, audit | L1:334-339 | Later labs | — | Orchestrate traces (no cost, no custom spans); Lab 3 partial; Lab 4 reframed | Mixed (see brief) |
| 37 | Wrap-up: "Lab 1: LangGraph + constrained decoding"; "structure limits what the agent can say" | `wrap-up-summary`; `responsible-by-design` | — | — | Orchestrate react_core + validate/retry | False on IBM as written |
| 38 | ADLC "Tool access" dimension maps to Lab 1 | `adlc-agents` (speaker note) | Conceptual | — | n/a | n/a |

## 2. Exercises

What students did hands-on before the change, and whether the IBM edition can run each now:

1. **`uv run streamlit run app/ui.py --server.port 8501` and explore patients, tabs and inbox (L1:126-142).** Partly. The UI runs against the shared EHR in remote mode (verified with Playwright). It now needs `.env` with the EHR URL and tenant (derived from the API key), which contradicts "no API key needed".
2. **Read `tools.py`, `agent.py` and `models.py` and match them to the excerpts (L1:148-233).** Partly. `tools.py` and `models.py` still match closely. The `agent.py` excerpt (`_build_agent`, `create_react_agent`) does not exist on the IBM branch: the file is now an IAM, polling and retry client. The system prompt moved to `agent.yaml`, and the output schema is appended only at deploy time, so students cannot see the actual prompt in the repo.
3. **Configure `LLM_PROVIDER` / key in `.env` (L1:239).** No. It is replaced by `WXO_INSTANCE_URL`, `WXO_API_KEY`, `WXO_NAME_PREFIX`, `EHR_API_URL` and `EHR_TENANT`, plus `orchestrate env add` / `activate`.
4. **(Implicit, new) Deploy the agent.** Yes in code: `uv run python -m lab1.agent.deploy` is verified per seat. It is missing from the lab text, and new tools take a few minutes to become callable.
5. **`uv run uvicorn lab1.agent.api:app --port 8001` (L1:245).** Yes, verified with the Orchestrate backend, but only after step 4.
6. **Click Run Agent on 2-3 patients and observe sorting, actions, Related links and dropdown indicators (L1:250-263).** Partly. Mechanically it works, with 24/24 valid after one retry. Some patients return 0 concerns, so there is nothing to observe, and runs are slower (async polling plus a possible retry).
7. **Step 4: note right / wrong / missing per patient (L1:271-278).** Yes. Expect "missing" to dominate because the agent usually makes 1 tool call.
8. **"Run twice on the same patient" to see instability (L1:306).** Yes. The mechanism (overwriting store) is unchanged. Not measured.
9. **"Read the system prompt carefully" and spot overstepping (L1:314-320).** Partly. The prompt is in `agent.yaml`, but whether gpt-oss-120b oversteps the same way has not been checked.
10. **Think question about cross-patient tool access (L1:173).** Yes (conceptual; the tools are still unscoped within a tenant).

There was no graded or code-modifying exercise before the change either. The hands-on work was: run, observe, critique.

## 3. Simplicity check

**Before the change.** The text points students at three files: `tools.py` (99 lines), `agent.py` (138) and `models.py` (25), so **262 lines**, about half of them comments.
- The real logic was a 7-line `_build_agent`, a 35-line prompt string, about 10 lines of `process_patient`, and five tools of about 3 lines each (search_labs is about 20).
- Setup was one env var (`LLM_PROVIDER`, default free-tier Gemini) and one uvicorn command.
- Everything ran in one local Python process, so a student could step through the whole loop.

**IBM version of the same piece: about 525 lines across six files, roughly 2×.**
- `agent.py` (193)
- `tools.py` (110)
- `deploy.py` (151)
- `agent.yaml` (57)
- `connection.yaml` (12)
- `requirements-orchestrate.txt` (1)

Moving parts that were added:
- **IAM token exchange and refresh**, agent-ID lookup by name, and async run creation and polling with timeout (IBM agent.py:59-127).
- **Step-history parsing** just to log which tools were called (agent.py:130-135). Before, this was visible in the LangGraph message list.
- **Code-fence stripping and a validate-and-retry loop** (agent.py:138-178), which replaces `response_format`.
- **`deploy.py` work:**
  - inlines Pydantic `$ref`s into a flat schema and appends it to the instructions;
  - **regex-rewrites the source of `tools.py`** to add per-seat name prefixes (deploy.py:84-101);
  - shells out to the `orchestrate` CLI three times (connection, tools, agent).
- **The loop and tools run remotely.** You cannot set a breakpoint in a tool or in the loop. Visibility comes only from traces, at 4 req/min with a 4-hour window.
- **External prerequisites:** `orchestrate` CLI install, `env add` / `activate`, an IBM Cloud API key, and a public EHR on Code Engine with a tenant header, plus a local EHR in remote mode for the UI.
- **Tools have to be self-contained** (no repo imports) because they are uploaded.
- **Comment drift:** the comment at IBM tools.py:25-26 says "switching frameworks meant only changing this import line". That is not true: `expected_credentials`, the connections lookup and the `_get` helper were all added.

To get back toward the old simplicity, students should only read `agent.yaml`, `tools.py` and `models.py`, and treat `deploy.py` and `agent.py` as plumbing they run but don't read. The docs need to say so explicitly.

## 4. Top gaps (most important first for a 2-hour workshop)

1. **The Structured Outputs / constrained decoding section is false on IBM, and the IBM code demonstrates the anti-pattern the text warns against.**
   - Claims: rows 10-13, 37; L1:198-213, 288; slides `lab1-structured-output` and `wrap-up-summary`.
   - Live behaviour: prompt-embedded schema, fence stripping, a retry, and 20/24 valid on the first try.
   - This is the main teaching point of Lab 1. It needs rewriting, for example as "here is the measured failure rate when you can't constrain decoding, and what we do about it".
   - Separately, the original was only strictly true for Gemini and OpenAI (Anthropic used `function_calling`). Its "fewer tokens" claim was never measured and ignored LangGraph's extra final structured call.
2. **The lab text cannot be followed on IBM.**
   - IBM `lab-1.md` is the unchanged OSS text. Step 3 says to configure an LLM provider. There is no deploy step, no `orchestrate` CLI setup, and no `WXO_*` / tenant variables, and the code excerpts point at LangGraph code that no longer exists.
   - The code is verified, but students depend on the instructor to fill these steps in.
3. **"The agent investigates autonomously" is contradicted by the data (rows 8, 29).**
   - The median run makes 1 tool call (only `get_patient_record`), and some patients get 0 concerns. Step 3 (L1:255) and Step 4 depend on the agent showing tool-driven investigation and producing concerns to critique.
   - This is a quality problem in a verified deployment, and it makes the "observe the ReAct loop" exercise weak.
4. **The simplicity claims ("surprisingly short", "That's the whole agent") no longer hold (row 3, L1:177; slide `lab1-langgraph`).** What a student needs to understand grew from 262 lines in one process to about 525 across six files, run remotely and via a CLI. The slide code is not in the repo.
5. **The "UI is the constraint, no chat box" claim and the background-against-jailbreak claim are weaker on Orchestrate (rows 19-20; `our-approach-2`).** The agent is a native Orchestrate agent that seat admins can chat with directly. Guardrail controls other than the PII Filter are untested. In the same area: the `lab1-langgraph` claim that Lab 3 reuses `StateGraph` primitives for the critic loop has no IBM equivalent (critic loop: none).

---

# LAB 2

# Lab 2 (Observability): claims inventory, pre-change code vs. IBM edition

Sources read: `origin/main:docs/oss/content/lab-2.md` (382 lines), `origin/main:docs/oss/content/slides.md` (slides 440–561 plus intro slide `adlc-agents`), `origin/main:lab2/agent/*`, `app/models.py`, `app/ui.py`, `pyproject.toml`, and `origin/txc-2026-ibm` (`lab1/agent/*`, `lab2/orchestrate/pii_output_plugin.py`, `docs/ibm/content/lab-2.md`).

**Key fact:** on `txc-2026-ibm`, `lab2/agent/*` is the same as `main`. `git diff --stat` touches only `lab1/agent/*` and the new `lab2/orchestrate/pii_output_plugin.py`. `docs/ibm/content/lab-2.md` is still the OSS Langfuse text, one for one. So the IBM edition currently has no Lab 2 agent, no Lab 2 instructions, and no Lab 2 exercise. The only Lab 2 pieces are the plug-in and the verified Orchestrate trace API. The Lab 2 agent still calls `app.llm.get_chat_model()` (Gemini, OpenAI or Anthropic), which the IBM edition does not allow.

## 1. Claims inventory

| # | Claim | Where | Pre-change implementation (student-facing lines) | Simplicity before | IBM-side equivalent | IBM status |
|---|---|---|---|---|---|---|
| 1 | Lab 2 maps to "Observability: can you explain what the agent did and why?" | slide `adlc-agents` (l.333–335) | text only | n/a | Orchestrate traces | Verified (API) |
| 2 | Agent observability needs content (prompts, tool args, outputs), not just metadata | `lab2-different`; lab-2.md "Why Observability Matters" l.12–16 | text only | n/a | n/a, conceptual | n/a |
| 3 | The trace store becomes a secondary store of PHI that needs governance | `lab2-different`; l.16–24 | text only (demonstrated by #9) | n/a | Orchestrate traces store raw PII from tool output; 30-day retention; visible across the tenant | Verified (and the risk is real) |
| 4 | "What to Log" table (log freely / with masking / do not log) | `lab2-what-to-log`; l.26–35 | text only | n/a | n/a, conceptual; Orchestrate gives no control over what is logged | n/a |
| 5 | Langfuse is self-hosted in Docker and "nothing leaves the building" | `lab2-langfuse`; Step 1 l.52–61 | `docker-compose.langfuse.yml` (168 lines, 6 containers, pre-seeded keys) | Simple for students (one command); compose file is complex but hidden | Orchestrate SaaS traces. The claim does **not** hold: traces live on IBM's tenant | Reframe needed (not done) |
| 6 | Instrumentation is "three lines"; one callback at the entry point propagates to every LLM and tool call | `lab2-langfuse`; Step 2 l.77–103 | `lab2/agent/agent.py:88,109-118`; about 15 new lines (41-line diff vs Lab 1, mostly comments) | Simple: one handler plus a `config=` argument | Built-in tracing, zero code | Verified (stronger claim: 0 lines) |
| 7 | Traces are tagged by patient and grouped by session (`langfuse_session_id`, `langfuse_tags`) | Step 2 l.95–98; "Filtering and search" l.318–324 | `agent.py:113-116` | Simple | No custom tags or sessions on Orchestrate traces | None (not possible) |
| 8 | Run the agent from the UI and the trace appears | Step 3 l.107–119 | `lab2/agent/api.py` (107 lines), `run.py` | Simple | Lab 1 Orchestrate agent plus the local agent API; a Lab 2 API is not built | Partial: Lab 1 path verified, Lab 2 none |
| 9 | Tool outputs in the trace show names, DOB, phone, email, address, member ID in plain text | `lab2-pii`; Step 4 l.123–134 | Comes from the masking toggle defaulting to off (`masking.py:152`) | Simple | Orchestrate traces show full tool I/O with raw PII | Verified via API; Analyze UI view not checked |
| 10 | Masking is client-side and runs before data leaves the process ("strongest guarantee") | `lab2-pii`; Step 5 l.144; "What's Working" l.346 | `masking.py:155-192` (`mask_pii` passed to `Langfuse(mask=...)`) | Moderate: 192-line module | No client-side hook into Orchestrate traces. Post-invoke plug-in masks only the **final answer**, not traces | None for traces; answer masking built, verified once, not wired |
| 11 | Layer 1: Pydantic `_pii`/`_phi` annotations redact fields by name (`<PII_REDACTED>`) | `lab2-pii`; Step 5 l.150–161 | `app/models.py:28-36,177-205`; `masking.py:33-53,128-142` | Moderate. **Likely not exercised on tool output:** tools return `resp.json()` dicts (`tools.py:39,47,55`), so `_mask_value` takes the dict branch (l.122) and plain strings go to Presidio; only a BaseModel (e.g. `PatientConcerns.patient_name`) would hit Layer 1. Inferred from code, not run | n/a; Orchestrate tool output is not run through a mask | None |
| 12 | Layer 2: Presidio (spaCy NER plus regex) catches PII in free text; custom member-ID recognizer | `lab2-presidio`; Step 5 l.163–177 | `masking.py:58-89` | Moderate: needs a spaCy model, and none is installed anywhere in the repo (no `en_core_web_*` in `pyproject.toml` or scripts); presumably downloaded at runtime | Platform PII Filter (regex, no names) runs only at `agent_pre_invoke`; plug-in is regex on the answer | Partial: input filter verified; answer plug-in verified once, unwired |
| 13 | Presidio "hooks into the same callback layer as Langfuse. One callback stack handles both" | `lab2-presidio` | Not how the code works: masking goes through `Langfuse(mask=)` (`masking.py:190`), not a LangChain callback | text only / inaccurate | n/a | n/a |
| 14 | NER fails on short strings like "Patricia Kowalski"; annotations don't | `lab2-pii`; `lab2-presidio`; l.179–181 | text, plus #11 code | Simple concept | Regex plug-in catches no names at all (plug-in docstring l.43–44) | n/a; gap is worse |
| 15 | Toggle "PII Masking" in the UI and re-run without restarting | Step 5 l.195–197 | `api.py:95-107` (`/masking`, `/masking/toggle`); `app/ui.py:188-205,742-749`; module global `masking_enabled` | Simple | Would mean redeploying the agent with or without the plug-in, or binding/unbinding a control | None |
| 16 | After masking, trace tool outputs show `<PII_REDACTED>`, `<PHI_REDACTED>`, `<PERSON>` etc. | Step 6 l.201–211 | See #11: `<PII_REDACTED>` in tool outputs is unlikely given dict outputs; Presidio placeholders plausible. Not run | n/a | Not achievable: Orchestrate traces keep raw tool output | None |
| 17 | Masked and unmasked traces can be compared side by side | Step 6 tip l.213–214 | depends on #15 | Simple | Compare a trace with and without the plug-in; only the final answer differs | None |
| 18 | Standalone first names may still leak in LLM spans | Step 6 warning l.216–217 | text only | n/a | Regex plug-in misses all names | n/a (more true) |
| 19 | Trace shows nested timeline: root span, LLM spans with tokens and latency, tool spans with I/O, cost | Step 7.1 l.225–234; `lab2-langfuse` | Langfuse `CallbackHandler` | Simple | Run → LLM call (model, tokens) → tool calls with full I/O; **no cost** | Verified via API, except cost |
| 20 | The ReAct loop is visible; count LLM calls and tool order; spot repeat calls | Step 7.2 l.236–244; `lab2-what-traces-show` | Langfuse | Simple | Same, from the Orchestrate trace | Verified via API. Agent usually makes one tool call (median 1), so there is little loop to see |
| 21 | Run twice and compare: tool order and concerns differ (instability) | 7.2 callout l.246–247; "Concerns are still unstable" l.360–362 | text plus observation | Simple | Same, via the trace API at 4 req/min | Partial: possible, not demonstrated |
| 22 | Implicit summarization: compare tool output with concerns to spot hallucination, omission, distortion | 7.3 l.249–259; `lab2-what-traces-show` | text plus observation | Simple | Same, via the trace | Partial: data available; Analyze UI not checked |
| 23 | `get_patient_record` returns the whole record (cost, context, and trace exposure) | 7.4 l.261–268 | `tools.py:42-47` | Simple | Same tool in IBM `lab1/agent/tools.py:58-63` | Verified (same behavior) |
| 24 | Narrower tools would shrink traces and cost; "revisit in Lab 3" | 7.4 callout l.270–271 | text only | n/a | Focused tools on Orchestrate | None |
| 25 | The synthetic "user" prompt is invisible to the doctor but visible in the trace | 7.5 l.273–285; `lab2-what-traces-show` | `agent.py:97-101` | Simple | Orchestrate trace shows LLM input | Verified to the extent traces show LLM input; this specific view not checked |
| 26 | Add to Dataset / Annotate in the UI with no code | 7.6 l.287–295; `lab2-datasets` | Langfuse UI only | Simple | Orchestrate evaluation/datasets or watsonx.governance | None (governance unverified) |
| 27 | Scores and LLM-as-Judge (conceptual; Lab 3 builds it) | 7.7 l.297–307; `lab2-datasets` | text only | n/a | Lab 3 judge agents | Built-verified as a test harness (`scripts/check_structured_outputs.py`), not lab code; no scores written back to traces |
| 28 | Langfuse computes cost per run; ~$0.10/run arithmetic | "Cost tracking" l.309–316; `lab2-what-traces-show`; "What's Working" l.348 | Langfuse pricing tables (depends on model being priced) | Simple | Orchestrate traces carry tokens, no cost | None |
| 29 | Filter by tags, session, time range | l.318–324 | Langfuse UI plus #7 | Simple | Trace API has a time window (4h); no tags or sessions | Partial (time only) |
| 30 | Structured logging and metrics are out of scope | "What's Not Covered" l.328–336 | text only | n/a | n/a, conceptual | n/a |
| 31 | "Full visibility into every LLM call, tool call, decision step with timing and tokens" | "What's Working" l.344 | Langfuse | Simple | Orchestrate traces | Verified via API |
| 32 | "Two-layer PII/PHI masking … client-side … strongest guarantee" | "What's Working" l.346 | `masking.py` | Moderate; Layer 1 effectiveness doubtful (#11) | Input filter plus answer plug-in; traces unmasked | False on IBM side as written |
| 33 | Still hallucinates / unstable / oversteps; traces make it auditable, not preventable | "What's Still Broken" l.352–366 | text only | n/a | Same on Orchestrate (0 concerns for some patients is an additional failure mode) | n/a, holds |
| 34 | Agent behavior is identical to Lab 1 (same prompt, `response_format`) | `agent.py:31-32,70-78` | `create_react_agent(response_format=PatientConcerns)` | Simple | Lab 1 Orchestrate agent: no constrained decoding; JSON schema in instructions plus Pydantic validation and one retry | Verified (20/24 valid first try, 24/24 after retry) |

## 2. Exercises (pre-change, hands-on)

| Step | Student action | IBM edition can run it? |
|---|---|---|
| 1 | `docker compose -f docker-compose.langfuse.yml up -d`; log in at localhost:3000 | No. Not applicable; replaced by the Orchestrate Analyze UI, CLI or API. No instructions written; Analyze UI not checked. |
| 2 | Read `lab2/agent/agent.py` vs `lab1` (callback diff) | No equivalent diff. Tracing is zero-code on Orchestrate, so there is nothing to read. Possible substitute: read `pii_output_plugin.py` plus the `plugins:` YAML block. |
| 3 | `uv run uvicorn lab2.agent.api:app --port 8001` plus Streamlit; Run Agent | Partly. Works with the **lab1** Orchestrate API. `lab2.agent.api` still runs LangGraph with outside providers. |
| 4 | Open the trace and find raw PHI in tool outputs | Partly. Raw PHI verified via the trace API; not checked in the Analyze UI. 4 req/min and tenant-wide visibility affect a room of seats (students could see each other's traces). |
| 5 | Read `masking.py`; toggle PII Masking ON in the UI | No. No toggle; the plug-in is not wired into `deploy.py` or `agent.yaml` (grep finds no `plugin` in either). |
| 6 | Re-run and verify placeholders in the trace | No. Not achievable: Orchestrate traces keep raw tool output. Only the final answer can be masked (verified once). |
| 7.1–7.5 | Inspect span tree, tool order, run twice, compare tool output vs concerns, find the synthetic prompt | Partly. Data is present via the API; no student-facing instructions; UI path unchecked; a median of 1 tool call makes the "ReAct loop" observation thin. |
| 7.6 | Add to dataset / annotate in the UI | No (not built or checked). |
| Cost | Read the cost column | No (tokens only). |
| Filter | Filter by patient tag or session | No (time window only). |

## 3. Simplicity check

**Before:** the student was pointed at about 200 lines.
- `lab2/agent/agent.py`: 132 lines, about 15 of them new vs Lab 1.
- `lab2/agent/observability/masking.py`: 192 lines.
- The `_pii`/`_phi` helpers and annotations in `app/models.py`: about 25 lines.
- One compose command and one UI toggle.

What made it simple:
- (a) Tracing was one callback passed at `invoke`, and the diff from Lab 1 showed it.
- (b) Masking was one function given to `Langfuse(mask=...)`, switched by a module global (`masking.py:152`) through `/masking/toggle`. No restart, no redeploy.
- (c) Everything ran locally, so a before/after comparison took seconds.

Caveats on that simplicity: Presidio needs a spaCy model that is never installed explicitly. Layer 1 (annotations) probably does nothing on tool outputs, because the tools return dicts (`tools.py:39-47`, `masking.py:122`).

**IBM version now and what it would need:**
- Tracing: 0 lines, which is simpler. Reading traces needs the Analyze UI (unchecked) or CLI/API calls. The API is rate-limited (4 req/min), has a 4h window, and shows traces tenant-wide.
- Masking: the 75-line `lab2/orchestrate/pii_output_plugin.py`, plus these moving parts:
  1. `orchestrate tools import -k python -f …` (plug-in upload, per seat, with a name prefix).
  2. A `plugins: agent_post_invoke:` block in the agent YAML. `deploy.py` does not do this today.
  3. Redeploying the agent to switch masking on or off. There is no runtime toggle.
  4. Optionally binding the PII Filter control, which only affects user input.
- The result masks only the final answer. Traces and model context still hold raw PHI, so the "fix it, re-run, see placeholders in the trace" loop cannot be shown.
- The only fix that keeps PHI out of traces is source-side minimization (layer 3 in the plug-in docstring). That means changed or narrower tools, and none are built.

## 4. Top gaps, most important first

1. **The core exercise, "see PHI in traces → mask → verify the trace is clean" (Steps 4–6, slides `lab2-pii` and `lab2-presidio`, "What's Working" l.346), cannot run on Orchestrate.** Traces keep raw tool output. The plug-in masks only the answer and is not wired into `deploy.py`. Tool-level minimization: none. This is the lab's main teaching point and it needs a rewrite: "you cannot mask the platform's trace store, so minimize at the source."
2. **There is no IBM Lab 2 at all.** `lab2/agent/*` is the same as `main` (LangGraph plus outside LLM providers, which are disallowed), and `docs/ibm/content/lab-2.md` is the unchanged Langfuse text (Docker, localhost:3000, `create_langfuse_handler`). A student following the IBM docs today would run the wrong stack.
3. **Trace inspection steps (7.1–7.5, `lab2-what-traces-show`) have data but no verified student path.** The Analyze UI is not checked, the API is 4 req/min across a room of seats, and traces are visible tenant-wide. With a median of 1 tool call per run, the "ReAct loop / tool order" observation may show almost nothing.
4. **Cost, tags/sessions, dataset/annotate (#7, #26, #28, #29) are not available or not verified.** "Cost attribution per run" (l.348) and the $0.10/run exercise are false on Orchestrate. Datasets and annotation, and watsonx.governance, are unverified.
5. **Pre-change accuracy issues carried into the IBM docs:**
   - "Nothing leaves the building" (`lab2-langfuse`) is false on SaaS.
   - "Presidio hooks into the same callback layer" (`lab2-presidio`) is inaccurate even pre-change.
   - The Layer 1 `<PII_REDACTED>` result in tool outputs (Step 6) is doubtful even pre-change, because tools return dicts. This is inferred from code, not run.

---

# LAB 3

# Lab 3 inventory: claims, pre-change code, and IBM status

Lab 3 cannot be run on the IBM side today. On `origin/txc-2026-ibm`, `lab3/` and `docs/ibm/content/lab-3.md` are the same as on `main`. The IBM Lab 3 slides (ids `lab3-*`) still show the original Guardian content. The `lab3/` code still needs `app/llm.py` (Gemini, OpenAI or Anthropic, which are not allowed), Langfuse and LangGraph. The only IBM-side Lab 3 work is `scripts/check_structured_outputs.py`. It runs the Lab 3 prompts as three Orchestrate judge agents and is a test harness, not lab code.

## 1. Claims inventory

Sources: S = `origin/main:docs/oss/content/slides.md` (slide id). T = `origin/main:docs/oss/content/lab-3.md` (line number). Code = `origin/main:lab3/agent/*`.

| # | Claim | Where | Pre-change implementation | Simplicity before | IBM-side equivalent | IBM status |
|---|---|---|---|---|---|---|
| 1 | Lab 3 is the ADLC inner loop: run, inspect traces, find a failure, fix it | S `lab3-adlc-loop`; T 10-24 | Text only | n/a | n/a, conceptual | n/a |
| 2 | Each fix was driven by something seen in the traces, not by guessing | S `lab3-adlc-loop` | Text only. Nothing in the code shows which trace led to which fix. | n/a | Orchestrate traces (Analyze UI, CLI, API) | Traces verified via API. The trace-to-fix link remains a teaching claim only. |
| 3 | Lab 2 traces show made-up evidence (lab values or dates not in the record) | S `lab3-what-we-found` #1; T 44-46 | Text only. No example trace or reproduction script. | n/a | Compare the tool I/O in an Orchestrate trace with the final answer | None. No one has confirmed that gpt-oss-120b makes things up here. Its median of 1 tool call and 0 concerns for some patients is a different failure. |
| 4 | The agent goes off-task (suggests diagnoses or treatments) despite the prompt. "A system prompt is a request, not a constraint." | S `lab3-what-we-found` #2; T 48-50 | Text only. The prompt rules are in `lab3/agent/agent.py:68-69`. | n/a | Same claim against the `agent.yaml` instructions | None. Not checked on gpt-oss-120b. |
| 5 | `get_patient_record` dumps the whole record on every call | S `lab3-what-we-found` #3; T 52-54, 63-75 | `lab2/agent/tools.py:43` (about 6 lines) | Simple: one GET | The IBM Lab 1 `tools.py:59` `get_patient_record` | Verified as true: the IBM agent usually calls only this tool. |
| 6 | Prompt injection is reduced by design, because agent output goes to the doctor, not the patient | S `lab3-prompt-injection`; T 56-57; intro S `responsible-agent` (line 138) | Text only (architecture) | n/a | Same architecture. Content Guardrails jailbreak control exists. | Conceptual. Guardrail control not tested. |
| 7 | Keyword search tools replace `get_patient_record`, so the agent must say what it is looking for | S `lab3-focused-tools`; T 61-89 | `lab3/agent/tools.py` (99 lines, 8 tools, each about 6 lines) | Simple: copy-paste GET wrappers | Orchestrate ADK `@tool` versions of `search_*` | None |
| 8 | Without keywords, the agent would call every getter and rebuild the full record | T 91-92 | Text only | n/a | n/a, conceptual | n/a |
| 9 | Search uses a recursive keyword matcher over nested fields | T 94-110 | `app/api.py:116-125` `_contains` (10 lines) plus search endpoints at `app/api.py:137-183` | Simple | The shared EHR on Code Engine serves the same endpoints | Probably present: `app/api.py` changed by only +38 lines on the IBM branch. Search endpoints not tested through Orchestrate tools. |
| 10 | The dump-everything tool is gone | T 77 | `lab3/agent/tools.py:95-99` | n/a | n/a | **Only partly true before the change.** `get_messages` (all messages and threads), `get_demographics` (contact and insurance) and `get_inbox` (all patients) are still there, and Lab 2 already had `search_labs`. |
| 11 | Fewer tokens, lower cost, less PHI in traces | S `lab3-focused-tools`; T 273, 337 | Text only. Not measured. | n/a | Orchestrate traces show tokens but not cost | None. Cost is not shown on Orchestrate. |
| 12 | Claim extraction pulls specific, checkable claims and drops vague ones and IDs | S `lab3-critic` #1; T 137-150 | `grounding.py:68-119` `_extract_claims` (prompt plus about 15 lines) | Simple: one structured-output call | Tool-less Orchestrate agent `claim_extractor` returning `ExtractedClaims` | Verified (structured output 100% first try), but only in the check script, not as lab code |
| 13 | Each claim is checked against the raw tool output | S `lab3-critic` #2; T 152-169 | `grounding.py:125-152` `_check_llm_judge`. Context comes from `agent.py:106-117` `_extract_tool_context`. | Simple: about 10 lines, but it needs LangGraph message history | `grounding_judge` agent returning `ClaimVerdicts` | Built, but different. The check script judges against the **full patient record** from `GET /patients/{pid}` (`check_structured_outputs.py:312`), not tool output. Getting tool output needs trace parsing, which is not built. |
| 14 | Extract first because the grounding model gives one verdict per claim, so you can tell which part is wrong | S `lab3-critic`; T 187-188 | Shape of `grounding.py:57-62` `GroundingResult` | Simple | Same | Verified (schema only) |
| 15 | The critic checks on-task behavior and grounding, then returns per-concern feedback | S `lab3-critic` #3; T 190-203 | `critic.py:30-99` `evaluate` (about 25 lines of logic plus a prompt) | Simple: one structured-output call | `critic` agent returning `CriticResult` | Verified (structured output) in the check script only |
| 16 | Critic feedback goes back to the primary agent, which re-runs (the loop) | S `lab3-critic` #3; T 120-135 | `agent.py:76-233`: `ReviewState`, 2 nodes, `should_revise`, `MAX_REVISIONS=2` (about 60 lines of loop) | Moderate: LangGraph `StateGraph`, though easy to read | Local wrapper: runs API, judges, then a new run with feedback in the message (plan D2) | **None** |
| 17 | LangGraph handles state, the loop and routing, with no manual bookkeeping | T 230-234 | `agent.py:215-230` | Simple | Orchestrate has no custom graph nodes, so the wrapper would be plain Python | None. This claim stops being true on IBM. |
| 18 | The same LLM judging itself has self-evaluation bias | T 118; S `lab3-guardian` | `get_chat_model()` used everywhere | n/a | gpt-oss-120b judges gpt-oss-120b | True on IBM, so the bias is present. Plan D2(a) says "a different model judges", which is false with one model. |
| 19 | Granite Guardian is purpose-built, separate and independent | S `lab3-why-guardian`; T 185 | `grounding.py:158-196` `_check_guardian` (about 30 lines, Ollama) | Simple | Local Ollama only (hosted model withdrawn) | None. Not in IBM pre-work, although `docs/ibm/content/prerequisites.md:182-202` still lists it. |
| 20 | Guardian runs locally at about 1-2 s per claim, and no data leaves the machine | S `lab3-why-guardian` | Text only (timing) | n/a | Same if Ollama is installed | None. On IBM, patient data already leaves the laptop through Orchestrate, which weakens this point. |
| 21 | Guardian format: system `groundedness`, user Context+Claim, returns Yes or No | S `lab3-why-guardian`, `lab3-guardian`; T 171-183 | `grounding.py:173-194` | Simple | Same code | None |
| 22 | LLM-as-judge uses your API quota, Guardian is free | S `lab3-guardian`; T 327 | Text only | n/a | Orchestrate quota (seat) versus local | n/a. Needs rewording. |
| 23 | A runtime toggle switches LLM and Guardian grounding (same shape as Lab 2's masking toggle) | S `lab3-guardian`; T 154-159, 305-319 | `grounding.py:31`; `api.py:116-128`; `app/ui.py:221,757` | Simple: flag plus endpoint | Toggle in the local wrapper | None |
| 24 | Toggling to Guardian without Ollama makes the agent error or crash | T 250-251, 307-308; prereqs 231-232 | **Not true in code.** `grounding.py:230-240` catches the error and marks every claim `supported=True`. | n/a | n/a | n/a. This was already wrong before the change: it fails open without telling anyone. |
| 25 | Run the system with `uvicorn lab3.agent.api` plus the Streamlit UI | T 238-253 | `api.py` (128 lines), `run.py`, `store.py` | Moderate: same framework as Labs 1-2 | Local `lab3.agent.api` on :8001 with an Orchestrate backend (works for Lab 1) | None for Lab 3 |
| 26 | The trace has spans: Patient Review, Primary Agent, Grounding Check, Claim Extraction, Grounding: LLM/Guardian, Critic Evaluation | T 257-296 | `@observe` names at `agent.py:120,239`, `grounding.py:105,143,158,202`, `critic.py:73` | Simple: decorators | Orchestrate trace (run, LLM, tools). No custom spans. Judge agents show up as separate runs. | None. Custom spans are verified as not possible. |
| 27 | Check the tool calls (`search_*`, not `get_patient_record`), the keywords and the token count | T 269-273 | Needs #7 | n/a | Orchestrate trace shows tool I/O and tokens | Trace view verified. The focused tools to look at do not exist. |
| 28 | A rejected answer gives a second Primary Agent span with the feedback injected | T 295-300 | `agent.py:134-138` | Simple | A second Orchestrate run | None |
| 29 | The critic loop catches problems, and the second attempt is usually better | T 339 | Text only. Not measured. The critic approves automatically on error (`critic.py:93-99`). | n/a | n/a | None |
| 30 | "Grounding: LLM-as-Judge" and "Grounding: Granite Guardian" spans can be compared side by side | T 341; S `lab3-guardian` | Span names (#26) | Simple | n/a | None |
| 31 | Still broken: any tool can fetch any patient, with no access control or audit | T 345-347 | True: `tools.py` has no scoping | n/a | Lab 4 caller-scoped tools | Documented, not tested |
| 32 | Wrap-up: "Lab 3: Critic loop + Granite Guardian" | S `wrap-up-summary` | n/a | n/a | n/a | Neither exists on IBM. The slide is unchanged in IBM `slides.md:899`. |

## 2. Exercises (pre-change)

Lab 3 had no code-writing exercise. Students read the code, ran it, toggled modes and compared traces.

| Step | Pre-change action | Can the IBM edition run it? |
|---|---|---|
| Review the Lab 2 traces in Langfuse to find the three problems (T 42) | Open the Langfuse UI | **Partly.** Orchestrate traces exist and are verified via API, but no one has shown the three problems with gpt-oss-120b. |
| Step 1: read `lab2/agent/tools.py`, then `lab3/agent/tools.py` and `_contains` | Reading only | **Partly.** The files can be read, but the Lab 3 tools are LangChain `@tool`, not the Orchestrate ADK, and are never deployed. |
| Step 2: read `grounding.py`, `critic.py`, `agent.py` | Reading only | **Partly.** Prompts and schemas are reused by the check script. The LangGraph loop does not run on IBM. |
| Step 3: `uv run streamlit run app/ui.py` plus `uv run uvicorn lab3.agent.api:app --port 8001`, then Run Agent | Run commands | **No.** `lab3` calls `get_chat_model()`, which needs Gemini, OpenAI or Anthropic (not allowed), and Langfuse. |
| Step 4: read the span tree in Langfuse (Primary Agent, grounding, critic, revision) | Observe | **No.** There are no custom spans on Orchestrate and no loop. |
| Step 5: toggle the Grounding button between LLM and GUARDIAN and compare | Toggle in the UI | **No.** No wrapper, and Ollama is not in the IBM pre-work. |
| "Things to notice": count revision rounds, compare the first and second outputs, check `supported:false` verdicts | Observe | **No.** There is no loop. Verdicts exist only as check-script output, judged against the full record. |

## 3. Simplicity check

**Code students are pointed at before the change.** The four main Lab 3 files come to 714 lines; with the toggle endpoint in `api.py` it is 842. They are `lab3/agent/tools.py` (99 lines), `grounding.py` (247), `critic.py` (99), `agent.py` (269) and `api.py` (128, for the toggle). They also see about 10 lines of `_contains` in `app/api.py` and look at `lab2/agent/tools.py` for comparison. Not pointed at, but needed: `run.py` (87), `store.py` (52), `models.py` (25), and `observability/masking.py` (192).

**What made it simple.** Each concept was a short function in one place:
- Extraction, judging and the critic are each one `get_chat_model().with_structured_output(Model).invoke(PROMPT.format(...))` call, about 10-15 lines plus a prompt.
- Guardian is a for-loop over `ollama.chat`.
- The loop is a 6-field `TypedDict` plus a 15-line graph.
- Tracing is `@observe(name=...)` decorators.
- Tool output for grounding came free from the LangGraph message history (`_extract_tool_context`, 6 lines).
- Everything ran in one Python process with one model client.

The volume is closer to "moderate": a 247-line `grounding.py`, a 269-line `agent.py`, and try/except blocks that fail open. The individual pieces are simple.

**What the IBM version has today.** It has only `scripts/check_structured_outputs.py` (348 lines), a test harness. The extract, judge and critic steps require:
- creating three Orchestrate agents through the API (`deploy_judges`), with prompt text pulled out of `lab3/*.py` by `ast` (`lab_prompt`), and JSON Schema added to the instructions (`format_suffix`)
- running the runs API with polling, stripping code fences, Pydantic validation and a retry (`ask`)
- an IAM or API-key client class
- source data that is the full EHR record, not tool output, and is cut to 60,000 characters

**What the IBM version would still need for the loop the lab describes:**
- a local wrapper that calls the deployed agent through the runs API
- something to recover tool output, by parsing the trace API (4 requests/min, 4-hour window) or by re-fetching from the EHR
- three judge-agent calls for each concern
- critic feedback sent to a new run, with its own revision limit and state
- a re-deploy step per seat for the judges
- focused tools rewritten as ADK tools with credentials, plus redeploy
- a UI toggle wired to the wrapper

Moving parts added compared with before:
- 3 extra deployed agents per seat
- the runs-API client and polling
- schema-in-prompt plus retry instead of `with_structured_output`
- tool context recovered from traces
- no custom spans, so the trace story is spread across 4 or more separate runs

The "one function per concept" property is gone. Each concept now sits behind an HTTP agent call.

## 4. Top gaps, by importance for a 2-hour workshop

1. **The critic/revision loop (#15-17, #28-29, wrap-up #32).** This is the core of the lab, and nothing runnable exists on IBM. The verified judge agents prove only that the output schemas work. The wrapper, feedback injection and revision rounds are not built.
2. **Grounding against "raw tool output" (#13, #26-27).** The IBM harness judges against the full patient record. That makes the hallucination check weaker and contradicts the slide. Getting tool output needs trace-API parsing, which is limited to 4 requests/min.
3. **Focused tools (#7, #10-11, #27).** None exist on IBM. The IBM agent shows the very problem the lab fixes (median 1 call, to `get_patient_record`), so this is the most demonstrable fix if it is built. It is also the smallest one: ADK `@tool` wrappers over endpoints that probably already exist on the shared EHR.
4. **Granite Guardian and self-evaluation bias (#18-23, slides `lab3-why-guardian`, `lab3-guardian`).** These slides are unchanged on the IBM branch. Guardian is not in the IBM pre-work, and the only judge is gpt-oss-120b judging gpt-oss-120b. The slides currently promise a comparison students cannot make.
5. **The premise of the lab (#3-4).** The three failures are written as things students "will find" in the traces. No one has shown made-up evidence or off-task output with gpt-oss-120b on Orchestrate; the observed failure is under-investigation.

**Already wrong before the change:**
- The "will crash without Ollama" warning (T 250-251, 307-308): `grounding.py:230-240` instead marks every claim supported.
- `critic.py:93-99` approves automatically on error.

The materials don't mention either fail-open.

Files referenced:
- `/Users/olivia/workspace/workshops/ai-agents-workshop/lab3/agent/{agent.py,grounding.py,critic.py,tools.py,api.py}` (read from `origin/main`)
- `/Users/olivia/workspace/workshops/ai-agents-workshop/app/api.py`
- `scripts/check_structured_outputs.py`, `docs/superpowers/plans/2026-10-27-materials-reconciliation.md` and `docs/ibm/content/{lab-3.md,slides.md,prerequisites.md}` (read from `origin/txc-2026-ibm`)

---

# LAB 4

# Lab 4 inventory: "Securing Data Used By The Agent"

**Sources read:**
- Lab text: `origin/main:docs/oss/content/lab-4.md`
- Slides: `origin/main:docs/oss/content/slides.md`, lines 676–770 (`section-lab-4` through `lab4-production`), plus the intro and wrap-up slides
- Code: `origin/main:lab4/agent/*`, `lab4/db/init.sql`, `docker-compose.yml`, `.env-example`, `app/api.py`, `app/ui.py`
- IBM edition: `origin/txc-2026-ibm`

On the IBM branch:
- `docs/ibm/content/lab-4.md` is byte-identical to the OSS version.
- The IBM `slides.md` Lab 4 section (lines 782–870) still teaches Postgres RLS.
- `lab4/` has no changes.
- `app/llm.py` has no Orchestrate provider. It offers only Gemini, OpenAI and Anthropic, and none of those are allowed in the IBM edition.

## 1. Claims inventory

| # | Claim | Where | Pre-change implementation | Simplicity before | IBM-side equivalent | IBM status |
|---|---|---|---|---|---|---|
| 1 | The fourth agent dimension, "Tool access", maps to the "secure" lab | slide `adlc-agents` (note, l.335) | text only | n/a | n/a, conceptual | Reframed (still true as a concept) |
| 2 | Agent output (concerns) is PHI too | lab-4.md l.14; slide `lab4-output-is-sensitive` | text only | n/a | n/a, conceptual | Reframed (true; also applies to Orchestrate traces, which store raw PII) |
| 3 | In Labs 1–3 the flat JSON store lets any code path read or overwrite any concern, and a second run wipes the first | lab-4.md l.6; slide `lab4-output-is-sensitive` | Lab 1–3 store (not lab4 code) | Simple: one JSON file | IBM Lab 1 agent API still writes local JSON | Verified for Lab 1 (the store is unchanged) |
| 4 | Provider A and provider B can reach different conclusions about the same patient | slide `lab4-output-is-sensitive`; lab-4.md l.14 | text only, demonstrated by Step 3 | n/a | Per-provider runs on Orchestrate | None |
| 5 | Access control belongs in the data layer: RLS applies to every query, including ones not yet written | lab-4.md l.173–181; slide `lab4-rls` | `lab4/db/init.sql:47–67` (2 policies, about 20 lines). Connects as non-owner `app_user` (`.env-example:55`), so RLS really applies | Simple: one declarative policy | Closest analog: the shared EHR's tenant middleware (`app/api.py`, X-Tenant header) | Reframed (RLS as discussion). Tenant isolation on the EHR is Verified, but it isolates students, not providers |
| 6 | The app tells Postgres "who's asking" with `set_config('app.provider_id')` on every operation | lab-4.md l.101 | `store.py:_pg_conn` l.61–71 (1 SQL call) | Simple | Orchestrate context variables carrying the caller identity into tools | None (documented, not tested) |
| 7 | `get_concerns` / `save_concerns` (upsert by ID) / `share_concern` | lab-4.md l.95–99 | `store.py` l.97–184. The file is 351 lines because it has both a Postgres and a JSON backend plus a pool | Moderate: dual backend and a connection pool hide a small core | Concern store outside Orchestrate | Reframed / None |
| 8 | Switching roles shrinks the patient list (Rachel sees patients 1–6) | lab-4.md l.154 | `init.sql:81–91` seed; `api.py /role/patients`; `ui.py` about l.681 filter. **The filter is in the UI only.** `trigger_run` (`api.py:158`) and the tools never check `provider_patients` | Simple, but the enforcement is cosmetic | Per-provider roles | None |
| 9 | Rachel's concerns panel is empty even for shared patients, because of RLS | lab-4.md l.155–171 | `init.sql:50–58` + `_pg_get_concerns` | Simple | none | Reframed |
| 10 | RLS does not verify identity. A bug that sets the wrong provider leaks data. Production needs JWT, per-provider DB roles and `current_user` | lab-4.md l.174, l.250; slide `lab4-production` | text only (an accurate caveat) | n/a | Same weakness on IBM: the X-Tenant header is a self-asserted string | Reframed (works as discussion; the EHR header is a live example) |
| 11 | The agent is a delegate; its output takes the identity of whoever invoked it | lab-4.md l.196; slide `lab4-ownership` | `api.py:162` captures `_active_provider`; `run.py:30` saves under it. Module-global role, single user | Simple | Orchestrate run under the caller's identity | None |
| 12 | Default deny, explicit grant; sharing is auditable and "logged" | lab-4.md l.214; slide `lab4-ownership` | `init.sql:39–45, 60–67`; `store.py:_pg_share_concern`. The "audit" is only the `shared_concerns` row (shared_by, shared_at). There is no separate log | Simple | none | None |
| 13 | A shared concern shows as "Shared by Dr. Sarah Kim, MD" | lab-4.md l.204 | `api.py /shared-by`; `ui.py` l.492–507 | Simple | none | None |
| 14 | Tool scoping: a factory creates per-patient tools and denies other patient IDs | lab-4.md l.103–111; slide `lab4-scoping` | `tools.py:create_tools` + `_check_access` (about 12 lines of logic, 144 lines total) | Simple: a closure plus an equality check | Orchestrate tools are static uploaded functions, so a closure is impossible. It would need a context variable plus a check inside each tool | None |
| 15 | `list_patients` is "unscoped clinic directory" only; the agent "cannot pull clinical data for unauthorized patients" | lab-4.md l.227–229 | `tools.py:51–63`. **This is false as implemented.** `/patients` returns every patient's active conditions (`app/api.py:90`), and `get_inbox` returns every patient's message subjects and categories | Simple, but leaky | IBM Lab 1 `list_patients` is the same (and `get_patient_record` is unscoped) | None (the gap is present on IBM too) |
| 16 | Prompt-injection test: Elena (patient-005) asks about neighbor Patricia (patient-001); the agent is denied and recovers | lab-4.md l.218–228; slide `lab4-scoping` ("tries to access... gets denied") | Data: `patient_005.json:1155`. Denial: `tools.py:_check_access`. The text hedges ("may try"); the slide states it as fact. Not verified to happen | Simple | Orchestrate trace would show the tool call. Without scoping, the IBM agent could read Patricia's full record | None (untested; with a median of 1 tool call per run the attempt is unlikely to show up) |
| 17 | Observe the denial in the Langfuse trace | lab-4.md l.220 | Langfuse handler `agent.py:155–163`. The denial is a tool return value, visible as tool output | Simple | Orchestrate traces show tool I/O | Verified for traces in general; the denial case is None |
| 18 | "In production, log the denial silently to Langfuse" | lab-4.md l.232 | text only (code uses `logger.warning`, `tools.py:35`) | n/a | No custom spans on Orchestrate | None (not possible: no custom spans) |
| 19 | Concern stability: existing concerns are injected with "reuse the SAME id" instructions | lab-4.md l.113–127; slide `lab4-scoping` | `agent.py:primary_agent_node` l.137–147 (about 10 lines) + `run.py:27–30` | Simple: prompt text plus upsert | Same block added to IBM `lab1/agent/agent.py` message/instructions | None (feasible but not built) |
| 20 | Running twice builds on prior work; omitted concerns stay | lab-4.md l.127, l.240 | upsert `store.py:107–160`; JSON `_json_save_concerns` l.245 | Simple | Local store upsert | None |
| 21 | Downstream systems can rely on stable concern IDs | slide `lab4-scoping`; lab-4.md l.242 | text only. ID reuse is left to the LLM; lab-4.md l.253 admits "usually" | n/a | n/a | Reframed (the slide overstates it) |
| 22 | Sharing is binary; read-only vs read-write is future work | lab-4.md l.252 | **As implemented, a share is read-write.** The `FOR ALL` policy lets the recipient UPDATE. `get_concerns` passes shared concerns to the recipient's agent as "your previous runs", so a re-run can upsert over the owner's concern by ID (code trace, not tested) | n/a | none | None |
| 23 | Input hardening is still needed against adversarial content in the authorized patient's data | lab-4.md l.251 | text only | n/a | Orchestrate Content Guardrails (jailbreak/HAP) | Built-unverified (exist on the instance, untested) |
| 24 | Structured output makes deterministic reconciliation and granular sharing easier | lab-4.md l.248, 253 | text only | n/a | Pydantic validation in IBM `agent.py` | Reframed (structured output itself is Verified, 24/24 after retry) |
| 25 | Trace visibility needs its own RBAC (Langfuse RBAC) | lab-4.md l.254; slide `lab4-production` | text only | n/a | Orchestrate traces are visible tenant-wide and hold raw PII | Verified as a problem: the IBM setup demonstrates the gap |
| 26 | Lab 4 = Governance phase of the ADLC | lab-4.md l.12 | text only | n/a | watsonx.governance | None (nothing verified; data_marts returns 403) |
| 27 | Wrap-up: "Lab 4: Postgres RLS + scoped tools"; "Secure at the infrastructure layer, not just the prompt" | slides `wrap-up-summary`, `responsible-by-design` | — | n/a | — | Reframed (scoped tools do not exist on IBM) |
| 28 | Lab 4 still works without Docker (JSON fallback: stability and tool scoping work) | lab-4.md l.84–85 | `store.py` fallback; `DATABASE_URL` unset | Simple | — | No: the lab4 agent cannot run on IBM at all (no allowed LLM provider in `app/llm.py`) |

## 2. Exercises (pre-change) and whether the IBM edition can run them

| Step | What the student did | IBM can run it? |
|---|---|---|
| Setup | `docker compose up -d`; `psql` shows 3 providers; `uv sync --all-extras`; run streamlit + `uvicorn lab4.agent.api` | **Partly.** Postgres and psql run locally, and the IBM prerequisites still list Docker for Lab 4. The lab4 agent API starts, but `check_llm_config` and runs need Gemini, OpenAI or Anthropic, which are not allowed. |
| 1 | Run the agent as Dr. Kim; `psql` shows `provider_id='dr_kim'` | **No.** The lab4 agent (LangGraph + critic + Langfuse) is not converted to Orchestrate. |
| 2 | Switch the role dropdown to Rachel; the patient list shrinks and concerns are empty; read the RLS policy | **Partly.** The UI dropdown and the RLS read would work against local Postgres. The concerns only come from Step 1, so the demo works only if concerns are seeded by hand-written SQL (none exists). |
| 3 | Run as Rachel on patient-001; `psql` shows two concern sets | **No** (same reason as Step 1). |
| 4 | Share a concern; Rachel sees the "Shared by" badge; `psql` on `shared_concerns` | **Partly.** UI, API and DB work without an LLM, but there are no concerns to share unless seeded. |
| 5 | Run Elena (patient-005); look in the Langfuse trace for the denied tool call | **No.** There is no scoped tool on Orchestrate and no Langfuse. On the IBM Lab 1 agent the same prompt would hit an unscoped `get_patient_record`, which is untested. |
| 6 | Re-run the same patient; concerns and IDs stay stable | **No.** IBM `lab1/agent/agent.py` does not inject existing concerns. |

The decided reframe (RLS as discussion with no exercise) removes Steps 1–4. Steps 5–6 are not covered by that decision and currently have no IBM path.

## 3. Simplicity check

**What the student was pointed at pre-change** (lab-4.md l.95, 105, 115, 157):
- `lab4/agent/store.py`: 351 lines
- `lab4/agent/tools.py`: 144 lines
- `lab4/agent/agent.py`: 298 lines, of which the stability part is l.137–147
- `lab4/db/init.sql`: 91 lines

That is 884 lines in total. The lines that carry the teaching are about 50:
- the RLS policy: 9 lines
- `set_config`: 1 line
- `_check_access` plus the factory signature: about 15 lines
- the existing-concerns prompt block: about 10 lines
- the `ON CONFLICT` upsert: about 15 lines

**What made it simple:**
- Each guarantee was one local construct the student could read in one screen: a SQL policy, a Python closure, a prompt string.
- Everything ran on the laptop.
- Identity was a single module global (`api.py:60`).

It was not simple everywhere:
- `store.py` is padded by the JSON fallback and the connection pool.
- `agent.py` carries the full Lab 3 critic/grounding graph.
- The run needed 3 processes (streamlit, the lab4 API, Docker Postgres), plus the Langfuse stack for Step 5.

**What the IBM version of each piece would need:**
- **Tool scoping:** Orchestrate tools are static uploaded modules (`lab1/agent/tools.py` must be self-contained), so the closure factory cannot carry over. It would need:
  - an Orchestrate context variable carrying the authorized patient ID, set per run by the local client
  - a check inside each `@tool` that reads that variable
  - a redeploy through `deploy.py` per seat

  Context variables are untested. Moving parts added: the context-variable API, deploy, and a per-run variable injection in `agent.py`.
- **Concern stability:** about 10 lines added to IBM `lab1/agent/agent.py` (put existing concerns into the run message) plus an upsert in the local store. This is the cheapest piece to port, and it is not built.
- **RLS / sharing:** stays local Postgres. It is fully decoupled from Orchestrate, but its concerns depend on an agent run, so the demo needs either a seeding script or a converted lab4 agent.
- **Identity:** on IBM it is the tenant header `X-Tenant`, which is self-asserted and set from the key-value connection. This is structurally the same weakness the `lab4-production` slide describes, so it is usable as a discussion example.

## 4. Top gaps (ordered for a 2-hour workshop)

1. **The Lab 4 docs and slides in the IBM edition are an unmodified copy of the OSS lab.** The IBM `lab-4.md` is identical, and the slides still say "Postgres RLS + scoped tools". Every step tells students to run `lab4.agent.api` against an LLM provider they are not allowed to use. Nothing in Lab 4 runs end-to-end on IBM.
2. **Tool scoping and the Elena/Patricia injection test have no IBM implementation, and the IBM Lab 1 agent is the unscoped baseline.** This is the one Lab 4 claim about agent behavior (the slide says "gets denied"). Context variables are untested.
3. **The claim "cannot pull clinical data for unauthorized patients" is false even pre-change.** `list_patients` returns every patient's active conditions (`app/api.py:90`) and `get_inbox` returns every patient's message subjects. The same tool exists on IBM. Fix the wording or the tool, whichever edition ships.
4. **Concern stability is claimed on the slides but not built on IBM.** It is a small port (prompt block plus upsert). The slide also overstates "know they'll persist", which lab-4.md l.253 contradicts.
5. **The "Governance" framing and trace RBAC point to watsonx.governance, which has nothing verified.** Orchestrate traces are tenant-wide and hold raw PII. That makes the trace-RBAC point a real demonstrable problem, but nothing on IBM addresses it. Separately, the pre-change sharing and role code has two issues the reframed discussion should not repeat as fact:
   - A share grants write access, not just read (`FOR ALL` policy).
   - The patient restriction by role is a UI-only filter.