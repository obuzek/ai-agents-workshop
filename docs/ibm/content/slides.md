---
revealjs:
  mode: diapo
  # Slide geometry lives here rather than in the plugin config: mkdocs-revealjs
  # has no `width` option in its mkdocs.yml schema, but deck front matter is
  # passed straight through to Reveal.initialize().
  width: 1280
  height: 720
  # mkdocs-revealjs 0.12 defaults embedded decks to keyboardCondition: focused (keys only work
  # after clicking the deck). null restores page-wide shortcuts (F/O/S/arrows).
  keyboardCondition: null
---

<!-- .slide: id="title" data-background-gradient="linear-gradient(to top, #0f62fe 0, #0f62fe 16px, #161616 16px)" -->

<div style="color:#f4f4f4;display:flex;flex-direction:column;min-height:600px">

<p style="font-size:0.7em;letter-spacing:0.08em;text-transform:uppercase;color:#78a9ff;margin-top:1em">IBM TechXchange 2026</p>

<h1 style="color:#ffffff;text-transform:none;font-weight:300;font-size:2.4em;line-height:1.1;margin-top:0.6em">Building <span style="color:#78a9ff;font-weight:600">Responsible</span><br>AI Agents</h1>

<div class="push-bottom" style="border-left:4px solid #0f62fe;padding-left:0.8em;margin-bottom:1.2em">
<p style="font-size:0.85em;font-weight:600;margin:0;color:#ffffff">Olivia Buzek</p>
<p style="font-size:0.7em;margin:0;color:#c6c6c6">Staff AI Engineer, IBM</p>
</div>

</div>

---

<!-- .slide: id="todays-modules" -->

## Today's modules

<div style="display:grid;grid-template-columns:auto auto 1fr;gap:0.7em 1em;align-items:baseline;font-size:0.78em;margin-top:0.6em">
<div style="font-size:1.6em;font-weight:300;color:#0f62fe">1</div><div><strong>Build</strong></div><div>An agent on Orchestrate: definition, tools, deploy</div>
<div style="font-size:1.6em;font-weight:300;color:#0f62fe">2</div><div><strong>Observe</strong></div><div>Traces, and why traces are PHI. Controls and plug-ins for PII</div>
<div style="font-size:1.6em;font-weight:300;color:#0f62fe">3</div><div><strong>Improve</strong></div><div>Checks: grounding, LLM-as-judge and a critic, as judge agents</div>
<div style="font-size:1.6em;font-weight:300;color:#0f62fe">4</div><div><strong>Secure</strong></div><div>Agent output is sensitive data. Data storage guarantees. Identity end to end (discussion)</div>
</div>

<p style="font-size:0.7em;opacity:0.75;margin-top:2em">Labs 1–3: run it, then look at what changed. Lab 4: a discussion.</p>

Note: Here's the plan. In Lab 1 you deploy an agent to Orchestrate. In Lab 2 we look at its traces. They're full of patient data, so we'll look at what Orchestrate can mask, and what it can't. In Lab 3 we add checks on the agent's output, using other agents as judges. Lab 4 is a discussion: where does the agent's output get stored, and who gets to see it?

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

<!-- .slide: id="watsonx-products" -->

## watsonx.ai Studio vs watsonx Orchestrate vs watsonx.governance

<div style="display:flex;gap:28px;font-size:0.78em;line-height:1.4">
<div style="flex:1;border-top:4px solid #8d8d8d;padding-top:0.6em">
<p style="margin:0 0 0.2em;font-weight:600;font-size:1.25em">watsonx.ai Studio</p>
<p style="margin:0 0 0.8em;opacity:0.75">"A studio of integrated tools for building generative AI and machine learning solutions"</p>
<p style="margin:0 0 0.3em"><strong>What it's for</strong></p>
<ul style="margin:0 0 0.8em 1em">
<li>Foundation models: IBM and open source</li>
<li>Prompt Lab: experiment with prompts</li>
<li>Projects: shared workspaces for assets</li>
<li>Tuning, RAG, deployments</li>
</ul>
<p style="margin:0 0 0.3em"><strong>Today</strong></p>
<p style="margin:0">You open it once. That creates the watsonx profile that governance needs.</p>
</div>
<div style="flex:1;border-top:4px solid #0f62fe;padding-top:0.6em">
<p style="margin:0 0 0.2em;font-weight:600;font-size:1.25em">watsonx Orchestrate</p>
<p style="margin:0 0 0.8em;opacity:0.75">"An agent management platform designed to help build, deploy, orchestrate, manage and govern AI agents"</p>
<p style="margin:0 0 0.3em"><strong>What it's for</strong></p>
<ul style="margin:0 0 0.8em 1em">
<li>Agents and the tools they call</li>
<li>Connections that hold credentials</li>
<li>Controls and plug-ins: guardrails, PII</li>
<li>Traces and evaluation</li>
</ul>
<p style="margin:0 0 0.3em"><strong>Today</strong></p>
<p style="margin:0">Where you build and run your agent: definition, tools, connection, controls, traces.</p>
</div>
<div style="flex:1;border-top:4px solid #8d8d8d;padding-top:0.6em">
<p style="margin:0 0 0.2em;font-weight:600;font-size:1.25em">watsonx.governance</p>
<p style="margin:0 0 0.8em;opacity:0.75">"Govern any AI, anywhere with real-time visibility, enterprise controls, and continuous accountability"</p>
<p style="margin:0 0 0.3em"><strong>What it's for</strong></p>
<ul style="margin:0 0 0.8em 1em">
<li>Evaluating and monitoring AI output</li>
<li>Metrics, factsheets, model history</li>
<li>AI risk management</li>
<li>Policy and regulatory compliance</li>
</ul>
<p style="margin:0 0 0.3em"><strong>Today</strong></p>
<p style="margin:0">The evaluation concepts behind Lab 3: grounding, judges, metrics.</p>
</div>
</div>

Note: You'll hear about three watsonx products today. watsonx.ai Studio is where you work with models directly, try prompts in Prompt Lab, and keep things in projects. Today you only open it once. Opening it creates the watsonx profile that governance needs.

watsonx Orchestrate is where your agent lives. The agent, its tools, its connection to the EHR, the controls on it, and the traces of every run are all in Orchestrate.

watsonx.governance is for evaluating and monitoring AI, and for managing risk. In Lab 3 we build the kind of checks it's designed to track: grounding, judges, metrics.

