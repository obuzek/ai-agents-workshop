# Lab 2: Observability

**Duration:** ~25 minutes

???+ abstract "What You'll Do"
    Lab 1's agent gives you concerns, but not how it got them. Which tools did it call? What data did it see?

    watsonx Orchestrate already records this. Every run of your agent produces a **trace**. In this lab you'll open a trace, find the patient data inside it, and try the two masking layers Orchestrate offers. Then you'll compare traces to see what each layer changes and what it leaves alone.

    Each step is something you run and look at. The extra-credit step at the end is optional.

---

## What an Agent Trace Needs to Show

Traditional software observability tracks status codes, latency and error rates. For an agent you also need the **content**: the prompts, the tool call arguments, the tool results and the model's replies. Without the content you can't tell why the agent said what it said.

The content also includes patient data. When the agent calls `get_patient_record("patient-001")`, the trace records:

- **Input**: the patient ID
- **Output**: the whole patient record: name, date of birth, phone, email, address, insurance member ID, medications, labs, messages

That output now lives in the trace store as well as in the EHR. The trace store is a second copy of patient data, and it needs the same rules as the first.

In the slides before this lab, we covered the **"What to Log" framework**:

| Log Freely | Log With Masking | Do Not Log |
|---|---|---|
| Latency, token counts | Summarized user intent | Raw credentials / secrets |
| Model name, parameters | Redacted inputs / outputs | Full PHI in healthcare contexts |
| Tool call names, success/fail | Error messages (scrubbed) | Internal API keys in tool args |
| Trace structure / spans | Session metadata | Unmasked PII |

Orchestrate writes the traces for you, so there's no instrumentation code to write or maintain. In exchange, the platform decides what goes in them. This lab shows what Orchestrate puts in its traces and which parts you can change.

---

## Learning Objectives

By the end of this lab, you will:

- [x] Find your agent's traces in Orchestrate and read a trace: LLM calls, tool calls, token counts
- [x] Find raw patient data (PHI) in a trace and say who can read it and for how long
- [x] Explain the difference between Orchestrate's model gateway, its controls and its plug-ins
- [x] Bind a PII Filter control to your agent and see what it masks
- [x] Deploy a PII masking plug-in and see what it masks, and what is still in the trace
- [x] Explain why returning less data from the tools is the only layer that keeps PHI out of the trace

---

## Step 1: Run Your Agent and Open Its Trace

You need your Lab 1 agent deployed, the inbox UI running and the Lab 1 agent service running. If you stopped them, restart them:

```bash
cd ~/ai-agents-workshop
uv run streamlit run app/ui.py --server.port 8501      # terminal 1
uv run uvicorn lab1.agent.api:app --port 8001          # terminal 2
```

