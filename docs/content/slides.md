---
revealjs:
  presentation: true
---

<!-- .slide: id="title" data-background-image="../images/odsc-title.png" data-background-size="contain" data-background-color="#000" -->

---

<!-- .slide: id="section-agents" data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Section 1</p>

# The World of Agents

</div>

Note: Welcome!

When I first submitted this talk several months back, the world of agents was quite different. At that time, people were talking deeply about agent architectures, and "how to build an agent" was still esoteric for most people.

---

<!-- .slide: id="sudo-make-agent" -->

<p style="text-align: center">
<img src="https://imgs.xkcd.com/comics/sandwich.png"/></br><code>$ sudo make me an agent</code></p>

Note: Since that time, the world changed. Between November and February, coding models took a massive leap forward, and now - the easiest way to make an agent is just to tell a coding model to make you one.

---

<!-- .slide: id="what-is-an-agent" -->

## What is an agent?

<div style="display: flex; gap: 2em">
<div style="flex: 1">
<ul><li>Prompt</li>
<li>Tools</li>
<li>Data</li>
<li>Reasoning</li>
<li>Repeat</li>
</ul>
</div>
  <div style="flex: 1">
  <h3>ReAct Loop</h3>
  <svg viewBox="0 0 320 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-height:200px;margin-top:0.5em">
    <defs>
      <marker id="react-arr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
        <polygon points="0 0, 10 3.5, 0 7" fill="#888"/>
      </marker>
    </defs>
    <line x1="183" y1="87" x2="225" y2="153" stroke="#888" stroke-width="2" marker-end="url(#react-arr)"/>
    <line x1="204" y1="190" x2="116" y2="190" stroke="#888" stroke-width="2" marker-end="url(#react-arr)"/>
    <line x1="95" y1="153" x2="137" y2="87" stroke="#888" stroke-width="2" marker-end="url(#react-arr)"/>
    <circle cx="160" cy="50" r="42" fill="#0f62fe"/>
    <text x="160" y="50" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="13" font-family="IBM Plex Sans, sans-serif">Observe</text>
    <circle cx="248" cy="190" r="42" fill="#0f62fe"/>
    <text x="248" y="190" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="13" font-family="IBM Plex Sans, sans-serif">Plan</text>
    <circle cx="72" cy="190" r="42" fill="#0f62fe"/>
    <text x="72" y="190" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="13" font-family="IBM Plex Sans, sans-serif">Act</text>
  </svg>
  </div>
</div>

Note: I think we're close to not needing this anymore! But just to levelset:

---

<!-- .slide: id="do-you-need-agent" -->

## Do You Even Need To Make An Agent?

<img src="../images/subagents-screenshot.png"/>

Note: In fact, it's even simpler than that: now, general purpose agents can write themselves subagents on the fly, based on nothing more than a couple words. And those agents can launch agents, and those agents can launch agents...

---

<!-- .slide: id="why-build-agent" -->

## Do You Even Need To Make An Agent?

### Why you might want to build an agent:

* You need to run a similar type of workflow over and over again
* You work on sensitive data that can't be dropped into a general purpose LLM
* You need to share your workflow with a large number of team members
* You need that workflow to run reliably and efficiently

Note: So that brings us here - to the problem space of _responsible_ AI agents.

---

<!-- .slide: id="why-were-here" -->

## Why We're Here

### Today You'll Learn:

1. How do you design an agent that needs to operate on sensitive data?
2. Given a user problem where your job is to build a tool that supports experts, how do you make sure you support instead of replacing their expertise?
3. Which tools are the right ones to get started with agents?

---

<!-- .slide: id="responsible-agent" -->

## What Does It Mean For An Agent To Be Responsible?

<div style="display: flex; gap: 2em">
<div style="flex: 1">
  <h3>Qualities of Responsibility</h3>
  <ul>
    <li><strong>Augments human intelligence</strong>: Reduces time spent completing tasks</li>
    <li><strong>Aligns with human values</strong>: Follows human values, ethical considerations, guidelines
   and policies - necessary in critical organizations</li>
    <li><strong>Robust</strong>: Behaves predictably in complex environments</li>
    <li><strong>Efficient</strong>: Doesn't waste computation achieving its goals</li>
    <li><strong>Private</strong>: Doesn't reveal information except to those who should have access</li>
    <li><strong>Explainable</strong>: Humans can reason about the agent's behavior</li>
  </ul>
