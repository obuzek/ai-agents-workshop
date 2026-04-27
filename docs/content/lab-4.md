# Lab 4: Securing Data Used By The Agent

**Duration:** ~25 minutes

???+ abstract "What You'll Secure"
    Labs 1-3 store all agent output in a single JSON file with no access control. Any code path can read or overwrite any patient's concerns. Lab 4 moves the concern store to Postgres with Row-Level Security, scopes agent tools to authorized patients, and makes concerns stable across runs.

---

## Where We Are in the ADLC

Lab 1 built the agent. Lab 2 made it observable. Lab 3 improved its reliability. Lab 4 is **Governance** — ensuring the agent's output is as protected as the data it reads.

The key insight: **agent-generated artifacts are sensitive data too.** The agent reads patient records and produces clinical concerns. Those concerns contain PHI. They need the same access control as the source data — and in a multi-provider practice, they need *more*, because each provider's agent may reach different conclusions about the same patient.

---

## Learning Objectives

By the end of this lab, you will:

- [x] Move agent output from a flat file to Postgres with Row-Level Security
- [x] Understand why access control belongs in the data layer, not the application layer
- [x] Scope agent tools to a single patient to prevent cross-patient data leakage
- [x] Test an adversarial prompt injection that tries to access another patient's data
- [x] Make concerns stable across agent runs (update by ID, not replace wholesale)
- [x] Share concerns between providers with explicit, auditable grants

---

## Setup

### Start Postgres

Lab 4 stores concerns in Postgres. Start it with Docker Compose:

```bash
docker compose up -d
```

Verify it's running:

```bash
docker compose exec postgres psql -U agent -d agent_store \
  -c "SELECT id, display_name, role FROM providers ORDER BY id;"
```

You should see:

```
      id       |    display_name     |        role
---------------+---------------------+---------------------
 dr_kim        | Dr. Sarah Kim, MD   | physician
 maria_gonzalez| Maria Gonzalez      | medical_assistant
 rachel_torres | Rachel Torres, NP   | nurse_practitioner
(3 rows)
```

### Install the Postgres driver

```bash
uv sync --all-extras
```

### Start the servers

You need three terminals for Lab 4:

**Terminal 1 — API server:**

```bash
uv run uvicorn app.api:app --reload --port 8000
```

**Terminal 2 — Agent API (with Postgres):**

```bash
uv run uvicorn lab4.agent.api:app --port 8001
```

**Terminal 3 — UI:**

```bash
uv run streamlit run app/ui.py --server.port 8501
```

---

## What Changed from Lab 3

Open the Lab 4 code side by side with Lab 3. Three things changed:

### 1. The store moved to Postgres

Open `lab4/agent/store.py`. Instead of `load_store()` / `save_store()` working on a flat JSON file, you'll see:

- `get_concerns(patient_id, provider_id)` — fetches concerns from Postgres, filtered by RLS
- `save_concerns(patient_id, provider_id, concerns)` — upserts: updates existing concern IDs, inserts new ones, leaves unmentioned concerns untouched
- `share_concern(concern_id, shared_with, shared_by)` — creates an explicit share grant

Every database operation calls `set_config('app.provider_id', ...)` on the connection. This is how the application tells Postgres "who's asking" — and Postgres uses it to enforce RLS policies.

### 2. Tools are scoped to one patient

Open `lab4/agent/tools.py`. Instead of a flat list of tools, there's a factory:

```python
def create_tools(authorized_patient_id: str) -> list:
```

Every data-access tool checks `patient_id == authorized_patient_id` before making the API call. If the agent tries to access another patient's data, it gets an explicit denial.

### 3. Concerns are stable across runs

Open `lab4/agent/agent.py` and look at `primary_agent_node`. The agent receives its previous concerns as context:

```
EXISTING CONCERNS (from your previous runs):
[... JSON list of current concerns with IDs ...]

INSTRUCTIONS FOR EXISTING CONCERNS:
- If an existing concern is still valid, include it with the SAME id.
- If you find a new concern, create it with a new unique id.
- Concerns you omit will remain in the store unchanged.
```

This means running the agent twice doesn't wipe out previous work — it builds on it.

---

## Step 1: Run the Agent as Dr. Kim

In the UI, you should see an **Active Role** dropdown at the top of the page, above the patient list. It should show "Dr. Sarah Kim, MD."

Pick a patient and click **Run Agent**. Watch the concerns appear.

Now open a `psql` session and verify the concerns are in the database:

```bash
docker compose exec postgres psql -U agent -d agent_store \
  -c "SELECT id, title, provider_id FROM concerns LIMIT 5;"
```

Every concern has `provider_id = 'dr_kim'` — because Dr. Kim's agent created them.

---

## Step 2: See RLS in Action

Switch the role to **Rachel Torres, NP** using the dropdown.

Two things happen:

1. The **patient list** shrinks — Rachel Torres only has access to patients 1-6
2. The **concerns panel** is empty — even for patients Rachel Torres can access

Why? Because RLS. Look at the policy in `lab4/db/init.sql`:

```sql
CREATE POLICY provider_concern_access ON concerns
    FOR ALL
    USING (
        provider_id = current_setting('app.provider_id', true)
        OR id IN (
            SELECT concern_id FROM shared_concerns
            WHERE shared_with = current_setting('app.provider_id', true)
        )
    );
```

Rachel Torres can only see concerns where `provider_id = 'rachel_torres'` or the concern was explicitly shared with them. Dr. Kim's concerns are invisible — **even though they're in the same table, for the same patients.**

This is the teaching moment: **a bug in your Python code cannot leak Dr. Kim's concerns to Rachel Torres.** The database prevents it. Application-layer access control can always be bypassed by a code bug. Database-layer access control cannot.

