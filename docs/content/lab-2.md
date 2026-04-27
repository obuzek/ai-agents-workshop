# Lab 2: Observability

**Duration:** ~20 minutes

???+ abstract "What You'll Add"
    The naive agent from Lab 1 is a black box — you can see its output (concerns), but not how it got there. Which tools did it call? What data did it see? How long did each step take? How much did it cost?

    In this lab you'll instrument the agent with **Langfuse**, an open-source LLM observability platform. You'll see every decision the agent makes — and then you'll discover that your traces contain patient PHI, and fix it.

---

## Why Observability Matters for Agents

Traditional software observability tracks HTTP status codes, latency histograms, and error rates — metadata about what happened. Agent observability is fundamentally different because you need to capture the **content** of what was processed: the full prompts, tool call arguments, model outputs, and reasoning chain.

This creates a tension: the richer your traces, the more useful they are for debugging — but the more likely they are to contain sensitive data. Your trace store becomes a **secondary repository of sensitive data** that needs its own governance posture.

???+ example "The trace data problem"
    When the agent calls `get_patient_record("patient-001")`, the trace captures:

    - **Input**: the patient ID
    - **Output**: the entire patient record — name, DOB, medications, lab results, messages

    That output is now sitting in your trace store. If anyone with access to your observability platform can see it, you've created a PHI leak that has nothing to do with your agent's behavior.

In the slides before this lab, we covered the **"What to Log" framework**:

| Log Freely | Log With Masking | Do Not Log |
|---|---|---|
| Latency, token counts, cost | Summarized user intent | Raw credentials / secrets |
| Model name, temperature, params | Redacted inputs / outputs | Full PHI in healthcare contexts |
| Tool call names, success/fail | Error messages (scrubbed) | Internal API keys in tool args |
| Trace structure / spans | Session metadata | Unmasked PII |

This lab puts that framework into practice.

---

## Learning Objectives

By the end of this lab, you will:

- [x] Understand why agent observability requires different tooling than traditional software monitoring
- [x] Know the difference between traces, spans, and the data they capture
- [ ] Instrument a LangGraph agent with Langfuse using three lines of code
- [ ] See raw PHI in your traces and understand the risk
- [ ] Implement client-side PII masking so sensitive data never reaches the trace store
- [ ] Use the Langfuse UI to inspect agent behavior: tool calls, token usage, cost, latency

---

## Step 1: Start Langfuse

Langfuse runs locally via Docker Compose. All data stays on your machine — nothing is sent to the cloud.

```bash
docker compose -f docker-compose.langfuse.yml up -d
```

This starts 6 containers: Langfuse web UI, a background worker, Postgres, Clickhouse, Redis, and MinIO (object storage). The first run pulls images and takes ~30 seconds.