</div>
<div style="flex: 1">
  <h3>Impacts to Consider</h3>
  <ul>
    <li><strong>Human Dignity</strong>: Workers should see AI as partners, not replacements for their skills</li>
    <li><strong>Human Agency</strong>: Agents should only make decisions that keep human critical thinking intact</li>
    <li><strong>Jobs</strong> Augmenting, instead of replacing, creates opportunities for more people to create new things</li>
    <li><strong>Environment</strong>: Computational efficiency matters</li>
  </ul>
</div>
</div>

<p class="push-bottom" style="text-align: right; font-size: 0.6em">source: <a href="https://www.ibm.com/granite/docs/resources/ai-agents-opportunities-risks-and-mitigations.pdf">AI Agents: Opportunities, Risks and Mitigations</a></p>

Note: We can frame this a few different ways.

---

<!-- .slide: id="responsible-agent-articles" -->

## What Does It Mean For An Agent To Be Responsible?

<div style="overflow: hidden; height: 600px; border: 1px solid rgba(255,255,255,0.2); border-radius: 4px;">
  <img src="../images/lee-2025-ai-critical-thinking.pdf.png"
       style="width: 100%; height: 100%; object-fit: cover; object-position: top; display: block;"/>
</div>

Note: This study from Lee et al. at CHI 2025 found that mechanizing routine tasks, and leaving exception handling to the user, actually makes the user's judgment worse since they're no longer practicing with regularity, and they are then less prepared when exceptions arise.

Users with AI access produced a less diverse set of outcomes for the same task — interpreted as deterioration of critical thinking

This has also long been a lesson of autopilot automation in aviation: The Air France disaster in 2009, where pilots couldn't fly a plane on autopilot. Now - pilots must hand-fly regularly to prevent skill erosion.

---

<!-- .slide: id="useful-agent" -->

## What Does It Mean For An Agent To Be Useful?

<div style="display: flex; gap: 2em">
<div style="flex: 1">
  <h3>Antipatterns</h3>
  <ul>
    <li><strong>Sparkle button</strong>: Implies "magic"; usually isn't</li>
    <li><strong>Unnecessarily broad chat</strong>: McDonald's doesn't need to generate Python code</li>
    <li><strong>Deterministic workflow made probabilistic</strong>: Simple workflows should stay simple</li>
    <li><strong>Limited, by accident</strong>: Hasn't thought through the user's actual needs</li>
  </ul>
</div>
<div style="flex: 1">
  <p/>
</div>
</div>

Note: Wearable app that generates charts for you, but wants you to do it in plain text instead of buttons.

A grammar checker that responds to your friends, replacing your relationships with them.

McDonald's chat, so unrestricted that it can write Python for you.

---

<!-- .slide: id="problem-statement"-->

### The Problem

Since the introduction of **EHR portals**, doctors are **overwhelmed with messages** from their patients. Sometimes the patients ask several questions in one message. Sometimes the messages are urgent. Responding to them comes on top of a doctor's patient load — and that means that **keeping up is exhausting**. But when patients don't get responses to their questions, they may let **important medical needs go un-handled**.

### The Question

Can we use an AI agent to support doctor-patient communication outside of appointments in a way that:

* preserves the doctor-patient relationship,
* enables the doctor to remain the expert, and
* reduces the cognitive load of keeping up with their inbox?

Note: Can we build an agent that does this, and still helps the doctors?

---

<!-- .slide: id="our-approach" -->

## Our Approach

The recipe for a responsible healthcare inbox agent:

* Never drafts for the doctor
* Never offers medical advice
* DOES help summarize information
* DOES help extract information
* DOES help surface information

---

<!-- .slide: id="our-approach-2" -->

## Our Approach

The UI:

<table style="font:1.2em">
<tr><td><h3>What</h3></td><td><h3>Why</h3></td></tr>
<tr><td>Skips the chatbox approach</td><td>Limits the possible workflows the agent enables</td></tr>
<tr><td>Backgrounds the agent</td><td>Prevents feedback loops on jailbreaking and prompt injection while still accomplishing our needs</td></tr>
</table>