In the UI at [http://localhost:8501](http://localhost:8501), pick a patient and click **Run Agent**. Write down the patient and the time.

### Find the trace in Orchestrate

Traces are in watsonx Orchestrate, not in watsonx.ai.

1. Open the Orchestrate UI for the workshop instance ([how to open it](ibm-cloud-login.md#4-open-watsonx-orchestrate-for-the-labs)).
2. From the main menu, open **Analyze**. This opens **Agent analytics**, a table of agents.
3. Click your agent, `<prefix>lakeview_inbox_agent` (for example `student0_lakeview_inbox_agent`).
4. The **Traces** view lists runs with a timestamp, trace ID, status, model and latency. Pick the run at the time you wrote down.
5. Open **Trace details** to see each step of the run.

IBM documents this path in [Monitoring agents](https://www.ibm.com/docs/en/SSAVQO/administering/agent_observability.html). The ADK docs describe the same data under "Analyze > [Agent name] > Overview and Conversations" ([Observability SDK](https://developer.watson-orchestrate.ibm.com/traces/observability-sdk.md)).

<!-- TODO(verify): exact menu labels in the workshop tenant's UI. The IBM Docs page is titled "legacy experience"; the ADK docs use "Overview" and "Conversations" instead of "Traces" / "Trace details". Check which one the TXC tenant shows and drop the other. -->

??? tip "From the command line instead"
    The `orchestrate` CLI can list and export traces from your active environment:

    ```bash
    orchestrate observability traces search --last 30m --limit 20
    orchestrate observability traces export --trace-id <32-character trace ID> --output trace.json
    ```

    `search` can't filter by agent name in the current ADK (that option is deprecated), so you'll see runs from the whole room. Use the time of your run to find yours. `export` writes the full trace as JSON.

    <!-- TODO(verify): the trace API is rate-limited (we measured 4 requests/minute and a 4-hour search window). Confirm whether the CLI hits the same limit before a room of 30 runs it at once. -->

### Read the trace

The trace is a tree of **spans**. One span covers the whole run. Inside it are:

- **LLM calls**, with the model name (`claude-sonnet-5-5`) and input and output token counts. There's no cost figure.
- **Tool calls**, with the full arguments and the full result.
- The agent's final reply: the raw JSON before `agent.py` validated it.

Open the `get_patient_record` tool call and look at its output.

???+ warning "This is the patient record"
    The tool output holds the patient's name, date of birth, phone number, email, home address, insurance member ID, and the full clinical record, in plain text. The LLM calls that follow contain the same data, because the tool result is part of the model's input.

    Orchestrate recorded all of it without any code from you.

???+ question "Look at the run"
    - How many tool calls did the agent make before it answered? Did it call `search_labs` or `get_messages`, or did it answer from `get_patient_record` alone?
    - Open the first LLM call and read its input. The "user" message was written by `agent.py`, not by Dr. Kim. The doctor never sees this prompt, but it shapes everything the agent does.
    - Compare what the tools returned with the concerns the agent wrote. Is every piece of evidence in the tool output? Lab 3 checks this automatically.

---

## Step 2: Who Else Can Read This Trace?

Go back to the agent list in **Analyze**. Open someone else's agent, for example the seat next to you, and open one of their traces.

You can read it. You can read their patient's record in the tool output.

That's because every seat in this workshop has the same broad role on one shared Orchestrate instance. IBM's docs say users with the Administrator or Builder role can view conversations in their tenant ([Chat privacy and data protection](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/base?topic=instance-chat-privacy-data-protection)) and that builders and administrators can view traces ([Monitoring agents](https://www.ibm.com/docs/en/SSAVQO/administering/agent_observability.html)). The patients are synthetic, so this is safe today.

### Traces are PHI

Treat the trace store like any other copy of patient data. **Data provenance** means you can say where patient data went and what happened to it at each step. For the trace store, that comes down to three questions:

| Question | In this workshop | Source |
|---|---|---|
| **Where does it live?** | In the Orchestrate instance, next to the agent. It is a separate copy from the EHR. | Observed |
| **Who can read it?** | Every seat. Access follows the Orchestrate role, and every seat has a Builder-level role or higher. | Tested; [Monitoring agents](https://www.ibm.com/docs/en/SSAVQO/administering/agent_observability.html) |
| **How long is it kept?** | 30 days, then deleted. The period is fixed. | [Managing data retention](https://www.ibm.com/docs/en/SSAVQO/administering/data_retention_agentic_experience.html) |

In a real deployment you'd answer the same questions before the first real patient: who gets a role that can read traces, whether 30 days fits your retention policy, and what the tools put into the trace in the first place. Lab 4 comes back to this.

---

## Policy Engines: What Orchestrate Offers

Orchestrate has three places where you can change what happens on the way into and out of your agent.

- The **model gateway** routes the agent's LLM calls. It lets one agent definition use models from different providers: today it sends your agent's calls to Claude Sonnet 5.5 through the workshop's model proxy, which holds the Anthropic key so it never reaches your laptop. Model policies can fall back to another model, balance load across models, or retry ([Model policies](https://developer.watson-orchestrate.ibm.com/llm/model_policies.md); public preview). Checking content is the job of controls.
- **Controls** are Orchestrate's policy engine. A control binds a built-in policy type to your agent at a fixed **hook**, such as `agent_pre_invoke` (before the agent sees the message). Policy types include a PII Filter, Content Guardrails (jailbreak, hate/abuse/profanity, harm, social bias), Secrets detection, Regex pattern, SQL sanitizer, an output-length guard, rate limiters and model fallback/retry. ([Managing controls](https://developer.watson-orchestrate.ibm.com/controls/managing_controls.md))
- **Plug-ins** are your own Python code, run at agent hooks such as `agent_post_invoke` (after the agent answers, before the caller gets the answer). ([Plug-ins](https://developer.watson-orchestrate.ibm.com/plugins/plugins.md))

The diagram shows what we tested on the workshop instance. Content Guardrails and the other control types exist, but we haven't tested them.

<div class="wxo-policy" style="margin:1.5em 0">
<svg class="wxo-policy-svg" viewBox="0 0 760 640" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="A caller sends a message to the agent. Controls at agent_pre_invoke run first: the PII Filter masks PII the user types (verified); Content Guardrails are untested. Controls bound to tool_post_invoke and agent_post_invoke were accepted but did not execute in our tests. The agent runs a ReAct loop. Its LLM calls go through the model gateway, which handles fallback, load balancing and retry to Claude Sonnet 5.5. Its tool calls go to the tool runtime, which reads the shared EHR. Tool output carries patient messages, which is an indirect prompt-injection path that no control inspects. After the agent answers, a Python plug-in at agent_post_invoke masks phone, email, date of birth and member ID in the answer (verified). Every step writes to the trace store, which holds raw tool input and output and LLM context, is readable across the tenant, and keeps traces for 30 days." style="width:100%;max-width:760px;height:auto;display:block;margin:0 auto">
<style>
.wxo-policy-svg { font-family: 'IBM Plex Sans', sans-serif; color: inherit; }
.wxo-policy-svg text { fill: currentColor; font-size: 14px; }
.wxo-policy-svg text.t { font-size: 16px; font-weight: 600; }
.wxo-policy-svg text.mono { font-family: 'IBM Plex Mono', monospace; font-size: 13px; }
.wxo-policy-svg text.zone { fill: #8d8d8d; font-size: 14px; font-weight: 600; letter-spacing: 0.04em; }
.wxo-policy-svg text.muted { fill: #8d8d8d; font-size: 13px; }
.wxo-policy-svg text.warn { fill: #fa4d56; font-size: 13px; }
.wxo-policy-svg text.on-blue { fill: #ffffff; }
.wxo-policy-svg .box { fill: none; stroke: currentColor; stroke-width: 1.5px; }
.wxo-policy-svg .box.blue { fill: #0f62fe; stroke: none; }
.wxo-policy-svg .box.soft { fill: rgba(141,141,141,0.16); stroke: none; }
.wxo-policy-svg .box.dash { stroke: #8d8d8d; stroke-dasharray: 5 4; }
.wxo-policy-svg .zone-r { fill: none; stroke: #8d8d8d; stroke-width: 1.5px; stroke-dasharray: 6 6; }
.wxo-policy-svg .edge { fill: none; stroke: currentColor; stroke-width: 2px; marker-end: url(#wxo-p-arrow); }
.wxo-policy-svg .edge.both { marker-start: url(#wxo-p-arrow-start); }
.wxo-policy-svg .edge.rec { stroke: #8d8d8d; stroke-width: 1.5px; stroke-dasharray: 5 4; marker-end: url(#wxo-p-arrow-muted); }
.wxo-policy-svg .edge.inj { stroke: #fa4d56; marker-start: url(#wxo-p-arrow-red-start); marker-end: url(#wxo-p-arrow-red); }
</style>
<defs>
<marker id="wxo-p-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" markerUnits="strokeWidth" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="currentColor"/></marker>
<marker id="wxo-p-arrow-start" viewBox="0 0 10 10" refX="0" refY="5" markerWidth="7" markerHeight="7" markerUnits="strokeWidth" orient="auto"><path d="M10 0 L0 5 L10 10 z" fill="currentColor"/></marker>
<marker id="wxo-p-arrow-muted" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" markerUnits="strokeWidth" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#8d8d8d"/></marker>
<marker id="wxo-p-arrow-red" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" markerUnits="strokeWidth" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#fa4d56"/></marker>
<marker id="wxo-p-arrow-red-start" viewBox="0 0 10 10" refX="0" refY="5" markerWidth="7" markerHeight="7" markerUnits="strokeWidth" orient="auto"><path d="M10 0 L0 5 L10 10 z" fill="#fa4d56"/></marker>
</defs>
<!-- Caller (outside Orchestrate) -->
<rect class="box" x="222" y="10" width="260" height="56"/>
<text class="t" x="238" y="34">Caller (agent.py)</text>
<text x="238" y="54">"Review patient-005"</text>
<line class="edge" x1="352" y1="66" x2="352" y2="112"/>
<!-- Orchestrate zone -->
<rect class="zone-r" x="1" y="92" width="758" height="456"/>
<text class="zone" x="16" y="118">WATSONX ORCHESTRATE</text>
<!-- Controls at agent_pre_invoke -->
<rect class="box" x="222" y="112" width="260" height="100"/>
<text class="t" x="238" y="136">Controls</text>
<text class="mono" x="316" y="136">agent_pre_invoke</text>
<text x="238" y="160">PII Filter: masks PII the user</text>
<text x="238" y="180">types. Verified.</text>
<text x="238" y="200">Content Guardrails: untested.</text>
<!-- Post hooks that didn't run -->
<rect class="box dash" x="530" y="112" width="218" height="92"/>
<text class="muted" x="544" y="134">Controls at tool_post_invoke</text>
<text class="muted" x="544" y="154">and agent_post_invoke:</text>
<text class="muted" x="544" y="174">accepted, but did not run</text>
<text class="muted" x="544" y="194">in our tests.</text>
<line class="edge" x1="352" y1="212" x2="352" y2="236"/>
<!-- Agent -->
<rect class="box blue" x="222" y="236" width="260" height="120"/>
<text class="t on-blue" x="238" y="262">Your agent</text>
<text class="on-blue" x="238" y="286">ReAct loop (react_core)</text>
<text class="on-blue" x="238" y="314">LLM calls go to the gateway</text>
<text class="on-blue" x="238" y="336">Tool calls go to the tool runtime</text>
<!-- Model gateway -->
<rect class="box" x="530" y="216" width="218" height="96"/>
<text class="t" x="544" y="240">Model gateway</text>
<text x="544" y="262">Fallback, load balance, retry</text>
<text x="544" y="282">to Claude Sonnet 5.5</text>
<text class="muted" x="544" y="302">Reliability only. Preview.</text>
<line class="edge both" x1="482" y1="264" x2="530" y2="264"/>
<!-- Tool runtime -->
<rect class="box" x="530" y="324" width="218" height="56"/>
<text class="t" x="544" y="348">Tool runtime</text>
<text x="544" y="368">runs your tools.py</text>
<line class="edge both" x1="482" y1="340" x2="530" y2="340"/>
<!-- Tool runtime to EHR, with injection label -->
<line class="edge both inj" x1="560" y1="380" x2="560" y2="572"/>
<text class="warn" x="574" y="414">Tool output carries patient</text>
<text class="warn" x="574" y="434">messages. This is the indirect</text>
<text class="warn" x="574" y="454">prompt-injection path. No</text>
<text class="warn" x="574" y="474">control inspects tool output.</text>
<line class="edge" x1="352" y1="356" x2="352" y2="396"/>
<!-- Plug-in -->
<rect class="box blue" x="222" y="396" width="260" height="96"/>
<text class="t on-blue" x="238" y="420">Plug-in</text>
<text class="mono on-blue" x="300" y="420">agent_post_invoke</text>
<text class="on-blue" x="238" y="444">Your Python. Masks phone, email,</text>
<text class="on-blue" x="238" y="464">DOB and member ID in the answer.</text>
<text class="on-blue" x="238" y="484">Verified.</text>
<!-- Trace store -->
<rect class="box soft" x="12" y="140" width="180" height="352"/>
<text class="t" x="26" y="166">Trace store</text>
<text x="26" y="192">Every step writes here.</text>
<text x="26" y="226">Raw tool input and</text>
<text x="26" y="246">output, and the LLM</text>
<text x="26" y="266">context: this is PHI.</text>
<text x="26" y="300">Readable across the</text>
<text x="26" y="320">whole tenant.</text>
<text x="26" y="354">Kept 30 days.</text>
<line class="edge rec" x1="222" y1="162" x2="192" y2="162"/>
<line class="edge rec" x1="222" y1="296" x2="192" y2="296"/>
<line class="edge rec" x1="222" y1="444" x2="192" y2="444"/>
<!-- Answer and EHR (outside Orchestrate) -->
<line class="edge" x1="352" y1="492" x2="352" y2="572"/>
<rect class="box" x="222" y="572" width="260" height="56"/>
<text class="t" x="238" y="596">Answer to the caller</text>
<text x="238" y="616">concerns JSON</text>
<rect class="box" x="530" y="572" width="218" height="56"/>
<text class="t" x="544" y="596">Shared EHR (cloud)</text>
<text x="544" y="616">your copy of the patients</text>
</svg>
</div>

!!! danger "The injection path is the tool output"
    In this agent, untrusted text arrives through tool output: a patient's portal message, returned by `get_messages` or `get_patient_record`. The input controls see what the caller sends. The controls we bound to the post-invoke hooks didn't run in our tests, so in this workshop nothing inspects tool output. Until a tool-output control runs for you, handle it in your own design: return less from the tools (Step 5) and check the agent's answer against the record (Lab 3).

Here are the three layers for patient data, with what we measured:

| Layer | Mechanism | What it protects | What it doesn't protect |
|---|---|---|---|
| **Input** | PII Filter control at `agent_pre_invoke` | PII the user types in the message. Regex detectors: phone, email, date of birth, SSN, MRN and others. | Names. Anything that comes back from a tool. |
| **Output** | Python plug-in at `agent_post_invoke` | Phone, email, labelled date of birth and member ID in the final answer | Names and addresses. The tool output and LLM context, which are already in the trace. |
| **Source** | Tools return only the fields the agent needs | The model's context, the trace and the answer | Any field the tool still returns. |

---

## Step 3: Bind the PII Filter Control

Bind the built-in PII Filter to your agent at `agent_pre_invoke`. Replace `student0_` with your prefix:

```bash
orchestrate controls create \
  --artifact "PII Filter" \
  --name student0_pii_input \
  --hook agent_pre_invoke \
  --agent student0_lakeview_inbox_agent
```

<!-- TODO(verify): this is the form in IBM's managing_controls docs, without --config. Our live test passed a --config JSON; confirm the defaults mask phone/email without it. `orchestrate controls get-type --name "PII Filter"` shows the config options. -->

The inbox UI always sends the same message, which has no PII in it. To see the control work, send your agent a message that does:

```bash
orchestrate chat ask --agent-name student0_lakeview_inbox_agent \
  "Please review patient-001. If anything is urgent, call me at 555-201-3344 or email dr.kim@example.com."
```

<!-- TODO(verify): `orchestrate chat ask` is documented for the local Developer Edition; confirm it runs against the SaaS instance. -->

If `orchestrate chat ask` doesn't work against the workshop instance, open your agent in the Orchestrate UI and paste the same message into its chat preview.

Open the new trace. You'll see:

- A **control step** at `agent_pre_invoke` before the agent runs, reporting that PII was detected and redacted.
- The LLM input with the phone number and email masked.
- The `get_patient_record` tool output, still with the patient's phone, email and date of birth in full.

The control cleaned what the user typed. It didn't touch what the tool returned.

The CLI also accepts this control at `tool_post_invoke` and `agent_post_invoke`. In our tests on this instance, those hooks produced no control step in the trace and masked nothing. That's why Step 4 uses a plug-in to mask the answer.

To remove the control later:

```bash
orchestrate controls remove --name student0_pii_input
```

---

## Step 4: Deploy the PII Masking Plug-in

Open `lab2/orchestrate/pii_output_plugin.py`. It's one function, `mask_pii_output`, marked as an `agent_post_invoke` plug-in. It runs regexes over the agent's final answer:

- email addresses become `[EMAIL]`
- phone numbers become `[PHONE]`
- insurance member IDs become `[MEMBER_ID]`
- dates of birth become `[DOB]`, only when labelled ("DOB", "birth date"), so lab and visit dates stay as evidence

Redeploy your agent with the plug-in attached:

```bash
uv run python -m lab1.agent.deploy --pii-plugin
```

This imports the plug-in under your prefix and adds it to the agent's `agent_post_invoke` hook. Deploying again without `--pii-plugin` removes it. As in Lab 1, give a fresh deploy a couple of minutes before you run it.

We ran this plug-in live on the workshop instance with an earlier model. The `--pii-plugin` option of `deploy.py` has unit tests but hasn't been run live with Claude Sonnet 5.5. If you don't see the plug-in span in Step 4's trace, tell your instructor.

???+ question "Ask Bob"
    Open `lab2/orchestrate/pii_output_plugin.py` and ask Bob: "Which of these regexes would match a lab date or a medication dose by mistake? Why is the DOB pattern written the way it is?"

Run the agent again from the inbox UI, on the same patient as Step 1. Then compare the new trace with the one from Step 1:

- There's a new span for the plug-in, `mask_pii_output` (with your prefix), after the agent's last LLM call.

<!-- TODO(verify): whether the span name in the trace carries the seat prefix. Our test deployed the plug-in without a prefix. -->

- The answer that comes out of the plug-in has placeholders where the phone, email, member ID or labelled DOB were. If the agent didn't quote any of these in its concerns, there's nothing to mask. Ask for them with `orchestrate chat ask` (for example "include the patient's phone number in the summary") to see the difference.
- The patient's **name** and **address** still appear wherever the agent wrote them. Regexes don't find names.
- The `get_patient_record` tool span and the LLM calls still hold every value in full.

The plug-in runs after the model has read the full record, so it can only clean the answer.

---

## Step 5: Minimize at the Source (Try It Yourself, Extra Credit)

The input control and the output plug-in both leave the tool output in the trace. The only way to keep PHI out of the model and out of the trace is for the tool to return less.

`get_patient_record` returns demographics the agent never needs to find a concern: phone, email, address, member ID. The concerns are about labs, medications, messages and follow-ups.

Try it yourself:

1. In `lab1/agent/tools.py`, change `get_patient_record` to drop the contact and insurance fields before it returns. The repository's data models already mark these fields with `_pii` and `_phi` in `app/models.py`. Use them as your list, but don't import `app.models`: `tools.py` is uploaded to Orchestrate on its own.
2. Redeploy with `uv run python -m lab1.agent.deploy`.
3. Run the agent on the same patient and open the trace. The tool span no longer holds those fields, so neither do the LLM calls or the answer.
4. Check the concerns. Did the agent lose anything it needed?

Ask Bob for help: "Which fields in app/models.py are marked with _pii or _phi, and how would I drop those keys from the dict that get_patient_record returns in lab1/agent/tools.py?"

Lab 3 goes further: tools that search for one thing (a lab, a condition) instead of returning the whole record.

---

## What's Not Covered Here

**Cost.** Orchestrate traces show token counts per LLM call, not cost.

**Custom spans.** Tracing a hosted agent needs no code. For agents that run outside Orchestrate, IBM documents an Observability SDK and OpenTelemetry export ([Observability SDK](https://developer.watson-orchestrate.ibm.com/traces/observability-sdk.md)). We don't use them in this workshop.

**Operational monitoring.** In production you'd also track runs per hour, error rates and latency trends in your existing monitoring stack. The Agent analytics page shows some of this per agent.

**Evaluation.** Are the agent's concerns correct? That's Lab 3.

---

## What's Working

**Every run is recorded.** Every LLM call and tool call is in the trace, with inputs, outputs, timing and token counts, and you wrote no code for it.

**Two masking layers you can see.** The PII Filter control masks what the user types. The plug-in masks identifiers in the answer. Each one shows up in the trace as its own step.

**You can say where the patient data went.** The EHR, the model's context, the trace store, the answer. For the trace store, you know who can read it and how long it's kept.

---

## What's Still Broken

### The trace still holds the full record

Neither masking layer touches the tool output. Until the tools return less, every run puts a patient record in the trace store, readable by the whole tenant for 30 days.

### The agent still hallucinates and oversteps

With the trace, you can compare what the tools returned with what the agent claimed, and see when it suggests a diagnosis. Nothing checks this automatically yet.

### The agent still investigates shallowly

The trace shows how few tool calls the agent makes. Lab 3 adds checks for this.

---

## Up Next

| Lab | Problem | Solution |
|---|---|---|
| ~~[Lab 1](lab-1.md)~~ | ~~No structure, no tools, just vibes~~ | ~~A ReAct agent with structured output~~ |
| ~~[Lab 2](lab-2.md)~~ | ~~No visibility into agent behavior~~ | ~~Orchestrate traces, PII controls and plug-ins~~ |
| **[Lab 3](lab-3.md)** | Hallucinations, overstepping, shallow investigation | Evaluation: grounding checks, LLM-as-judge, critic |
| **[Lab 4](lab-4.md)** | Unrestricted data access | Security: where the data lives, who can read it, identity end to end |