Sources (IBM's own descriptions):
- watsonx.ai: https://www.ibm.com/products/watsonx-ai and https://www.ibm.com/docs/en/watsonx/saas?topic=overview-watsonx ("a studio of integrated tools…", Prompt Lab, projects)
- Prompt Lab and projects: https://dataplatform.cloud.ibm.com/docs/content/wsj/getting-started/get-started-prompt-lab.html?context=wx
- watsonx Orchestrate: https://www.ibm.com/products/watsonx-orchestrate
- watsonx.governance: https://www.ibm.com/products/watsonx-governance and https://www.ibm.com/docs/en/watsonx/saas?topic=overview-watsonx (evaluate prompts, monitor output, factsheets, risk)

---

<!-- .slide: id="which-model" -->

## Which model?

Today's agent runs on **Claude Sonnet 5.5**. It's a high-end model at a reasonable cost.

- In Orchestrate it's `virtual-model/anthropic/claude-sonnet-5-5`, reached through Orchestrate's model gateway.
- Orchestrate can be set up with many model backends: watsonx.ai, Anthropic, OpenAI, AWS Bedrock, Ollama and others.
- Through watsonx.ai you can choose open-weights models, or deploy your own. That's one way to run on-prem.

Note: We're using Claude Sonnet 5.5 today because it's a strong model at a reasonable price. We tried the free gpt-oss-120b first. It often stopped after one look at the patient record, so it missed things.

You're not locked into one model. Orchestrate's model gateway can talk to a long list of providers. If your data can't leave your building, watsonx.ai has open-weights models, and you can deploy your own model there.

Sources:
- Providers Orchestrate supports for models: https://developer.watson-orchestrate.ibm.com/llm/managing_llm.md
- watsonx.ai models: https://www.ibm.com/products/watsonx-ai
- Deploying your own model in watsonx.ai: https://www.ibm.com/docs/en/SSYOK8/wsj/analyze-data/deploy-custom-fm-cloud.html

---

<!-- .slide: id="todays-architecture" -->

## How today's workshop is wired

<div style="display:flex;gap:36px;align-items:flex-start;flex:1;min-height:0">
<div style="flex:0 0 770px">
<svg class="arch-diagram" viewBox="0 0 780 540" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Your laptop runs the Streamlit UI, a local EHR API and the lab agent service. The agent service runs your agent on watsonx Orchestrate in the shared TechZone account. The local EHR API and the agent's tools both reach the shared EHR on Code Engine with your tenant header." style="width:100%;height:auto;display:block">
<style>
.arch-diagram { font-family: 'IBM Plex Sans', sans-serif; color: inherit; }
.arch-diagram text { fill: currentColor; font-size: 17px; }
.arch-diagram text.b { font-size: 19px; font-weight: 600; }
.arch-diagram text.muted { fill: #8d8d8d; }
.arch-diagram text.zone { fill: #8d8d8d; font-size: 17px; font-weight: 600; letter-spacing: 0.02em; }
.arch-diagram text.on-accent { fill: #fff; }
.arch-diagram text.edge-label { font-size: 16px; fill: #8d8d8d; }
.arch-diagram text.edge-label.accent { fill: #4589ff; }
.arch-diagram .node { fill: none; stroke: currentColor; stroke-width: 1.5px; }
.arch-diagram .node.fill { fill: rgba(141,141,141,0.18); stroke: none; }
.arch-diagram .node.accent { fill: #0f62fe; stroke: none; }
.arch-diagram .group { fill: none; stroke: #8d8d8d; stroke-width: 1.5px; stroke-dasharray: 6 6; }
.arch-diagram .edge { fill: none; stroke: currentColor; stroke-width: 2px; marker-end: url(#arch-arrow); }
.arch-diagram .edge.accent { stroke: #0f62fe; marker-end: url(#arch-arrow-accent); }
.arch-diagram .edge.muted { stroke: #8d8d8d; marker-end: url(#arch-arrow-muted); }
.arch-diagram .edge.dashed { stroke-dasharray: 8 6; }
</style>
<defs>
<marker id="arch-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="currentColor"/></marker>
<marker id="arch-arrow-accent" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#0f62fe"/></marker>
<marker id="arch-arrow-muted" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#8d8d8d"/></marker>
</defs>
<!-- zone 1: the student's laptop (x 0-330) -->
<rect class="group" x="1" y="1" width="329" height="538"/>
<text class="zone" x="24" y="32">YOUR LAPTOP</text>
<rect class="node" x="24" y="52" width="282" height="116"/>
<text class="b" x="44" y="84">Lab agent service :8001</text>
<text x="44" y="112">starts the run, validates JSON,</text>
<text x="44" y="138">stores concerns locally</text>
<rect class="node" x="24" y="224" width="282" height="84"/>
<text class="b" x="44" y="258">Streamlit UI :8501</text>
<text x="44" y="286">Run Agent, review concerns</text>
<rect class="node" x="24" y="364" width="282" height="84"/>
<text class="b" x="44" y="398">Local EHR API :8000</text>
<text x="44" y="426">thin forwarder</text>
<rect class="node fill" x="24" y="464" width="282" height="56"/>
<text x="44" y="488"><tspan font-weight="600">.env</tspan>  API key · instance URL</text>
<text x="44" y="510">seat prefix · EHR tenant</text>
<line class="edge" x1="165" y1="224" x2="165" y2="168"/>
<line class="edge" x1="165" y1="308" x2="165" y2="364"/>
<!-- zone 2: IBM Cloud, TechZone (x 420-780, y 0-236) -->
<rect class="group" x="420" y="1" width="359" height="235"/>
<text class="zone" x="444" y="32">IBM CLOUD · TECHZONE (ca-tor)</text>
<rect class="node accent" x="444" y="52" width="312" height="160"/>
<text class="b on-accent" x="464" y="84">watsonx Orchestrate</text>
<text class="on-accent" x="464" y="112">studentN_lakeview_inbox_agent</text>
<text class="on-accent" x="464" y="138">ReAct loop + LLM calls</text>
<text class="on-accent" x="464" y="164">prefixed tools + connection</text>
<text class="on-accent" x="464" y="190" opacity="0.8">shared by ~34 seats</text>
<line class="edge accent" x1="306" y1="110" x2="444" y2="110"/>
<text class="edge-label accent" x="375" y="98" text-anchor="middle">runs API</text>
<text class="edge-label accent" x="375" y="132" text-anchor="middle">IAM key</text>
<!-- zone 3: shared EHR on Code Engine (x 420-780, y 300-540) -->
<rect class="group" x="420" y="300" width="359" height="239"/>
<text class="zone" x="444" y="331">CODE ENGINE · us-south</text>
<rect class="node" x="444" y="348" width="312" height="168"/>
<text class="b" x="464" y="380">Shared EHR (FastAPI)</text>
<text x="464" y="408">patient records in memory</text>
<text x="464" y="434">a private copy per tenant,</text>
<text x="464" y="460">keyed by X-Tenant</text>
<text class="muted" x="464" y="490">no agent logic, no UI</text>
<line class="edge" x1="306" y1="406" x2="444" y2="406"/>
<text class="edge-label" x="375" y="394" text-anchor="middle">records</text>
<text class="edge-label" x="375" y="428" text-anchor="middle">X-Tenant</text>
<line class="edge accent" x1="716" y1="212" x2="716" y2="348"/>
<text class="edge-label accent end" x="702" y="262" text-anchor="end">tools send X-Tenant</text>
<text class="edge-label accent end" x="702" y="284" text-anchor="end">from your connection</text>
</svg>
</div>
<div style="flex:1;min-width:0">
<p style="font-size:0.75em;margin:0 0 0.4em"><strong>Both paths send your tenant</strong>, so the UI and the cloud agent see the same private data.</p>
<p style="font-size:0.75em;margin:1em 0 0.4em"><strong>In production, instead:</strong></p>
<ul style="margin-left:1em;width:auto">
<li style="font-size:0.7em;margin-bottom:0.6em">A real system of record (FHIR API) with OAuth / SMART-on-FHIR per user, not a tenant header</li>
<li style="font-size:0.7em;margin-bottom:0.6em">UI and agent service hosted centrally behind SSO, not on laptops</li>
<li style="font-size:0.7em;margin-bottom:0.6em">Concerns in a governed database; secrets in a vault, not <code>.env</code></li>
<li style="font-size:0.7em;margin-bottom:0.6em">An instance per team, not one shared account where every seat is admin</li>
</ul>
</div>
</div>

Note: Before we build, here's how the pieces you'll run today fit together. Three places. On your laptop: the Streamlit UI on 8501, a local EHR API on 8000, and the lab agent service on 8001. Your .env holds your IBM Cloud API key, your Orchestrate instance URL, your seat prefix like student0_, and your EHR tenant, which is just a SHA-256 fingerprint of your key. When you click Run Agent, the agent service starts a run on watsonx Orchestrate in the shared TechZone account in Toronto. Your agent, studentN_lakeview_inbox_agent, runs its ReAct loop and LLM calls there, with your prefixed tools and your prefixed connection. When the tools need patient data, they call the shared EHR on Code Engine, an instructor-owned FastAPI service in Dallas, sending your tenant from the connection. The UI reads patient data through the local EHR API, which forwards to the same service with the same tenant, so the UI and the cloud agent see the same private copy. The agent service validates the JSON that comes back and stores concerns locally in a JSON file. Now, what would change in production? The EHR would be a real system of record, say a FHIR API, with real per-user auth like SMART-on-FHIR instead of a fingerprint header. The UI and agent service would be hosted centrally behind SSO. Concerns go to a governed database and credentials to a secrets manager or platform connections, not a .env file. And each team would get its own instance, not one shared account where every seat is admin. We made these shortcuts so 34 people could get running in ten minutes; none of them are what you'd ship.

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

<!-- .slide: id="lab1-why-orchestrate" -->

## Lab 1: Why Orchestrate?

The ReAct loop (observe, reason, act, repeat) needs something to run it. On watsonx Orchestrate, you describe the agent in a YAML file, and Orchestrate runs the loop.

<div style="display:flex;gap:32px;align-items:flex-start">
<div style="flex:1;min-width:0;font-size:1.45em">

```yaml
# lab1/agent/agent.yaml (excerpt)
kind: native
name: lakeview_inbox_agent
style: react_core
llm: virtual-model/anthropic/claude-sonnet-5-5
instructions: |
  You are a clinical inbox assistant ...
tools:
  - list_patients
  - get_patient_record
```

</div>
<div style="flex:1;min-width:0;font-size:0.95em">

- Orchestrate runs the loop. Your code starts a run and reads the answer.
- Tools run in IBM Cloud. Credentials live in a connection.
- Every run is traced automatically.
- Controls and plug-ins act on the agent's input and output.
- Models come from Orchestrate's model catalog.
- You can't set a breakpoint in a tool. You read the trace instead.

</div>
</div>

Note: There's an open-source edition of this workshop with a fully local LangGraph version of this agent. If you want to read that code, go look at it there. It's designed to run on a laptop, so we didn't use it in a hosted setting like this one.

Here, the agent is this YAML file: instructions, a model, and a list of tools. Orchestrate runs the loop and the tools, and it keeps a trace of every run. You can't step through it in a debugger, so you'll use the traces in Lab 2.

---

<!-- .slide: id="lab1-anatomy" -->

## Anatomy of an Orchestrate agent

<svg class="anat-diagram" viewBox="0 0 1180 548" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="On your machine, deploy.py reads agent.yaml, tools.py and connection.yaml and imports them into watsonx Orchestrate. agent.py starts runs through the runs API. In Orchestrate, the agent's ReAct loop calls the tool runtime, which uses the connection's credentials to call the shared EHR. Every LLM call and tool call is recorded in traces." style="width:100%;max-height:560px;height:auto;display:block">
<style>
.anat-diagram { font-family: 'IBM Plex Sans', sans-serif; color: inherit; }
.anat-diagram text { fill: currentColor; font-size: 17px; }
.anat-diagram text.b { font-size: 19px; font-weight: 600; }
.anat-diagram text.mono { font-family: 'IBM Plex Mono', monospace; font-size: 18px; font-weight: 600; }
.anat-diagram text.muted { fill: #8d8d8d; }
.anat-diagram text.zone { fill: #8d8d8d; font-size: 17px; font-weight: 600; letter-spacing: 0.02em; }
.anat-diagram text.on-accent { fill: #fff; }
.anat-diagram text.edge-label { font-size: 16px; fill: #8d8d8d; }
.anat-diagram text.edge-label.accent { fill: #4589ff; }
.anat-diagram .node { fill: none; stroke: currentColor; stroke-width: 1.5px; }
.anat-diagram .node.fill { fill: rgba(141,141,141,0.18); stroke: none; }
.anat-diagram .node.accent { fill: #0f62fe; stroke: none; }
.anat-diagram .group { fill: none; stroke: #8d8d8d; stroke-width: 1.5px; stroke-dasharray: 6 6; }
.anat-diagram .edge { fill: none; stroke: currentColor; stroke-width: 2px; marker-end: url(#anat-arrow); }
.anat-diagram .edge.accent { stroke: #0f62fe; marker-end: url(#anat-arrow-accent); }
.anat-diagram .edge.muted { stroke: #8d8d8d; marker-end: url(#anat-arrow-muted); }
.anat-diagram .edge.dashed { stroke-dasharray: 8 6; }
</style>
<defs>
<marker id="anat-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="currentColor"/></marker>
<marker id="anat-arrow-accent" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#0f62fe"/></marker>
<marker id="anat-arrow-muted" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#8d8d8d"/></marker>
</defs>
<!-- zone 1: your machine (x 0-330) -->
<rect class="group" x="1" y="1" width="329" height="546"/>
<text class="zone" x="24" y="32">YOUR MACHINE</text>
<rect class="node" x="24" y="52" width="282" height="76"/>
<text class="mono" x="44" y="82">agent.py</text>
<text x="44" y="110">starts runs, checks the JSON</text>
<rect class="node" x="24" y="164" width="282" height="76"/>
<text class="mono" x="44" y="194">deploy.py</text>
<text x="44" y="222">imports the three files below</text>
<line class="edge muted" x1="165" y1="300" x2="165" y2="240"/>
<text class="edge-label" x="177" y="276">reads</text>
<rect class="node fill" x="24" y="300" width="282" height="72"/>
<text class="mono" x="44" y="330">agent.yaml</text>
<text x="44" y="358">instructions · model · tools</text>
<rect class="node fill" x="24" y="384" width="282" height="72"/>
<text class="mono" x="44" y="414">tools.py</text>
<text x="44" y="442"><tspan font-family="'IBM Plex Mono', monospace">@tool</tspan> functions</text>
<rect class="node fill" x="24" y="468" width="282" height="72"/>
<text class="mono" x="44" y="498">connection.yaml</text>
<text x="44" y="526">EHR URL + your tenant</text>
<!-- zone 2: watsonx Orchestrate (x 420-860) -->
<rect class="group" x="420" y="1" width="439" height="546"/>
<text class="zone" x="444" y="32">WATSONX ORCHESTRATE</text>
<rect class="node accent" x="444" y="52" width="392" height="120"/>
<text class="b on-accent" x="464" y="84">Agent: ReAct loop + LLM</text>
<text class="on-accent" x="464" y="112">studentN_lakeview_inbox_agent</text>
<text class="on-accent" x="464" y="140" opacity="0.85">Claude Sonnet 5.5 through the model gateway</text>
<rect class="node" x="476" y="236" width="138" height="100"/>
<text class="b" x="490" y="268">Connections</text>
<text x="490" y="296">base URL,</text>
<text x="490" y="320">tenant</text>
<rect class="node" x="666" y="236" width="170" height="100"/>
<text class="b" x="684" y="268">Tool runtime</text>
<text x="684" y="296">runs your</text>
<text x="684" y="320"><tspan font-family="'IBM Plex Mono', monospace">@tool</tspan> code</text>
<rect class="node fill" x="444" y="412" width="392" height="112"/>
<text class="b" x="464" y="444">Traces</text>
<text x="464" y="472">every LLM call and tool call,</text>
<text x="464" y="498">with inputs and outputs</text>
<!-- edges inside Orchestrate -->
<line class="edge" x1="751" y1="172" x2="751" y2="236"/>
<text class="edge-label" x="763" y="210">tool calls</text>
<line class="edge" x1="614" y1="286" x2="666" y2="286"/>
<line class="edge muted dashed" x1="458" y1="172" x2="458" y2="412"/>
<line class="edge muted dashed" x1="751" y1="336" x2="751" y2="412"/>
<!-- machine to Orchestrate -->
<line class="edge accent" x1="306" y1="92" x2="444" y2="92"/>
<text class="edge-label accent" x="375" y="80" text-anchor="middle">runs API</text>
<line class="edge accent" x1="306" y1="202" x2="420" y2="202"/>
<text class="edge-label accent" x="363" y="190" text-anchor="middle">import</text>
<!-- zone 3: shared EHR (x 940-1180) -->
<rect class="group" x="940" y="1" width="239" height="546"/>
<text class="zone" x="964" y="32">CODE ENGINE</text>
<rect class="node" x="964" y="226" width="192" height="120"/>
<text class="b" x="982" y="258">Shared EHR</text>
<text x="982" y="286">a private copy</text>
<text x="982" y="312">per tenant</text>
<line class="edge" x1="836" y1="286" x2="964" y2="286"/>
<text class="edge-label" x="900" y="274" text-anchor="middle">HTTPS</text>
<text class="edge-label" x="900" y="308" text-anchor="middle">X-Tenant</text>
</svg>

Note: Here's what lives where. On your machine, agent.yaml is the agent definition, tools.py has the tools, and connection.yaml sets up the connection to the EHR. deploy.py adds your seat prefix and imports all three into Orchestrate. agent.py starts a run and checks the JSON that comes back.

In Orchestrate, the agent runs the loop with Claude Sonnet 5.5. When it calls a tool, Orchestrate runs your tool code, and the tool calls the shared EHR with your tenant. Every LLM call and tool call shows up in the trace. We'll look at those in Lab 2.

---

<!-- .slide: id="lab1-tools-and-schema" -->

## Lab 1: Tools and the Output Contract

Each function in `tools.py` decorated with `@tool` (from the Orchestrate ADK) does three things: registers it as callable, generates a JSON schema from type hints and docstring, and lets `deploy.py` import it into Orchestrate. The agent decides which tools to call and in what order — we don't script that.

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

LLMs generate one token at a time. Some inference services offer **constrained decoding** (the server masks tokens that would break the schema). It's the difference between asking someone to drive the speed limit and installing a speed governor.

Without it, we recommend: **prompt with the schema, validate, retry once.**

- `deploy.py` builds the JSON schema from `models.py` and adds it to the agent's instructions
- `agent.py` checks every answer against the Pydantic model, and retries once with the error

For a background agent with no human watching, this isn't a nice-to-have. If the output doesn't parse at 3 AM, nobody finds out.

Quick test: `uv run python scripts/check_structured_outputs.py --patients 3 --skip-judges`

Note: Constrained decoding is something the inference server does. Our agent on Orchestrate doesn't have it, so our code does the checking. When we tested this agent on gpt-oss-120b, the model we started with, 20 of 24 answers were valid on the first try, and all 24 were valid after one retry. The quick test runs your agent on three patients and prints the same numbers for today's model.

There are signs constrained outputs may come back to the mainstream: [Jev](https://opentweet.io/jev/vs-openai-structured-outputs)

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

<!-- .slide: id="lab2-orchestrate-traces" -->

## Lab 2: Traces in Orchestrate

Orchestrate traces every run of your agent. There's no code to add.

Each trace has:

- the run, from start to answer
- every LLM call: model, input, output, token counts
- every tool call: arguments and the full output

You can read traces in the Orchestrate UI, with `orchestrate observability traces` in the CLI, or through the API.

Traces show tokens, but not cost. To estimate cost, multiply tokens by the model's price.

Note: In the open-source edition, this lab is about adding tracing to the agent. Here it's already on. Run the agent on a patient, then open the trace and find your agent by its seat prefix. Look at what the tool returned. You'll see the whole patient record in there.

---

<!-- .slide: id="lab2-traces-are-phi" -->

## Lab 2: Traces Are PHI

Open a trace and look at the tool output. It's the patient's full record: name, date of birth, phone, insurance ID, conditions, messages.

In this workshop's Orchestrate instance:

- every seat can see every seat's traces
- traces are kept for 30 days

Treat the trace store like any other copy of patient data. Follow the data:

<p style="font-size:0.85em;margin-left:1em"><strong>EHR</strong> → tool output → model context → <strong>trace store</strong> → answer → concerns file</p>

At each step, ask: who can read it, how long is it kept, and what was removed before it got there?

Note: This is data provenance. Before you put an agent in front of real patient data, trace where that data goes and what happens to it at each step. Here, the full record goes from the EHR into the tool output, into the model, into the trace, and parts of it end up in the answer and in the concerns file on your laptop. The data is synthetic today, so it's fine that everyone can see each other's traces. With real patients, that's a breach.

---

<!-- .slide: id="lab2-policy-engine" -->

## Lab 2: Gateway and policy in Orchestrate

<svg class="gw-diagram" viewBox="0 0 1180 562" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="A run goes from the caller through Controls at agent_pre_invoke, where the PII Filter masks what the user types, to the agent's ReAct loop. The agent's LLM calls go through the model gateway; its tool calls go through the tool runtime to the shared EHR. The answer goes through your plug-in at agent_post_invoke, which masks phone, email, date of birth and member ID, and then to the caller. Control hooks after tools and after the agent did not run in our tests. Every step writes to the trace store, which holds raw tool output and LLM context, is visible tenant-wide, and keeps traces 30 days. Patient messages reach the model as tool output, and no control checks tool output." style="width:100%;max-height:540px;height:auto;display:block">
<style>
.gw-diagram { font-family: 'IBM Plex Sans', sans-serif; color: inherit; }
.gw-diagram text { fill: currentColor; font-size: 16px; }
.gw-diagram text.b { font-size: 18px; font-weight: 600; }
.gw-diagram text.mono { font-family: 'IBM Plex Mono', monospace; font-size: 15px; }
.gw-diagram text.muted { fill: #8d8d8d; }
.gw-diagram text.on-accent { fill: #fff; }
.gw-diagram text.ok { fill: #4589ff; font-weight: 600; }
.gw-diagram text.bad { fill: #fa4d56; font-weight: 600; }
.gw-diagram text.edge-label { font-size: 15px; fill: #8d8d8d; }
.gw-diagram .node { fill: none; stroke: currentColor; stroke-width: 1.5px; }
.gw-diagram .node.policy { stroke: #0f62fe; stroke-width: 2.5px; }
.gw-diagram .node.accent { fill: #0f62fe; stroke: none; }
.gw-diagram .node.fill { fill: rgba(141,141,141,0.18); stroke: none; }
.gw-diagram .node.phi { fill: rgba(250,77,86,0.12); stroke: #fa4d56; stroke-width: 1.5px; }
.gw-diagram .node.norun { fill: none; stroke: #fa4d56; stroke-width: 1.5px; stroke-dasharray: 5 4; }
.gw-diagram .edge { fill: none; stroke: currentColor; stroke-width: 2px; marker-end: url(#gw-arrow); }
.gw-diagram .edge.both { marker-start: url(#gw-arrow); }
.gw-diagram .edge.muted { stroke: #8d8d8d; marker-end: url(#gw-arrow-muted); }
.gw-diagram .edge.dashed { stroke-dasharray: 7 5; }
.gw-diagram .edge.warn { stroke: #fa4d56; stroke-dasharray: 5 4; marker-end: none; }
</style>
<defs>
<marker id="gw-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="currentColor"/></marker>
<marker id="gw-arrow-muted" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#8d8d8d"/></marker>
</defs>
<!-- row 0: model gateway above the agent -->
<rect class="node fill" x="380" y="2" width="580" height="96"/>
<text class="b" x="400" y="32">Model gateway <tspan class="muted" font-weight="400">(public preview)</tspan></text>
<text x="400" y="58">model policies: fallback · load-balance · retry</text>
<text x="400" y="84">to Claude Sonnet 5.5 through the workshop proxy · granite · …</text>
<text class="muted" x="940" y="32" text-anchor="end">for reliability</text>
<!-- legend -->
<text class="ok" x="0" y="32">✓ worked in our tests</text>
<text class="muted" x="0" y="58">? exists, untested</text>
<text class="bad" x="0" y="84">✗ did not run in our tests</text>
<!-- row 1 -->
<rect class="node" x="0" y="140" width="130" height="160"/>
<text class="b" x="16" y="172">Caller</text>
<text x="16" y="200">runs API</text>
<text x="16" y="224">or chat</text>
<rect class="node policy" x="170" y="140" width="250" height="160"/>
<text class="b" x="186" y="172">Controls</text>
<text class="mono muted" x="186" y="196">agent_pre_invoke</text>
<text x="186" y="228"><tspan class="ok">✓</tspan> PII Filter: masks</text>
<text x="208" y="250">PII the user types</text>
<text x="186" y="280"><tspan class="muted">?</tspan> Guardrails: jailbreak, HAP</text>
<rect class="node accent" x="460" y="140" width="230" height="160"/>
<text class="b on-accent" x="478" y="172">Agent</text>
<text class="on-accent" x="478" y="200">ReAct loop</text>
<text class="on-accent" x="478" y="228">reads tool output,</text>
<text class="on-accent" x="478" y="252">writes the answer</text>
<rect class="node policy" x="730" y="140" width="230" height="160"/>
<text class="b" x="746" y="172">Your plug-in</text>
<text class="mono muted" x="746" y="196">agent_post_invoke</text>
<text x="746" y="222"><tspan class="ok">✓</tspan> masks phone, email,</text>
<text x="768" y="244">DOB, member ID</text>
<rect class="node norun" x="742" y="256" width="206" height="32"/>
<text x="752" y="278"><tspan class="bad">✗</tspan> a control here</text>
<rect class="node" x="1000" y="140" width="180" height="160"/>
<text class="b" x="1016" y="172">Answer</text>
<text x="1016" y="200">back to</text>
<text x="1016" y="224">the caller</text>
<line class="edge" x1="130" y1="220" x2="170" y2="220"/>
<line class="edge" x1="420" y1="220" x2="460" y2="220"/>
<line class="edge" x1="690" y1="220" x2="730" y2="220"/>
<line class="edge" x1="960" y1="220" x2="1000" y2="220"/>
<line class="edge both" x1="575" y1="140" x2="575" y2="98"/>
<text class="edge-label" x="587" y="125">LLM calls</text>
<!-- row 2 -->
<rect class="node" x="460" y="340" width="230" height="110"/>
<text class="b" x="478" y="370">Tool runtime</text>
<text x="478" y="396">your <tspan font-family="'IBM Plex Mono', monospace">@tool</tspan> code</text>
<rect class="node norun" x="472" y="408" width="206" height="32"/>
<text x="482" y="430"><tspan class="bad">✗</tspan> tool_post_invoke</text>
<line class="edge both" x1="575" y1="300" x2="575" y2="340"/>
<text class="edge-label" x="587" y="326">tool calls</text>
<rect class="node" x="730" y="340" width="170" height="110"/>
<text class="b" x="746" y="370">Shared EHR</text>
<text x="746" y="396">full patient</text>
<text x="746" y="420">record</text>
<line class="edge both" x1="690" y1="395" x2="730" y2="395"/>
<!-- indirect injection callout -->
<rect class="node phi" x="1000" y="322" width="180" height="146"/>
<text class="b" x="1014" y="350">Injection path</text>
<text x="1014" y="376">Patient messages</text>
<text x="1014" y="398">reach the agent as</text>
<text x="1014" y="420">tool output. No</text>
<text x="1014" y="442">control checks it.</text>
<!-- trace store -->
<rect class="node phi" x="170" y="492" width="1010" height="68"/>
<text class="b" x="190" y="520">Trace store</text>
<text x="190" y="546">raw tool output + LLM context = PHI · every seat can see it · kept 30 days</text>
<line class="edge muted dashed" x1="295" y1="300" x2="295" y2="492"/>
<line class="edge muted dashed" x1="575" y1="450" x2="575" y2="492"/>
<line class="edge muted dashed" x1="940" y1="300" x2="940" y2="492"/>
</svg>

Note: Here's what we actually tested. The PII Filter control runs before the agent, and it masked PII that the user typed. The Content Guardrails control exists, for jailbreak and hate, abuse and profanity, but we didn't test it. Control hooks after a tool call and after the agent were accepted when we set them up, but they never ran. A Python plug-in after the agent did run, and it masked phone numbers, emails, dates of birth and member IDs in the answer.

The model gateway is for reliability: falling back to another provider, load balancing, retries. It doesn't apply any policy to the content.

Two things to notice. Everything goes into the trace store before any masking happens. And patient messages come back to the agent as tool output, which nothing checks. That's where prompt injection would come from in this agent.

---

<!-- .slide: id="lab2-pii-layers" -->

## Lab 2: Three Places to Remove PHI

<table style="font-size:0.7em">
<tr><td></td><td><strong>Runs</strong></td><td><strong>Model</strong></td><td><strong>Trace</strong></td><td><strong>Answer</strong></td></tr>
<tr><td><strong>Control:</strong> PII Filter</td><td>before the agent, on user input</td><td>user input only</td><td>✗</td><td>✗</td></tr>
<tr><td><strong>Plug-in</strong> (Python)</td><td>after the agent, on the answer</td><td>✗</td><td>✗</td><td>✓ identifiers</td></tr>
<tr><td><strong>Minimize at the source</strong></td><td>in the tool or the EHR</td><td>✓</td><td>✓</td><td>✓</td></tr>
</table>

- The PII Filter and the plug-in use patterns. They catch phone numbers and IDs, not names.
- Only the tool can keep PHI out of the model and the trace. If the tool doesn't return it, nothing downstream has it.

Note: The control and the plug-in are useful, but look at the trace column. Neither one changes what's in the trace. The only way to keep PHI out of the trace is to have the tool return less. That's one reason Lab 3 replaces the tool that returns the whole record.

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

On Orchestrate, every tool output goes into the trace. To log less, return less from your tools.

---

<!-- .slide: id="lab2-what-traces-show" -->

## Lab 2: What Traces Actually Show You

Traces show you things you can't see any other way:

- **Tool call order** — did the agent investigate, or stop after one call?
- **The implicit summarization problem** — compare what tools returned (ground truth) to what the agent concluded. Discrepancies are visible by eye. Lab 3 automates catching them.
- **The invisible prompt** — the doctor never sees the message the agent acted on. If the prompt is poorly written or biased, the trace is where you find out.
- **Tokens per run** — at scale, "the agent runs on every patient every day" adds up fast.

---

<!-- .slide: id="lab2-datasets" -->

## Lab 2: Traces as Evaluation Data

Traces aren't just for debugging right now — they're raw material for getting better over time.

- Save good and bad runs as examples. Over time you have a set of real agent behavior to test new versions against.
- When a clinician spots a wrong concern, record what went wrong. That's feedback from the domain expert to the engineering team.

And then there's **LLM-as-Judge**: use another LLM to check the agent's output at scale. We'll build this in Lab 3, from the same data you see in the trace.

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

This is the inner loop of the ADLC's Operations & Governance phase. Each improvement in this lab starts from something you can see in a trace.

Observability only pays off if you act on what you find.

---

<!-- .slide: id="lab3-what-we-found" -->

## Lab 3: What to Look For in the Traces

Things to check in your Lab 2 traces:

**1. Made-up evidence.** Compare the tool output (what the data says) to the agent's concerns (what it claims). Look for lab values or dates that aren't in the record.

**2. Off-task answers.** The instructions say not to make clinical recommendations. Look for suggested diagnoses or treatments anyway. A system prompt is a request, not a constraint.

**3. One big tool call.** `get_patient_record` returns the whole record — demographics, all conditions, all labs, all messages. Our agent usually calls it once and stops. More data in context means more chances to make things up.

---

<!-- .slide: id="lab3-prompt-injection" -->

## Lab 3: Prompt Injection — Reduced by Design

You might wonder whether a patient could craft a portal message to hijack the agent.

In this system, the risk is reduced by a deliberate architectural decision: the agent runs in the background, and its output goes to the **doctor** — not back to the patient. The patient never sees agent output, so there's no feedback loop to exploit.

The patient's message still reaches the agent, as tool output. Nothing on the platform checks tool output, so the agent's instructions and the doctor's review are what stand in the way.

---

<!-- .slide: id="lab3-focused-tools" -->

## Lab 3: Focused Tools Force Intentional Investigation

Replace `get_patient_record` with keyword-based search tools: `search_conditions`, `search_labs`, `search_medications`. The agent has to say what it's looking for before it gets any data.

Instead of drowning in everything at once, it has to reason first: "The patient mentioned fatigue — let me check thyroid conditions and TSH labs." This is investigation, not retrieval.

Fewer tokens in context means lower cost, less hallucination surface area, and less PHI in the traces.

---

<!-- .slide: id="lab3-critic" -->

## Lab 3: Checks as Judge Agents

Each check is its own agent on Orchestrate, with no tools and its own output schema:

1. **Claim extractor** — pulls out every specific, checkable medical claim in each concern. Vague descriptions ("recent lab results") are dropped. You can't check something that doesn't say anything specific.

2. **Grounding judge** (LLM-as-judge) — checks each claim against the patient's record. Is that lab value really there?

3. **Critic** — looks at the grounding results and whether the concern stays on task, and writes feedback for the agent.

Why extract claims first? The judge returns one verdict per claim, so you can tell *which part* of a concern is wrong.

Note: These three are prompts plus a schema, deployed as agents with no tools. You send each one a concern and the patient's data and get structured JSON back, checked the same way as in Lab 1.

---

<!-- .slide: id="lab3-judge-bias" -->

## Lab 3: Who Checks the Checker?

Our judges run on the same model as the agent: Claude Sonnet 5.5. A model checking its own kind of output has a bias. It tends to make the same mistakes it's looking for.

Ways to reduce it:

- a judge from a different model family (Orchestrate's catalog has more than one)
- a model trained for the check, such as a groundedness detector
- a clinician reviewing a sample of verdicts

Judges cut down on what reaches the doctor. The doctor is still the one who decides.

Note: In the open-source edition, there's an option to check grounding with Granite Guardian running locally. It's a model trained to detect ungrounded claims. We're not running it today. Here, the judge is the same model as the agent, so keep that bias in mind when you read its verdicts.

---

<!-- .slide: id="section-lab-4" data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Lab 4</p>

# Securing Data

Who can read what the agent knows? A discussion.

</div>

---

<!-- .slide: id="lab4-output-is-sensitive" -->

## Lab 4: Agent Output Is Sensitive Data

We've been protecting the patient records the agent reads. But the concerns the agent writes are also sensitive — they're clinical findings derived from patient data.

In Labs 1-3, the agent writes to a flat JSON file. Any code path can read or overwrite any patient's concerns. Run the agent twice and the first run's output is gone.

In a multi-provider practice, provider A's agent may reach a different conclusion about the same patient than provider B. That's clinically significant. Those conclusions need access control — and they need to be stable across runs.

---

<!-- .slide: id="lab4-storage-guarantees" -->

## Lab 4: Where Does the Agent's Data Live?

<table style="font-size:0.72em">
<tr><td><strong>Data</strong></td><td><strong>Stored in</strong></td><td><strong>What we saw today</strong></td></tr>
<tr><td>Traces: tool output, LLM context</td><td>watsonx Orchestrate</td><td>every seat can read them, kept 30 days</td></tr>
<tr><td>Agent, tools, connection</td><td>watsonx Orchestrate</td><td>credentials in the connection</td></tr>
<tr><td>Patient records</td><td>shared EHR on Code Engine</td><td>a copy per tenant, keyed by a header</td></tr>
<tr><td>Concerns</td><td>a JSON file on your laptop</td><td>no access control, no audit log</td></tr>
</table>

Questions to ask your platform, for each one:

- Where is it stored, and in which region?
- Who can read it? Can you limit that per user?
- How long is it kept? How do you delete it, including backups and exports?
- Is it encrypted at rest and in transit? Who holds the keys?

Note: Ask these about every place the agent's data ends up, including traces. Get the answers from the vendor's documentation. IBM's watsonx data security page says data at rest is encrypted by default, and that you can bring your own keys with Key Protect. Check what applies to the specific service you use. For Orchestrate traces, what we saw in this account is that every seat can read them and they're kept for 30 days.

Sources: https://dataplatform.cloud.ibm.com/docs/content/wsj/getting-started/security-data.html?context=wx

---

<!-- .slide: id="lab4-data-layer" -->

## Lab 4: Access Control Belongs in the Data Layer

You can put a rule like "Rachel Torres can't see Dr. Kim's concerns" in four places:

- **The prompt.** A request to the model. Text in a patient message can override it.
- **The UI.** Every other path to the data skips it.
- **The application's queries.** Forget the `WHERE` clause once, and data leaks.
- **The data layer.** The store checks every read and write, whichever code asks.

For example, Postgres row-level security applies a policy to every query, including ones you haven't written yet. The default is deny. Sharing a concern writes an explicit grant, and that grant is a record you can audit.

Note: The repository has a Lab 4 schema with a row-level security policy if you want to read one. We're not running a database today. I want you to know the rule can live in one place, in the store.

---

<!-- .slide: id="lab4-identity" -->

## Lab 4: Identity End to End

The agent acts for a clinician. Its tools should fetch only what that clinician could fetch.

- **The identity comes from the session.** The model never fills it in. If it's a tool argument, a prompt injection can change it.
- **The check happens below the agent.** The data layer decides what comes back.

Today, neither is true:

- Your tools send your tenant, which separates students. It doesn't identify a clinician.
- Within your tenant, the tools can read any patient. `list_patients` and `get_inbox` return conditions and message subjects for every patient.

Note: Patient Elena Vasquez's message mentions her neighbor, Patricia Kowalski. Nothing today stops the agent from looking up Patricia's record while it reviews Elena. The Lab 4 code in the repository scopes tools to one patient, but even there the clinic directory tools return every patient's conditions. A real fix needs the clinician's identity checked in the record system.

---

<!-- .slide: id="lab4-production" -->

## Lab 4: In Production

- Each clinician signs in, with OAuth or SMART on FHIR, and that identity reaches the record system on every tool call
- Concerns go in a store with access control by clinician, an audit log, and a retention rule
- Traces get the same treatment: limit who can read them, minimize what goes in, and set how long they're kept
- Credentials live in the platform's connections or a secrets manager, not in `.env`
- Each team gets its own Orchestrate instance and only the roles it needs

---

<!-- .slide: id="further-lifecycle" -->

## Going further on watsonx

<style>
.reveal .further { font-size: 0.95em; line-height: 1.35; }
.reveal .further.detail { font-size: 0.9em; }
.reveal .further .ok { color: #4589ff; font-weight: 600; }
.reveal .further .unt { color: #8d8d8d; font-weight: 600; }
.reveal .further .cols { display: flex; gap: 28px; }
.reveal .further .col { flex: 1; min-width: 0; border-top: 4px solid #0f62fe; padding-top: 0.5em; }
.reveal .further .step { margin: 0; font-weight: 600; font-size: 1.3em; }
.reveal .further .q { margin: 0.15em 0 0.3em; font-style: italic; }
.reveal .further .prod { margin: 0 0 0.7em; opacity: 0.7; font-size: 0.85em; }
.reveal .further ul { list-style: none; margin: 0 !important; padding: 0 !important; display: block; }
.reveal .further li { list-style: none; margin: 0 0 0.5em !important; padding-left: 1.2em; text-indent: -1.2em; }
.reveal .further li::marker { content: none; }
.reveal .further .legend { margin: 1.4em 0 0; font-size: 0.85em; }
.reveal .further code { font-size: 0.9em; }
</style>

<div class="further">
<div class="cols">
<div class="col">
<p class="step">1. Document it</p>
<p class="q">Can you show an auditor what this agent is for?</p>
<p class="prod">watsonx.governance</p>
<ul>
<li><span class="unt">?</span> AI use case and factsheets</li>
<li><span class="unt">?</span> AI Risk Atlas</li>
</ul>
</div>
<div class="col">
<p class="step">2. Test it</p>
<p class="q">Does it still behave after a change?</p>
<p class="prod">Orchestrate, watsonx.governance</p>
<ul>
<li><span class="ok">✓</span> Judge agents (Lab 3)</li>
<li><span class="unt">?</span> Evaluations and rubrics</li>
<li><span class="unt">?</span> Red-teaming</li>
<li><span class="unt">?</span> Governance metrics SDK</li>
</ul>
</div>
<div class="col">
<p class="step">3. Constrain it</p>
<p class="q">What can it never do?</p>
<p class="prod">Orchestrate</p>
<ul>
<li><span class="ok">✓</span> PII Filter control</li>
<li><span class="ok">✓</span> Plug-ins</li>
<li><span class="unt">?</span> Content Guardrails</li>
<li><span class="unt">?</span> Context variables for identity</li>
<li><span class="unt">?</span> Collaborator agents, workspaces</li>
</ul>
</div>
<div class="col">
<p class="step">4. Watch it</p>
<p class="q">What is it doing once it's live?</p>
<p class="prod">Orchestrate, watsonx.governance, watsonx.ai</p>
<ul>
<li><span class="ok">✓</span> Traces</li>
<li><span class="unt">?</span> Agent monitoring</li>
<li><span class="unt">?</span> Model choice in watsonx.ai Studio</li>
</ul>
</div>
</div>
<p class="legend"><span class="ok">✓ tested today</span> &nbsp;&nbsp; <span class="unt">? documented by IBM, not tested here</span></p>
</div>

Note: Today you built one agent and put some checks around it. If you take an agent like this toward production in a regulated setting, here's how I'd organize the rest of the work: document it, test it, constrain it, watch it.

The checkmarks are things we ran today. The question marks are in IBM's documentation, and I haven't tested them for this workshop. The next two slides go through each one.

---

<!-- .slide: id="further-document-test" -->

## Document it, test it

<div class="further detail">
<div class="cols">
<div class="col">
<p class="step">Document it</p>
<p class="prod">watsonx.governance</p>
<ul>
<li><span class="unt">?</span> <strong>AI use case:</strong> one entry per AI system. It tracks the system's assets through the lifecycle, with a risk level and approval steps.</li>
<li><span class="unt">?</span> <strong>Factsheets:</strong> the record for each model and prompt template, including its history and evaluation results.</li>
<li><span class="unt">?</span> <strong>AI Risk Atlas:</strong> IBM's list of AI risks. The agentic section includes "Sharing IP/PI/confidential information with tools" and "Function calling hallucination".</li>
</ul>
</div>
<div class="col">
<p class="step">Test it</p>
<p class="prod">Orchestrate, watsonx.governance</p>
<ul>
<li><span class="ok">✓</span> <strong>Judge agents:</strong> Lab 3's claim extractor, grounding judge and critic, each an Orchestrate agent.</li>
<li><span class="unt">?</span> <code>orchestrate evaluations evaluate</code>: run test cases, check the tool calls and their order.</li>
<li><span class="unt">?</span> <code>quick-eval</code>: no ground truth needed. Flags schema mismatches and calls to the wrong tool.</li>
<li><span class="unt">?</span> <strong>Rubric evaluations:</strong> an LLM grades each answer against your criteria, such as "no hallucination".</li>
<li><span class="unt">?</span> <code>orchestrate evaluations red-teaming</code>: 15 built-in attacks, mapped to the OWASP Top 10 for LLMs.</li>
<li><span class="unt">?</span> <code>ibm-watsonx-gov</code> SDK: faithfulness, answer relevance, tool call accuracy, PII, HAP.</li>
</ul>
</div>
</div>
<p class="legend"><span class="ok">✓ tested today</span> &nbsp;&nbsp; <span class="unt">? documented by IBM, not tested here</span></p>
</div>

Note: Document it. In watsonx.governance, an AI use case is the entry for one AI system. It holds what the system is for, its risk level, and the assets behind it, and it can go through approval steps. Factsheets are the detailed record for each model and prompt template. This is what an auditor asks for. I haven't checked how an Orchestrate agent shows up in a use case, so try it before you count on it.

The AI Risk Atlas is IBM's list of AI risks. It has a section for agents. Two entries describe our agent: sharing personal information with tools, and function calling hallucination. You can use it to name your risks with the same words everyone else uses.

Test it. The judge agents from Lab 3 are the part we ran. Orchestrate also has an evaluation command. evaluate runs test cases and checks that the agent called the right tools in the right order. quick-eval doesn't need expected answers. It looks for schema mismatches and calls to the wrong tool. Rubric evaluations use an LLM to grade answers against criteria you write. On a hosted instance these run against the draft version of the agent.

Red-teaming runs 15 built-in attacks against your agent, and each one is mapped to the OWASP Top 10 for LLMs. These attacks come in as user input. In our agent, the injection risk is in patient messages, which arrive as tool output, so you'd still need your own tests for that.

The watsonx.governance SDK, ibm-watsonx-gov, has metrics like faithfulness, answer relevance, tool call accuracy, PII and HAP. From our seats it returned a permissions error, so I haven't run it here.

Sources:
- AI use cases: https://ibm.com/docs/en/SSLSRPV_latest/wsj/analyze-data/xgov-use-cases.html and https://www.ibm.com/docs/SSYOK8/wsj/getting-started/use-case-watsonx-gov.html
- AI Risk Atlas: https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas
- Evaluations: https://developer.watson-orchestrate.ibm.com/evaluate/overview.md
- quick-eval: https://developer.watson-orchestrate.ibm.com/evaluate/quick_eval.md
- Rubric evaluations: https://developer.watson-orchestrate.ibm.com/evaluate/rubric.md
- Red-teaming: https://developer.watson-orchestrate.ibm.com/evaluate/llm_vulnerability.md
- ibm-watsonx-gov metrics: https://ibm.github.io/ibm-watsonx-gov/ and https://jp-tok.dataplatform.cloud.ibm.com/docs/content/wsj/model/wxgov-agentic-ai-evaluation-sdk.html?context=wx

---

<!-- .slide: id="further-constrain-watch" -->

## Constrain it, watch it

<div class="further detail">
<div class="cols">
<div class="col">
<p class="step">Constrain it</p>
<p class="prod">Orchestrate</p>
<ul>
<li><span class="ok">✓</span> <strong>PII Filter control:</strong> masks PII the user types. User input only.</li>
<li><span class="ok">✓</span> <strong>Plug-ins:</strong> your Python code before or after the agent.</li>
<li><span class="unt">?</span> <strong>Content Guardrails control:</strong> jailbreak, HAP, harm, social bias and more. It's on our instance.</li>
<li><span class="unt">?</span> <strong>Context variables:</strong> your app passes in the clinician's identity, and the runtime fills it into the tool. The LLM never picks it.</li>
<li><span class="unt">?</span> <strong>Collaborator agents:</strong> the inbox agent calls a critic agent itself.</li>
<li><span class="unt">?</span> <strong>Workspaces:</strong> agents, tools and connections only a team's members can see.</li>
</ul>
</div>
<div class="col">
<p class="step">Watch it</p>
<p class="prod">Orchestrate, watsonx.governance, watsonx.ai</p>
<ul>
<li><span class="ok">✓</span> <strong>Traces:</strong> every LLM call and tool call. Treat them as PHI.</li>
<li><span class="unt">?</span> <strong>Agent monitoring:</strong> success rate, response time and tokens for agents deployed to production. Built on watsonx.governance.</li>
<li><span class="unt">?</span> <strong>Model choice:</strong> watsonx.ai Studio has IBM and open-weights models, and you can deploy your own. Prompt Lab runs the same prompt on any of them.</li>
</ul>
<p style="margin:1em 0 0">The model you pick changes how well the agent investigates. Check again every time you change it.</p>
</div>
</div>
<p class="legend"><span class="ok">✓ tested today</span> &nbsp;&nbsp; <span class="unt">? documented by IBM, not tested here</span></p>
</div>

Note: Constrain it. The PII Filter control and the plug-in are what we ran in Lab 2. The filter only sees what the user types. The Content Guardrails control is on our instance and covers jailbreak, hate, abuse and profanity, harm, and social bias, among others. I haven't tested it.

Context variables are how I'd fix the identity problem from Lab 4. Your app passes the clinician's identity into the run. A Python tool can take it as an argument, and the runtime fills it in, so the model never chooses it. If the identity comes in the signed token, neither a tool nor the API call can overwrite it.

Collaborator agents let one agent call another. The inbox agent could call the critic itself, instead of our code calling it. That's less predictable than our loop, so test it. Workspaces keep a team's agents, tools and connections visible only to that team. We couldn't turn them on in the workshop account.

Watch it. Traces are what we used all day, and they hold patient data. Agent monitoring gives you a dashboard for agents deployed to production: success rate, response time, tokens. IBM says it's powered by watsonx.governance.

Last, the model. The free gpt-oss-120b we tried first often stopped after one look at the record, so it missed things. That's part of why we're on Claude Sonnet 5.5 today. watsonx.ai Studio has a big catalog, including open-weights models, and you can deploy your own. In Prompt Lab you can run the same prompt on different models and look at the answers. Whenever you change the model, run your tests again.

Sources:
- Controls: https://developer.watson-orchestrate.ibm.com/controls/managing_controls.md
- Plug-ins: https://developer.watson-orchestrate.ibm.com/plugins/plugins.md
- Context variables: https://developer.watson-orchestrate.ibm.com/conversation/context_variables.md
- Collaborators: https://developer.watson-orchestrate.ibm.com/agents/build_agent.md
- Workspaces: https://developer.watson-orchestrate.ibm.com/workspaces/overview.md
- Traces: https://developer.watson-orchestrate.ibm.com/traces/overview.md
- Agent monitoring: https://www.ibm.com/new/announcements/now-ga-monitor-agents-in-runtime-in-watsonx-orchestrate
- watsonx.ai models: https://www.ibm.com/products/watsonx-ai · Custom models: https://www.ibm.com/docs/en/SSYOK8/wsj/analyze-data/deploy-custom-fm-cloud.html
- Prompt Lab: https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/fm-prompt-lab.html?context=wx

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
- Structured outputs, checked by your code — no free text, no advice, no drafts
- Doctor stays in the loop at every step

</div>
<div style="flex: 1">

**Each Lab**
- Lab 1: an agent on Orchestrate, with a schema, validation and one retry
- Lab 2: Orchestrate traces; controls, plug-ins, and smaller tool output
- Lab 3: focused tools; grounding and critic checks as judge agents
- Lab 4: where agent data is stored, and identity end to end

</div>
</div>

---

<!-- .slide: id="responsible-by-design" -->

## Responsible by Design

Responsibility isn't something you bolt on at the end.

- **Build** with constraints from day one — structure limits what the agent can say
- **Observe** so you can explain every decision — and defend it
- **Improve** using evidence from real traces, not intuition
- **Secure** the data the agent reads and writes, in the data layer

=====/

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