Our agent will:
* Extract important points from messages and labs
* Raise those points in a structured way
* Expose them to the user without breaking confidentiality laws

<a href="http://localhost:8501">Our "Electronic Health Record"</a>

---

<!-- .slide: id="adlc-intro" -->

## What is the ADLC?

The Agent Development Lifecycle (ADLC) describes the end-to-end process for designing, building, and operating AI systems responsibly.

<p style="text-align: center"><img style="width: 75%; display: block; margin: 0 auto;" src="../images/adlc-diagram.png"/></p>

- Structured approach to AI system development
- Incorporates governance and ethics at every phase
- Enables repeatable, auditable workflows

Note: A few versions of this have emerged. 

<p class="push-bottom" style="text-align: right; font-size: 0.6em">source: <a href="https://www.ibm.com/forms/mkt-whitepaper-f42e50">Architecting secure enterprise AI agents with MCP</a></p>

---

<!-- .slide: id="adlc-phase-1" data-visibility="hidden" -->

## Phase 1: Problem Definition

- Identify business need and success criteria
- Assess feasibility and data availability
- Define scope, constraints, and stakeholders
- Conduct ethical impact assessment

Note: The problem definition phase is often undervalued. Ethical impact assessment here prevents costly redesigns later.

---

<!-- .slide: id="adlc-phase-2" data-visibility="hidden" -->

## Phase 2: Data Collection & Preparation

- Identify and gather relevant data sources
- Clean, label, and validate data
- Address bias and representativeness
- Establish data governance and lineage

---

<!-- .slide: id="adlc-phase-3" data-visibility="hidden" -->

## Phase 3: Model Development

- Select model architecture and approach
- Train, fine-tune, or prompt-engineer
- Evaluate performance and safety metrics
- Iterate based on results

---

<!-- .slide: id="adlc-phase-4" data-visibility="hidden" -->

## Phase 4: Deployment & Integration

- Package and serve the model
- Integrate with existing systems and workflows
- Set up monitoring and alerting
- Define rollback and incident response plans

---

<!-- .slide: id="adlc-phase-5" data-visibility="hidden" -->

## Phase 5: Operations & Governance

- Monitor model performance over time
- Detect and address drift and degradation
- Maintain audit trails and documentation
- Periodic re-evaluation and retraining

---

<!-- .slide: id="adlc-agents" -->

## ADLC for Agents

Agent-based systems introduce additional considerations:

- **Tool access** — what can the agent do?
- **Autonomy level** — when does it act without human approval?
- **Memory & state** — what persists across sessions?
- **Observability** — can you explain what the agent did and why?

Note: These four dimensions map directly to the four labs: build, observe, improve, secure.

---

<!-- .slide: id="lets-build" data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Up Next</p>

# Let's Build

Time for hands-on labs.

</div>

---

<!-- .slide: id="section-lab-1" data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Lab 1</p>

# The Naive Agent

What does a naive implementation look like — and why isn't it enough?

</div>

---

<!-- .slide: id="lab1-background-vs-chat" -->

## Lab 1: Why Not a Chat Interface?

Most people encounter agents as **chat agents** — you type, the agent responds. For our doctor inbox, that's the wrong choice.

With a chat box, there's nothing stopping a doctor from asking the agent to draft a reply, confirm a diagnosis, or "just handle it." The UI is a constraint on behavior. Choose it intentionally.

A **background agent** is triggered by data arriving — a new patient message — processes it, and writes structured output to a store the doctor then reads. The agent's role is constrained by design, not by a warning in the prompt.

<a href="http://localhost:8501">Open the EHR →</a>

---

<!-- .slide: id="lab1-langgraph" -->

## Lab 1: Why LangGraph?

The ReAct loop — observe, reason, act, repeat — needs orchestration: state tracking, conditional routing, tool execution, loop termination. You could write that yourself. LangGraph gives it to you.

```python
def _build_agent():
    llm = get_chat_model()
    return create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SYSTEM_PROMPT,
        response_format=PatientConcerns,
    )
```

That's the whole agent. `create_react_agent` handles the loop:
1. Send system prompt + user message to the LLM
2. If the LLM returns tool calls → execute them, feed results back, go to 1
3. If the LLM is done → one final call with Structured Outputs to produce a `PatientConcerns` object

In Lab 3, we use the same `StateGraph` primitives to wire together the critic loop. Each component has one job; the graph connects them.

