# Lab 2: Observability

**Duration:** ~20 minutes

???+ abstract "What You'll Add"
    The naive agent from Lab 1 is a black box — you can see its output (concerns), but not how it got there. Which tools did it call? What data did it see? How long did each step take? How much did it cost?

    In this lab you'll instrument the agent with **Langfuse**, an open-source LLM observability platform. You'll see every decision the agent makes — and then figure out what you can make better.

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
- [x] Instrument a LangGraph agent with Langfuse using three lines of code
- [x] See raw PHI in your traces and understand the risk
- [x] Implement client-side PII masking so sensitive data never reaches the trace store
- [x] Use the Langfuse UI to inspect agent behavior: tool calls, token usage, cost, latency

---

## Step 1: Start Langfuse

Langfuse runs locally via Docker Compose. All data stays on your machine — nothing is sent to the cloud.

```bash
cd ai-agents-workshop
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

That's it. The `CallbackHandler` hooks into LangChain's callback system, which LangGraph propagates to every LLM call and tool call in the ReAct loop.

---

## Step 3: Run the Agent

Start the system (you need two terminals):

```bash
# Terminal 1: Streamlit UI (auto-starts the EHR API)
uv run streamlit run app/ui.py --server.port 8501

# Terminal 2: Agent API (now using lab2)
uv run uvicorn lab2.agent.api:app --port 8001
```

Go to the UI at [http://localhost:8501](http://localhost:8501), select a patient, and click **Run Agent**.

---

## Step 4: Find the PHI Leak

After the agent finishes, go to the Langfuse UI at [http://localhost:3000](http://localhost:3000).

Click into **Traces** in the left sidebar. You should see a new trace. Click on it.

???+ warning "Look at the trace data"
    Expand the spans and look at the tool call inputs and outputs. You'll see patient names, dates of birth, phone numbers, email addresses, home addresses, insurance member IDs, and full medical records — all in plain text.

    All of this is now sitting in your Langfuse database. Anyone with access to this Langfuse instance can see it.

    In a real system under HIPAA, this would be a **reportable breach**. Your observability platform just became an unauthorized copy of the patient record.

The core point of this lab is learning to evaluate and improve your agent — but you can't do that responsibly if your instrumentation is leaking sensitive data.

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

When the mask function encounters a Pydantic model, it reads these annotations and replaces the values with placeholders (`<PII_REDACTED>`, `<PHI_REDACTED>`) — no named entity recognition (NER) needed. This is reliable even for short values like names where NER would struggle.

**Layer 2: NER-based detection for free text.** For string fields that aren't annotated (message bodies, clinical notes, LLM reasoning), we use [Microsoft Presidio](https://github.com/microsoft/presidio) via LangChain's `PresidioAnonymizer`. Presidio combines:

- **[spaCy](https://spacy.io/) NER**: identifies names, locations, and other contextual entities in natural language
- **Regex patterns**: catches structured PII — SSNs, email addresses, phone numbers
- **Custom recognizers**: we add one for insurance member IDs

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

### Enable masking

Toggle the **PII Masking** button at the bottom of the UI to **ON**, then run the agent again for the same patient.

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

Now that you have traces (ideally both masked and unmasked), let's walk through what Langfuse reveals about your agent. This is where observability goes from "nice to have" to essential.

### 7.1 Reading a trace

Click into **Traces** in the left sidebar and open your most recent trace. The trace view shows a **nested timeline** of everything that happened during the agent run:

- The **root span** covering the entire `process_patient` call
- **LLM generation spans** for each reasoning step — with token counts (input + output) and latency
- **Tool call spans** for each tool the agent invoked — with the full inputs and outputs
- **Cost** calculated automatically from model and token counts

Click on any span to see its details. This is the primary debugging interface — when something goes wrong in production, you trace the exact path the agent took.

### 7.2 The sequence of agent calls

Expand the trace and look at the **order** of spans. The ReAct loop is visible: the LLM reasons, decides to call a tool, receives the result, reasons again, calls another tool, and so on until it produces its final output.

Pay attention to:

- **How many LLM calls** the agent makes — each one is a decision point (and a cost)
- **Which tools** get called and in what order — is the agent's strategy sensible?
- **Whether the same tool** gets called multiple times — that might indicate confusion

???+ question "Think about this"
    Run the agent twice on the same patient and compare the traces. Does the agent call the same tools in the same order? If not, what does that tell you about the reliability of the agent's strategy?

### 7.3 The implicit summary problem

Look at the final LLM generation — the one that produces the structured concerns. Now compare it to the tool call outputs that preceded it.

The agent is performing an **implicit summarization**: it reads the full patient record via tool calls, then synthesizes that into structured concerns. Every layer of summarization is an opportunity for:

- **Hallucination**: the agent claims something that isn't in the data
- **Omission**: the agent misses something clinically important
- **Distortion**: the agent changes the meaning or severity of a finding

This is visible in the traces. Compare what the tools returned (ground truth) with what the agent concluded (the concerns). You can spot discrepancies by eye — in Lab 3, we'll automate this.

### 7.4 Too much data from simple tools

Look at the **output** of the `get_patient_record` tool call. It returns the *entire* patient record — demographics, conditions, medications, labs, encounters, messages, everything — in a single blob.

This creates two problems:

1. **For the agent**: it has to reason over a huge context window. More data means more tokens, more cost, more latency, and more opportunities to get confused or hallucinate.
2. **For tracing**: that entire patient record is now captured in your trace store. Even with masking, you're storing a lot of clinical data. In production, this has retention, compliance, and storage cost implications.

???+ question "Think about tool design"
    What if instead of one `get_patient_record` tool, you had separate tools for `get_demographics`, `get_conditions`, `get_medications`, `get_labs`, `get_messages`? The agent could request only what it needs. How would that change the traces? How would it change the cost? We'll revisit this in Lab 3.

### 7.5 The invisible user message

Click on the first LLM generation span and look at the **input messages**. You'll see a system prompt and a "user" message — something like *"Review the patient record for patient-001 and identify any concerns..."*

But the doctor never wrote that message. The patient never wrote it either. It's a **synthetic prompt** constructed by the agent's `process_patient` function. The "conversation" between user and assistant is happening entirely behind the scenes.

This is important to understand:

- The doctor sees *concerns* in the UI — they never see this prompt
- The prompt shapes everything the agent does — but it's invisible to the end user
- If the prompt is poorly written or biased, the doctor has no way to know

Traces make this visible — you can see the exact prompt in every trace.

### 7.6 Datasets and annotations

Langfuse has two built-in features for **human learning from agent behavior**:

- **Add to Dataset**: on any trace or span, click "Add to dataset" to save it as a labeled example. Over time, you build a collection of real agent behaviors — good and bad — that you can use for evaluation, fine-tuning, or training new team members.

- **Annotate**: add free-text notes or structured scores to any trace. When a clinician reviews the agent's output and spots a problem, they can annotate the trace with what went wrong. This creates a feedback loop from domain experts back to the engineering team.

Neither of these requires any code changes — they're built into the Langfuse UI. The traces you're generating right now could become the foundation of your evaluation dataset.

### 7.7 Scores and LLM-as-Judge (conceptual)

Langfuse supports **scores** — numeric or categorical ratings attached to traces. You can assign scores manually (human evaluation) or programmatically (automated evaluation).

One powerful pattern is **LLM-as-Judge**: use a second LLM to evaluate the first LLM's output. For example:

- *"Does this concern have evidence in the patient record, or is it hallucinated?"*
- *"Does the urgency level match the clinical severity?"*
- *"Did the agent overstep by making a diagnosis instead of flagging a concern?"*

We haven't implemented this yet — it's conceptual in this lab. But the traces you're capturing here are exactly the input you'd need. In Lab 3, we'll build evaluation checks that could feed scores back into Langfuse.

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
| ~~[Lab 1](lab-1.md)~~ | ~~No structure, no tools, just vibes~~ | ~~A ReAct agent with structured output~~ |
| ~~[Lab 2](lab-2.md)~~ | ~~No visibility into agent behavior~~ | ~~Observability: Langfuse tracing, PII masking, cost tracking~~ |
| **[Lab 3](lab-3.md)** | Unstable output, hallucinations, overstepping | Evaluation: output validation, grounding checks, guardrails |
| **[Lab 4](lab-4.md)** | Unrestricted data access | Security: scoped tools, access controls, audit trails |

???+ tip "Further reading"
    For a deep dive into agent observability governance — data retention, compliance frameworks (HIPAA, GDPR, SOC 2), and the full tooling landscape — see `docs/agent-observability-governance-reference.md` in this repository.