???+ question "What if we just filtered in Python?"
    You could write `WHERE provider_id = :provider_id` in every query. But:

    - A developer could forget the filter in one query
    - An ORM might load related objects without the filter
    - A debugging endpoint might bypass the filter
    - A migration might drop the filter

    With RLS, the policy applies to **every query**, including ones you haven't written yet. The database is the last line of defense.

---

## Step 3: Run the Agent as Rachel Torres

While still in the Rachel Torres role, run the agent on one of the available patients (1-6).

Rachel Torres's agent generates its own concerns — independently of Dr. Kim's. Check the database:

```bash
docker compose exec postgres psql -U agent -d agent_store \
  -c "SELECT id, title, provider_id FROM concerns WHERE patient_id = 'patient-001' ORDER BY provider_id;"
```

You'll see two sets of concerns for the same patient — one from `dr_kim`, one from `rachel_torres`. The agent is a **delegate** — its output inherits the identity of whoever invoked it.

---

## Step 4: Share a Concern

Switch back to Dr. Kim. Find a concern and click **Share** → select Rachel Torres.

Now switch to Rachel Torres. The shared concern appears alongside Rachel Torres's own concerns, with a "Shared by Dr. Sarah Kim, MD" label.

Check the database:

```bash
docker compose exec postgres psql -U agent -d agent_store \
  -c "SELECT sc.concern_id, p.display_name as shared_by, sc.shared_with
      FROM shared_concerns sc JOIN providers p ON sc.shared_by = p.id;"
```

Sharing is an **explicit, auditable grant**. The default is isolation. Access requires a deliberate action — and that action is logged.

---

## Step 5: Test Tool Scoping

Open patient Elena Vasquez (patient-005) and run the agent. Look at the Langfuse trace for this run.

Elena's messages include one that mentions her neighbor Patricia Kowalski (patient-001) and asks the doctor to check if they should worry about the same thing. Watch the trace to see what happens:

1. The agent reads Elena's messages and sees the mention of Patricia Kowalski
2. The agent calls `list_patients()` — this succeeds (the clinic directory is unscoped)
3. The agent may try to call a data tool for Patricia's patient ID — and gets: `"Access denied: you are only authorized to access patient patient-005"`
4. The agent recovers and explains it can't access other patients' records

This is **least-privilege tool scoping**. The agent can see who's in the practice but cannot pull clinical data for unauthorized patients.

???+ note "In production"
    In a production system, you'd log the denial to Langfuse silently rather than returning it as a tool response. The doctor doesn't need to see that the agent tried and failed — but the security team does.

---

## Step 6: Verify Concern Stability

Run the agent again for the same patient as Dr. Kim. Compare the concern IDs before and after:

```bash
docker compose exec postgres psql -U agent -d agent_store \
  -c "SELECT id, title, last_updated FROM concerns
      WHERE patient_id = 'patient-001' AND provider_id = 'dr_kim'
      ORDER BY id;"
```

Concerns with the same underlying issue keep their IDs — the `last_updated` timestamp changes but the `id` is stable. New concerns get new IDs. Old concerns that the agent didn't mention are left untouched.

This matters because downstream systems (notification triggers, audit logs, care coordination) can reference concern IDs and know they're stable.

---

## What's Still Broken

Lab 4 addresses data isolation and tool scoping, but it's not a complete security solution:

- **No real authentication.** Roles are simulated with a dropdown. A production system needs JWT tokens or OAuth, with the identity flowing from the auth layer to the Postgres session variable.
- **The agent can still be manipulated.** Tool scoping prevents cross-patient data access, but the agent could still be influenced by adversarial content within the authorized patient's data. Defense-in-depth (output validation from Lab 3 + input sanitization) is needed.
- **Sharing is binary.** You can share a concern or not. A real system might need time-limited shares, read-only vs. read-write, or approval workflows.
- **Concern stability depends on the LLM.** The agent *usually* reuses existing IDs, but it's not guaranteed. A production system would add a deterministic reconciliation step after the agent runs.
- **Traces aren't scoped by provider.** We secured agent *output* with RLS, but the Langfuse traces from Lab 2 are still visible to anyone with access to the Langfuse instance. In production, use [Langfuse's RBAC](https://langfuse.com/docs/rbac) to scope trace visibility per provider — the same identity that flows into `app.provider_id` should determine who can see which traces.

---

## What Did We Learn?

| Principle | Implementation |
|---|---|
| **Access control in the data layer** | Postgres RLS — the database enforces isolation even if the application has bugs |
| **Agent output inherits identity** | Concerns are scoped to the provider who ran the agent |
| **Default deny, explicit grant** | RLS blocks all access; sharing creates targeted exceptions |
| **Least-privilege tools** | Agent can only access the patient it's authorized for |
| **Stable artifacts** | Concerns persist across runs — update by ID, not replace wholesale |

---

## Workshop Complete

| Lab | Problem | Solution |
|---|---|---|
| ~~[Lab 1](lab-1.md)~~ | ~~No structure, no tools, just vibes~~ | ~~A ReAct agent with structured output~~ |
| ~~[Lab 2](lab-2.md)~~ | ~~No visibility into agent behavior~~ | ~~Observability: Langfuse tracing, PII masking, cost tracking~~ |
| ~~[Lab 3](lab-3.md)~~ | ~~Unstable output, hallucinations, overstepping~~ | ~~Evaluation: output validation, grounding checks, guardrails~~ |
| ~~[Lab 4](lab-4.md)~~ | ~~Unrestricted data access, no isolation~~ | ~~Security: Postgres RLS, scoped tools, concern sharing~~ |

???+ success "You're done!"
    You've built an agent, made it observable, improved its reliability, and hardened it against data attacks. Check out the [Additional Resources](./resources.md) for further reading and frameworks to take this further.