Open [http://localhost:3000](http://localhost:3000) and log in:

- **Email**: `workshop@example.com`
- **Password**: `workshop`

You should see an empty project called **"Lab 2 Observability"**. No traces yet — we'll generate some in the next steps.

???+ tip "Pre-configured credentials"
    The Docker Compose file uses Langfuse's [headless initialization](https://langfuse.com/self-hosting/administration/headless-initialization) to pre-seed an organization, project, user, and API keys. You don't need to create anything manually.

    The API keys (`pk-lf-workshop` / `sk-lf-workshop`) are already set as defaults in the agent code.

---

## Step 2: Understand the Instrumentation

Open `lab2/agent/agent.py` and compare it to `lab1/agent/agent.py`. The diff is small:

```python
# --- NEW IN LAB 2 ---
from lab2.agent.observability import create_langfuse_handler

_langfuse_handler = create_langfuse_handler()
```

And in `process_patient()`:

```python
result = _agent.invoke(
    {"messages": [{"role": "user", "content": user_message}]},
    config={
        "callbacks": [_langfuse_handler],
        "metadata": {
            "langfuse_session_id": f"patient-review-{patient_id}",
            "langfuse_tags": ["lab2", patient_id],
        },
    },
)
```

That's it. The `CallbackHandler` hooks into LangChain's callback system, which LangGraph propagates to every LLM call and tool call in the ReAct loop. No manual instrumentation of individual steps needed.

???+ question "Think about this"
    The `config` dict also passes `metadata` with a session ID and tags. Why might you want to tag traces with the patient ID? What would you search for in the Langfuse UI after a doctor reports a problem with a specific patient's concerns?

---

## Step 3: Run the Agent (Without Masking)

First, let's see what happens when we trace **without** PII masking. We'll temporarily disable it.

Open `lab2/agent/observability/masking.py` and find the `create_langfuse_handler` function. Temporarily comment out the mask:

```python
def create_langfuse_handler(**kwargs) -> CallbackHandler:
    from langfuse import Langfuse

    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-lf-workshop")
    os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-lf-workshop")
    os.environ.setdefault("LANGFUSE_HOST", "http://localhost:3000")

    # Langfuse(mask=mask_pii)    # <-- comment this out temporarily
    Langfuse()                    # <-- use this instead

    return CallbackHandler(**kwargs)
```

Now start the system (you need three terminals, just like Lab 1):

```bash
# Terminal 1: Main API
uv run uvicorn app.api:app --port 8000

# Terminal 2: Streamlit UI
uv run streamlit run app/ui.py --server.port 8501

# Terminal 3: Agent API (now using lab2)
uv run uvicorn lab2.agent.api:app --port 8001
```

Go to the UI at [http://localhost:8501](http://localhost:8501), select a patient, and click **Run Agent**.

---

## Step 4: Find the PHI Leak

After the agent finishes, go to the Langfuse UI at [http://localhost:3000](http://localhost:3000).

Click into **Traces** in the left sidebar. You should see a new trace. Click on it.

???+ warning "Look at the trace data"
    Expand the spans and look at the tool call inputs and outputs. You'll see:

    - **Patient names** in full (e.g., "Patricia Kowalski")
    - **Dates of birth** (e.g., "1953-11-14")
    - **Phone numbers** (e.g., "847-555-0143")
    - **Email addresses** (e.g., "pat.kowalski@gmail.com")
    - **Home addresses** (e.g., "482 Birch Lane, Evanston, IL 60201")
    - **Insurance member IDs** (e.g., "1EG4-TE5-MK72")
    - **Full medical records** — conditions, medications, lab values

    All of this is now sitting in your Langfuse database. Anyone with access to this Langfuse instance can see it.

    In a real system under HIPAA, this would be a **reportable breach**. Your observability platform just became an unauthorized copy of the patient record.

This is the core teaching point of Lab 2: **observability must not become a data leak.** The solution is to filter sensitive data *before* it ever reaches the trace store.

---

## Step 5: Implement PII Masking

Now let's fix it. Open `lab2/agent/observability/masking.py`.

The `mask_pii` function is the client-side filter that Langfuse applies to all trace data — inputs, outputs, and metadata — *before* any data leaves the process. This is the approach recommended by the [Langfuse documentation](https://langfuse.com/docs/observability/features/masking) and is the strongest guarantee that sensitive data never reaches your trace store.

### How it works

Our masking uses two layers of defense:

**Layer 1: Field-level redaction from data model annotations.** Our Pydantic data models annotate which fields contain PII or PHI:

```python
# In app/models.py
class Demographics(BaseModel):
    name: Name
    birth_date: str = _phi(default="", alias="birthDate")    # PHI — clinical identifier
    phone: str = _pii(default="")                             # PII — contact info
    email: str = _pii(default="")                             # PII — contact info
```

When the mask function encounters a Pydantic model, it reads these annotations and replaces the values with placeholders (`<PII_REDACTED>`, `<PHI_REDACTED>`) — no NER needed. This is reliable even for short values like names where NER would struggle.

**Layer 2: NER-based detection for free text.** For string fields that aren't annotated (message bodies, clinical notes, LLM reasoning), we use [Microsoft Presidio](https://github.com/microsoft/presidio) via LangChain's `PresidioAnonymizer`. Presidio combines:

- **spaCy NER**: identifies names, locations, and other contextual entities in natural language
- **Regex patterns**: catches structured PII — SSNs, email addresses, phone numbers
- **Custom recognizers**: we add one for insurance member IDs (e.g., `1EG4-TE5-MK72`)

```python
from langchain_experimental.data_anonymizer import PresidioAnonymizer

_anonymizer = PresidioAnonymizer(
    analyzed_fields=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN",
                     "LOCATION", "DATE_TIME", "CREDIT_CARD", "URL"],
    add_default_faker_operators=False,  # Use <TYPE> placeholders, not fake values
)
```

### Why two layers?

NER is excellent at finding names embedded in paragraphs ("Dear Dr. Kim, I've been having trouble with..."). But it's unreliable on short strings — a field containing just `"Patricia Kowalski"` might not be confidently classified as a person name depending on context. By annotating the data model, we tell the masking layer *exactly* which fields are sensitive, and reserve NER for the free-text fields where it excels.

???+ question "Think about coverage"
    Even with two layers, no PII detection is perfect. What happens if:

    - A rare name isn't in spaCy's training data?
    - A medical condition is so specific it effectively identifies the patient?
    - The LLM paraphrases PII in a way that changes its surface form?
    - A first name appears alone in the LLM's reasoning text?

    These are real production concerns. In a real healthcare deployment, you would layer additional defenses: dedicated PHI detection models, regular audits of your trace store, and potentially routing sensitive data through a **governed data platform** (like [IBM watsonx.data](https://www.ibm.com/products/watsonx-data)) that enforces data governance policies at the storage layer — so even if your masking pipeline misses something, the data store itself has controls.

    For this workshop, our two-layer approach demonstrates the pattern. Production systems need more.

### Re-enable masking

Undo the change from Step 3 — restore the mask in `create_langfuse_handler`:

```python
Langfuse(mask=mask_pii)
```

Restart the agent API (Terminal 3), then run the agent again for the same patient.

---

## Step 6: Verify the Fix

Go back to Langfuse at [http://localhost:3000](http://localhost:3000). Find the new trace (the most recent one).

Expand the spans again. In the **tool call outputs**, you should see:

- `<PII_REDACTED>` where patient names, emails, and phone numbers used to be
- `<PHI_REDACTED>` where dates of birth and insurance member IDs were
- `<PERSON>`, `<PHONE_NUMBER>`, `<LOCATION>` where Presidio caught PII in free-text fields

The trace structure is preserved — you can still see which tools were called, in what order, how long each step took, and how many tokens were used. The clinical data (conditions, medications, lab values) is still visible because it's useful for debugging — only the identifying information is redacted.

???+ tip "Compare the two traces"
    With both the masked and unmasked traces in Langfuse, you can directly compare them. The unmasked trace is a cautionary tale; the masked one is the pattern you'd use in production.

???+ warning "You may still see some names"
    Look carefully at the LLM generation spans. You may see the patient's first name in the model's reasoning text — Presidio's NER doesn't always catch standalone first names. This is a known limitation of classical entity extraction. In a production system, you'd add additional defenses (see the "Think about coverage" callout above).

---

## Step 7: Explore the Langfuse UI

Now that you have traces, spend a few minutes exploring what Langfuse gives you:

### Trace timeline

Click into a trace and look at the nested spans. You should see:

- The **root span** covering the entire `process_patient` call
- **LLM generation spans** for each reasoning step — with token counts (input + output)
- **Tool call spans** for each tool the agent invoked — with inputs and outputs (now masked)
- **Latency** for each span, so you can see where time is spent

### Cost tracking

Langfuse automatically calculates cost based on the model and token counts. Look at the cost column — this tells you what each agent run costs. For a workshop with synthetic data this is small, but in production with 12 patients running multiple times per day, it adds up.

???+ question "Think about cost"
    If each patient review costs ~$0.10 in API calls, and you run the agent 3 times per day for 12 patients, that's $3.60/day or ~$100/month for a single practice. What if you have 100 practices? What if the agent re-runs unnecessarily because concerns aren't stable (a Lab 1 limitation)?

    This is why cost tracking in traces matters — you need visibility before you can optimize.

### Filtering and search

Use the sidebar filters to search by:

- **Tags**: find all traces for a specific patient (e.g., `patient-001`)
- **Session**: group traces by patient review session
- **Time range**: compare runs over time

---

## What's Not Covered Here

This lab focuses on **tracing** — capturing and inspecting individual agent runs. There are other observability signals we're not building today:

**Structured logging** (operational monitoring): In production, you'd also emit structured log events for aggregate monitoring — "agent run completed," "error rate," "runs per hour." These feed into your existing ops stack (Datadog, Splunk, Grafana). This is part of the **Operate and Monitor** phase of the ADLC — the runtime optimization loop we discussed in the slides. It's closer to traditional software engineering than to agent-specific work, so we're focusing our time on the agent-specific parts.

**Metrics and alerting**: p95 latency, token usage trends, error rates. Langfuse has some of this built in; for production you'd connect to your existing monitoring infrastructure.

**Evaluation**: Are the agent's concerns actually correct? That's Lab 3.

---

## What's Working

Let's take stock of what we've added:

**Full visibility into agent behavior.** Every LLM call, tool call, and decision step is captured with timing and token counts. When something goes wrong, you can trace the exact path the agent took.

**Two-layer PII/PHI masking.** Pydantic model annotations handle structured data (names, DOBs, contact info) reliably regardless of string length. Presidio NER catches PII embedded in free-text fields. Both run client-side before data leaves the process — the strongest guarantee available at this layer.

**Cost attribution per run.** You can see exactly what each agent run costs and where the tokens are spent. This is essential for understanding whether your agent is economically viable.

**Zero changes to agent behavior.** The agent produces the same output as Lab 1. We added three lines of integration code. Observability is additive — it shouldn't change what the system does.

---

## What's Still Broken

Observability lets us *see* the problems from Lab 1 more clearly, but it doesn't fix them:

### The agent still hallucinates

With traces, you can now *see* when the agent fabricates evidence — compare the tool call outputs (what the data actually says) with the agent's final concerns (what it claims). But there's nothing in place to catch this automatically.

### Concerns are still unstable

Run the agent twice on the same patient and compare the traces. The agent may call different tools in different orders and produce different concerns. Traces make this visible, but they don't stabilize it.

### The agent still oversteps

Look at the structured output in the trace. Despite the system prompt saying "do not make clinical recommendations," you'll likely see the agent suggesting diagnoses or treatments. The trace makes this auditable — but not preventable.

---

## Up Next

Now that you can see what the agent is doing, the next step is to make it do the right things more reliably.

| Lab | Problem | Solution |
|---|---|---|
| ~~Lab 2~~ | ~~No visibility into agent behavior~~ | ~~Observability: Langfuse tracing, PII masking, cost tracking~~ |
| **Lab 3** | Unstable output, hallucinations, overstepping | Evaluation: output validation, grounding checks, guardrails |
| **Lab 4** | Unrestricted data access | Security: scoped tools, access controls, audit trails |

???+ tip "Further reading"
    For a deep dive into agent observability governance — data retention, compliance frameworks (HIPAA, GDPR, SOC 2), and the full tooling landscape — see `docs/agent-observability-governance-reference.md` in this repository.