---

<!-- .slide: id="lab1-tools-and-schema" -->

## Lab 1: Tools and the Output Contract

Each function decorated with `@tool` does three things: registers it as callable, generates a JSON schema from type hints and docstring, and makes it available during the ReAct loop. The agent decides which tools to call and in what order — we don't script that.

The doctor never sees raw LLM output. The agent fills in a typed `Concern`:

- `title`, `summary`, `action` — what the doctor needs to act on
- `concern_type` — medication, lab result, symptom, follow-up, administrative
- `urgency` — routine, soon, or urgent
- `evidence` — specific values and dates, not paraphrases
- `related` — links back to the relevant messages, labs, encounters

The contract between agent and UI is explicit. The UI renders the schema. That's the constraint.

---

<!-- .slide: id="lab1-structured-output" -->

## Lab 1: Structured Outputs ≠ "Please Return JSON"

LLMs generate one token at a time. **Constrained decoding** masks out invalid tokens at each step — the model literally cannot produce malformed output. It's the difference between asking someone to drive the speed limit and installing a speed governor.

This is different from prompting for structure:

- **Prompting**: describe the format in the prompt; the model tries to follow it. Sometimes it wraps the JSON in markdown. Sometimes it invents fields.
- **Constrained decoding**: the schema is enforced at the token level. No retries, no parsing code, no stripping code fences.

For a background agent with no human watching, this isn't a nice-to-have. If the output doesn't parse at 3 AM, the pipeline fails silently.

---

<!-- .slide: id="section-lab-2" data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Lab 2</p>

# Observability

You can't improve what you can't see.

</div>

---

<!-- .slide: id="lab2-different" -->

## Lab 2: Agent Observability Is Different

Traditional monitoring captures metadata — latency, error rates, status codes. For agents, that's not enough.

When something goes wrong, you need to know which tools the agent called, in what order, with what inputs, and what the LLM actually saw before it decided. You need the **content**, not just the metadata.

That creates a tension: the richer your traces, the more useful they are for debugging — and the more likely they are to contain sensitive data. Your trace store becomes a **secondary repository of PHI** that needs its own governance posture.

---

<!-- .slide: id="lab2-langfuse" -->

## Lab 2: Why Langfuse?

Langfuse is an open-source LLM observability platform. Self-hostable — in this lab it runs entirely in Docker on your machine. Nothing leaves the building.

Instrumenting the agent takes three lines:

```python
handler = create_langfuse_handler()

result = agent.invoke(
    {"messages": [...]},
    config={"callbacks": [handler]},
)
```

The `CallbackHandler` hooks into LangChain's callback system, which LangGraph propagates automatically to every LLM call and tool call in the ReAct loop. You don't instrument each step — you instrument the entry point.

What you get: full traces with nested spans, token counts and cost per LLM call, tool call inputs and outputs, session grouping by patient, and a UI for browsing, filtering, annotating, and building evaluation datasets.

---

<!-- .slide: id="lab2-what-to-log" -->

## Lab 2: What to Log

Not everything should be in your traces.

<table>
<tr><td><strong>Log Freely</strong></td><td><strong>Log With Masking</strong></td><td><strong>Do Not Log</strong></td></tr>
<tr><td>Latency, token counts, cost</td><td>Summarized user intent</td><td>Raw credentials / secrets</td></tr>
<tr><td>Model name, temperature</td><td>Redacted inputs/outputs</td><td>Full PHI in healthcare contexts</td></tr>
<tr><td>Tool call names, success/fail</td><td>Error messages (scrubbed)</td><td>Internal API keys in tool args</td></tr>
<tr><td>Trace structure / spans</td><td>Session metadata</td><td>Unmasked PII</td></tr>
</table>

To improve the agent, you need rich traces. But rich traces mean more sensitive data in your observability platform. The table above is how you navigate that tension.

---

<!-- .slide: id="lab2-pii" -->

## Lab 2: Run the Agent. Look at the Traces.

You'll see patient names, dates of birth, phone numbers, insurance IDs, and full medical records — in plain text — in your observability platform. Under HIPAA, that's a reportable breach.

We mask it before it gets there, with two layers:

- **Pydantic model annotations** — fields tagged `@pii` or `@phi` are replaced with `<PII_REDACTED>` regardless of string length. NER fails on short strings like `"Patricia Kowalski"`. Annotations don't.
- **Microsoft Presidio** (spaCy NER + regex) — catches PII embedded in free text: message bodies, clinical notes, LLM reasoning.

Both layers run **client-side**, before any data leaves the process.

---

<!-- .slide: id="lab2-presidio" -->

## Lab 2: Why Presidio?

[Microsoft Presidio](https://github.com/microsoft/presidio) is an open-source PII detection and anonymization library. It combines two detection approaches:

- **spaCy NER** — a trained named entity recognition model that identifies people, locations, dates, and other entities in natural language context. Good at finding "Patricia Kowalski" inside a sentence.
- **Regex patterns** — catches structured PII regardless of context: SSNs, phone numbers, email addresses, credit cards. We add a custom recognizer for insurance member IDs.

It integrates with LangChain via `PresidioAnonymizer`, which hooks into the same callback layer as Langfuse. One callback stack handles both masking and tracing.

The reason we use two layers (Presidio + Pydantic annotations) is that NER struggles with short strings in isolation. A field containing just `"Patricia Kowalski"` may not be confidently classified as a person name. The annotations tell us exactly which fields are sensitive — NER handles the free text where it excels.

---

<!-- .slide: id="lab2-what-traces-show" -->

## Lab 2: What Traces Actually Show You

With masking in place, traces reveal things you can't see any other way:

- **Tool call order** — did the agent investigate sensibly, or call everything at once?
- **The implicit summarization problem** — compare what tools returned (ground truth) to what the agent concluded. Discrepancies are visible by eye. Lab 3 automates catching them.
- **The invisible prompt** — the doctor never sees the message the agent acted on. If the prompt is poorly written or biased, the trace is where you find out.
- **Cost per run** — token counts per LLM call. At scale, "the agent runs on every patient every day" adds up fast.

---

<!-- .slide: id="lab2-datasets" -->

## Lab 2: Traces as an Evaluation Dataset

Traces aren't just for debugging right now — they're raw material for getting better over time.

- **Add to Dataset** — save any trace as a labeled example. Good runs and bad runs. Over time you build a corpus of real agent behavior to use for regression testing and evaluation.
- **Annotate** — add scores or free-text notes to any trace. When a clinician spots a wrong concern, they annotate the trace with what went wrong. That's a feedback loop from domain experts back to the engineering team — without any code changes.

And then there's **LLM-as-Judge**: use a second LLM to evaluate the first one's output at scale. We'll build this in Lab 3. The traces you're capturing here are exactly the input it needs.

---

<!-- .slide: id="section-lab-3" data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Lab 3</p>

# Improving Your Agent

Use what you observed to make it better.

</div>

---

<!-- .slide: id="lab3-adlc-loop" -->

## Lab 3: Where We Are in the ADLC

Lab 1 was Model Development — building the agent. Lab 2 was Operations — adding visibility. Lab 3 is the feedback loop between the two:

**Run agent → Inspect traces → Identify failure → Implement fix → Run agent**

This is the inner loop of the ADLC's Operations & Governance phase. Each of the three improvements in this lab was driven by something specific visible in the traces — not by guessing, not by re-reading the prompt, not by switching models.

Observability only pays off if you act on what you find.

---

<!-- .slide: id="lab3-what-we-found" -->

## Lab 3: What the Traces Told Us

Three problems visible in the Lab 2 traces:

**1. It hallucinates.** Compare tool call outputs (what the data says) to the agent's concerns (what it claims). You'll find evidence strings citing lab values or dates that don't exist in the record.

**2. It goes off-task.** Despite the system prompt saying not to make clinical recommendations, it suggests diagnoses and proposes treatments. A system prompt is a request, not a constraint.

**3. It dumps everything.** `get_patient_record` returns the full patient record — demographics, all conditions, all labs, all messages — on every call. More data in context = more opportunities to hallucinate from irrelevant information.

---

<!-- .slide: id="lab3-prompt-injection" -->

## Lab 3: Prompt Injection — Reduced by Design

You might wonder whether a patient could craft a portal message to hijack the agent.

In this system, the risk is reduced by a deliberate architectural decision: the agent runs in the background, and its output goes to the **doctor** — not back to the patient. The patient never sees agent output, so there's no feedback loop to exploit.

This isn't an accident. It's a consequence of choosing a background agent over a chat interface. The "why not a chatbox" decision from Lab 1 is also doing security work here. Security decisions cascade through architecture.

---

<!-- .slide: id="lab3-focused-tools" -->

## Lab 3: Focused Tools Force Intentional Investigation

Replace `get_patient_record` with keyword-based search tools: `search_conditions`, `search_labs`, `search_medications`. The agent has to say what it's looking for before it gets any data.

Instead of drowning in everything at once, it has to reason first: "The patient mentioned fatigue — let me check thyroid conditions and TSH labs." This is investigation, not retrieval.

Fewer tokens in context means lower cost, less hallucination surface area, and less PHI exposure in the traces.

---

<!-- .slide: id="lab3-critic" -->

## Lab 3: Claim Extraction + Grounding

Three steps run after the primary agent:

1. **Claim extraction** — pull out every specific, verifiable medical claim from each concern. Vague descriptions ("recent lab results") get filtered out. You can't ground-check something that doesn't assert anything specific.

2. **Grounding check** — each extracted claim is verified against the raw tool output. Did the agent actually see that lab value?

3. **Critic** — evaluates on-task behavior plus grounding results; sends revision feedback back to the primary agent if needed.

Why extract claims first? A grounding model returns one verdict per claim. Without extraction, you can't tell *which part* of a concern is wrong.

---

<!-- .slide: id="lab3-why-guardian" -->

## Lab 3: Why Granite Guardian?

[Granite Guardian](https://www.ibm.com/granite/docs/models/guardian/) is IBM's open-source model fine-tuned specifically for risk and safety detection — not a general LLM doing safety "on the side."

It runs locally via [Ollama](https://ollama.com) — no API calls, no data leaving your machine. On consumer hardware, each claim check takes ~1-2 seconds.

The interface is deliberately minimal. The system message selects the risk detector (`groundedness`, `harm`, etc.). The user message provides the context and the claim. The model returns one token: `Yes` (risk detected) or `No` (safe). That's it.

This specificity matters: Granite Guardian was trained to detect hallucination and harm. A general LLM doing the same job brings its own biases and blind spots to the evaluation — and it's checking its own work. Guardian is a different model, trained for this task, running independently.

---

<!-- .slide: id="lab3-guardian" -->

## Lab 3: LLM-as-Judge vs. Granite Guardian

Two options for the grounding step:

<table>
<tr><td></td><td><strong>LLM-as-Judge</strong></td><td><strong>Granite Guardian</strong></td></tr>
<tr><td>Self-evaluation bias</td><td>Yes — checking its own work</td><td>No — separate model</td></tr>
<tr><td>Cost</td><td>Uses your API quota</td><td>Free, runs locally via Ollama</td></tr>
<tr><td>Purpose-built</td><td>General reasoning</td><td>Fine-tuned for groundedness detection</td></tr>
</table>

Guardian uses a specific message format: system message selects the `groundedness` risk detector; user message provides context and one claim. Returns Yes (hallucinated) or No (grounded). The lab lets you toggle between both and compare traces side by side.

---

<!-- .slide: id="section-lab-4" data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Lab 4</p>

# Securing Data

Enforce access control at the database layer.

</div>

---

<!-- .slide: id="lab4-output-is-sensitive" -->

## Lab 4: Agent Output Is PHI Too

We've been protecting the patient records the agent reads. But the concerns the agent writes are also sensitive — they're clinical findings derived from patient data.

In Labs 1-3, the agent writes to a flat JSON file. Any code path can read or overwrite any patient's concerns. Run the agent twice and the first run's output is gone.

In a multi-provider practice, provider A's agent may reach a different conclusion about the same patient than provider B. That's clinically significant. Those conclusions need access control — and they need to be stable across runs.

---

<!-- .slide: id="lab4-rls" -->

## Lab 4: Why Access Control Belongs in the Database

**Application-layer filtering**: every query includes `WHERE provider_id = :provider_id`. You have to remember it in every query, every ORM eager-load, every debug endpoint, every migration. Forget it once and data leaks silently.

**Postgres Row-Level Security**: the policy applies to every query automatically — including ones you haven't written yet. A new developer can write `SELECT * FROM concerns` and only sees what the session allows.

```sql
CREATE POLICY provider_concern_access ON concerns
    USING (
        provider_id = current_setting('app.provider_id', true)
        OR id IN (SELECT concern_id FROM shared_concerns
                  WHERE shared_with = current_setting('app.provider_id', true))
    );
```

One place to maintain the rule, instead of every query in the codebase.

---

<!-- .slide: id="lab4-ownership" -->

## Lab 4: Default Deny, Explicit Grant

Concerns belong to the provider whose agent created them. Dr. Kim and Rachel Torres run agents against the same patients — they get separate concern sets, even for the same patient. The agent is a delegate; its output inherits the identity of whoever invoked it.

The default is isolation. To share a concern, you make an explicit grant — `share_concern()` records it in `shared_concerns`. That action is auditable.

Compare this to most application-layer designs, where the default is permissive and you add filters to restrict. **Default deny inverts the assumption.** Access is exceptional, not normal.

---

<!-- .slide: id="lab4-scoping" -->

## Lab 4: Tool Scoping + Concern Stability

**Tool scoping**: instead of a flat tool list, a factory creates tools scoped to one authorized patient. If the agent tries to access a different patient's record, it gets an explicit denial.

Elena Vasquez's record mentions her neighbor Patricia Kowalski and asks the doctor to check on her. The agent sees the mention, tries to access Patricia's record, and gets denied. The doctor never sees data she didn't authorize.

**Concern stability**: the agent receives its previous concerns as context and reuses their IDs. Running it twice doesn't wipe previous work — it builds on it. Downstream systems (notifications, audit logs, care coordination) can reference concern IDs and know they'll persist.

---

<!-- .slide: id="lab4-production" -->

## Lab 4: What RLS Doesn't Fully Solve

The RLS policy trusts `current_setting('app.provider_id')` — a session variable the application sets. A Python bug that sets the wrong provider ID would still leak data. RLS centralizes the filter; it doesn't verify the identity.

In production:
- Each provider authenticates via JWT/OAuth
- Identity flows into a per-provider database role
- The policy checks `current_user`, not a session variable the app can misconfigure
- Langfuse traces need their own RBAC — the same provider who can see concerns in the UI shouldn't automatically see all traces

RLS is defense-in-depth, not a complete security boundary. It's one layer in a stack.

---

<!-- .slide: id="wrap-up" data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Fin</p>

# What You Built Today

</div>

---

<!-- .slide: id="wrap-up-summary" -->

## What You Built (and Why It Matters)

<div style="display: flex; gap: 2em">
<div style="flex: 1">

**The Agent**
- Background inbox triage for a doctor's EHR
- Structured outputs — no free text, no advice, no drafts
- Doctor stays in the loop at every step

</div>
<div style="flex: 1">

**The Stack**
- Lab 1: LangGraph + constrained decoding
- Lab 2: Langfuse + Presidio
- Lab 3: Critic loop + Granite Guardian
- Lab 4: Postgres RLS + scoped tools

</div>
</div>

---

<!-- .slide: id="responsible-by-design" -->

## Responsible by Design

Responsibility isn't something you bolt on at the end.

- **Build** with constraints from day one — structure limits what the agent can say
- **Observe** so you can explain every decision — and defend it
- **Improve** using evidence from real traces, not intuition
- **Secure** at the infrastructure layer, not just the prompt

=====

<style>
/* Embedded mode */
.mkdocs-revealjs-wrapper,
.mkdocs-revealjs-wrapper .reveal {
  aspect-ratio: 16 / 9 !important;
  height: auto !important;
  max-height: 80vh;
}
/* Fullscreen — let reveal.js take over completely */
.reveal:fullscreen,
.reveal:-webkit-full-screen {
  width: 100vw !important;
  height: 100vh !important;
  max-height: none !important;
  aspect-ratio: unset !important;
}
</style>

**Jump to:** [Intro](#/section-agents) · [ADLC](#/adlc-intro) · [Lab 1](#/section-lab-1) · [Lab 2](#/section-lab-2) · [Lab 3](#/section-lab-3) · [Lab 4](#/section-lab-4) · [Wrap-up](#/wrap-up)

**Keyboard shortcuts:** `F` fullscreen · `O` overview · `S` speaker notes · `←` `→` navigate
