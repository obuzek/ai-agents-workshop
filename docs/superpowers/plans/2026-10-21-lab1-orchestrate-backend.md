# Lab 1 on watsonx Orchestrate — status, findings, and plan

Branch: `ibm/orchestrate/lab-1` (worktree `.ai-worktrees/ibm-orchestrate-lab-1`). Not pushed.

## Decisions (2026-10-21)

1. **The real demo runs on the instructor's account**: Orchestrate hosts the agent, and Code Engine hosts the EHR API.
2. **Attendees get a simulation**: a local stand-in for the Orchestrate runs API that executes the same `agent.yaml` and `tools.py`.
3. **A working deploy script** brings up the full stack on a fresh IBM Cloud account, so attendees could reproduce it later.

Rejected alternatives:
- **Shared EHR instance for attendees.** UI replies mutate patient data, and "reply → re-run → the concern clears" needs per-attendee data.
- **Multitenant EHR API.** Too much plumbing.
- **Tunnels to attendee laptops.**
- **Attendees using Code Engine.** They don't have access to it.

## What works today (verified)

- **The EHR API on Code Engine** (`deploy/ehr-api/Dockerfile`) serves the synthetic patient data publicly.
- **`uv run python -m lab1.agent.deploy`** imports into the active `orchestrate` env:
  - a key-value connection (`lakeview_ehr.base_url`)
  - the 5 Python tools
  - the agent (`react_core`, `groq/openai/gpt-oss-120b`)
- **The local demo is unchanged for the user.** The path is Streamlit → `lab1.agent.api` → `process_patient()`, which calls the Orchestrate runs API (`POST /v1/orchestrate/runs`, then polls `GET /runs/{id}`) using an IBM Cloud API key → the result is validated as `PatientConcerns` → saved to the store → rendered in the UI.
- **Runs:** tested end to end on patients 001, 003, 004 and 006 through the UI and API, plus 6 direct runs. Each takes about 15–35 s.
- **The agent shows up in the Orchestrate UI** under Build → Global workspace. It's a draft, not live, and is editable there, with a preview chat. API runs work against the draft.
- **Per-attendee name prefixes work side by side.** Test: `@tool(name="alice_…")` plus an `alice_lakeview_inbox_agent`.

## Platform findings that matter for teaching

- **No enforced structured output on Orchestrate.**
  - `structured_output` is ignored by `react_core`, and also by `planner` on gpt-oss.
  - `llm_config.response_format` (both `json_schema` and `json_object`) makes runs fail with "I have encountered an error."
  - Current approach: `deploy.py` appends a JSON schema generated from `models.py` to the instructions; `agent.py` validates the reply and retries once in the same thread. 5 of 6 test runs were valid on the first try.
  - This contradicts `docs/content/lab-1.md:211` ("prompting for structure is fragile"), so that section needs reframing.
- **Tool cold start.** For roughly 30 s to 4 min after import or update, tools answer "We are configuring your tool in the background", and the agent then answers nonsense. Workshop timing needs to allow for it.
- **Run-to-run variance on gpt-oss-120b.** The agent often stops after one tool call; patient-001 got 0 concerns in one run and 2 in another, with real data returned both times.
- **Workspaces** are the real isolation mechanism, but creating one fails with `428 TRUSTED_PROFILE_ID is not configured`. An admin has to set up an IAM trusted profile first, and the steps aren't documented that I found. Trial and Essentials plans allow only 1 workspace.
- **Plans and pricing** (catalog list prices):
  - Trial (`lite`): free for 30 days, not offered in us-south.
  - Essentials: $530/mo.
  - Standard: $6,360/mo.
  - Premium: $18,000/mo.
- **The tenant shows limits for "LangGraph agents (10 live + 10 draft)"**, so Orchestrate may host LangGraph agents directly. If it does, the existing LangGraph Lab 1 code might deploy as-is, and `response_format` could work again. Unverified.
- **ADK version:** `react_core` needs ADK ≥ 2.19. The global `orchestrate` uv tool was upgraded from 2.8.0 to 2.19.0.

## TODO

- [ ] **Simulator.** A local server with `POST /v1/orchestrate/runs` and `GET /v1/orchestrate/runs/{id}` that loads `agent.yaml`, imports `tools.py` (the connection is read via the ADK env-var fallback `WXO_SECURITY_SCHEMA_lakeview_ehr=key_value_creds` and `WXO_CONNECTION_lakeview_ehr_base_url=http://localhost:8000`, unverified), and runs a ReAct loop with `app/llm.py`. Attendees then switch between it and the real instance just by changing `WXO_INSTANCE_URL`. Make it behave like Orchestrate: no constrained decoding, and return the same result shape.
- [ ] **Full deploy script.** Extend `deploy.py`, or add a wrapper, to also create or update the Code Engine app via `ibmcloud ce app create|update --build-source . --build-dockerfile deploy/ehr-api/Dockerfile`, read back its URL, then do the Orchestrate imports. It must be safe to re-run.
- [ ] **Durable demo instance.** The trial expires around 2026-11-20. Decide where the live demo runs if the workshop is later, then re-run the deploy script there.
- [ ] **Investigate the LangGraph-agents-on-Orchestrate option** (see findings).
- [ ] **Reframe the lab-1.md docs**: Orchestrate instead of LangGraph, the structured-output section, the cold-start note, and simulator vs. real instructions.
- [ ] **Optional `--prefix` on deploy.py**, if attendees ever deploy to a shared instance. Agent and tool names are global per tenant, so they'd overwrite each other otherwise.
- [ ] **Decide whether the Code Engine EHR API needs auth.** It's public and unauthenticated today, which is fine for synthetic data.

## Test resources to tear down

All in IBM Cloud account Developer Relations Prod, resource group Default:
- **Orchestrate Trial** `ai-workshop-test-orchestrate`, ca-tor, GUID `6a201280-24a7-41d8-a86a-243aada1a905`, CLI env `ai-workshop-test`
- **Code Engine project** `ai-workshop-test` (us-south), app `ehr-api` at https://ehr-api.2g7six4hbjvx.us-south.codeengine.appdomain.cloud
- **IBM Cloud API key** `ai-workshop-test-orchestrate`
