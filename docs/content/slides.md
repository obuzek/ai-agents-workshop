---
revealjs:
  presentation: true
---

<!-- .slide: data-background-image="../images/odsc-title.png" data-background-size="contain" data-background-color="#000" -->

---

<!-- .slide: data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Section 1</p>

# AI Development Lifecycle

Understanding how AI systems are built, deployed, and maintained

</div>

---

## What is the ADLC?

The AI Development Lifecycle (ADLC) describes the end-to-end process for designing, building, and operating AI systems responsibly.

- Structured approach to AI system development
- Incorporates governance and ethics at every phase
- Enables repeatable, auditable workflows

Note: Emphasize that ADLC is not just a technical framework — it's a governance and accountability structure.

---

## Phase 1: Problem Definition

- Identify business need and success criteria
- Assess feasibility and data availability
- Define scope, constraints, and stakeholders
- Conduct ethical impact assessment

Note: The problem definition phase is often undervalued. Ethical impact assessment here prevents costly redesigns later.

---

## Phase 2: Data Collection & Preparation

- Identify and gather relevant data sources
- Clean, label, and validate data
- Address bias and representativeness
- Establish data governance and lineage

---

## Phase 3: Model Development

- Select model architecture and approach
- Train, fine-tune, or prompt-engineer
- Evaluate performance and safety metrics
- Iterate based on results

---

## Phase 4: Deployment & Integration

- Package and serve the model
- Integrate with existing systems and workflows
- Set up monitoring and alerting
- Define rollback and incident response plans

---

## Phase 5: Operations & Governance

- Monitor model performance over time
- Detect and address drift and degradation
- Maintain audit trails and documentation
- Periodic re-evaluation and retraining

---

## ADLC for Agents

Agent-based systems introduce additional considerations:

- **Tool access** — what can the agent do?
- **Autonomy level** — when does it act without human approval?
- **Memory & state** — what persists across sessions?
- **Observability** — can you explain what the agent did and why?

Note: These four dimensions map directly to the four labs: build, observe, improve, secure.

---

<!-- .slide: data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Section 2</p>

# Opportunities, Risks & Mitigation

Making informed decisions about where and how to deploy AI agents

</div>

---

## Opportunities

AI agents can unlock significant value when applied thoughtfully:

- Automate repetitive, well-defined tasks at scale
- Augment human decision-making with richer context
- Enable 24/7 responsiveness across systems
- Synthesize information across disparate sources

---

## Risk Categories

- ⚠️ **Safety** — unintended actions in production systems
- 🔒 **Security** — prompt injection, data exfiltration
- ⚖️ **Fairness** — amplifying bias in automated decisions
- 🔍 **Transparency** — inability to explain agent behavior
- 📜 **Compliance** — regulatory and legal exposure

---

## Security Risks in Depth

- **Prompt injection** — malicious input hijacks agent behavior
- **Tool misuse** — agent is tricked into calling dangerous tools
- **Data leakage** — sensitive context exposed in completions
- **Privilege escalation** — agent gains unintended permissions

Note: These are the risks Lab 4 directly addresses. Preview them here so attendees have context before the lab.

---

## Mitigation Strategies

- ✅ Apply least-privilege to all tool access
- ✅ Validate and sanitize all inputs before processing
- ✅ Require human-in-the-loop for high-stakes actions
- ✅ Log all agent decisions with full context
- ✅ Test adversarially before deployment

---

## Responsible Agent Design Principles

- **Transparency** — document what the agent can and cannot do
- **Controllability** — ensure humans can override or stop the agent
- **Accountability** — every action must be attributable and logged
- **Robustness** — degrade gracefully under adversarial conditions

---

<!-- .slide: data-background="#0f62fe" -->

<div style="color:#fff">

<p style="font-size:0.65em;text-transform:uppercase;letter-spacing:0.12em;opacity:0.7">Up Next</p>

# Let's Build

Time for hands-on labs.

[Go to Lab 1 →](../lab-1/)

</div>

---

## Example: Flowchart LR (Lifecycle)

<div class="mermaid">
flowchart LR
    A[Define] --> B[Collect Data]
    B --> C[Develop Model]
    C --> D[Deploy]
    D --> E[Monitor]
    E --> A
</div>

---

## Example: State Diagram

<div class="mermaid">
stateDiagram-v2
    [*] --> Define
    Define --> CollectData
    CollectData --> Develop
    Develop --> Deploy
    Deploy --> Monitor
    Monitor --> Define
</div>

---

## Example: Flowchart TD (Branching)

<div class="mermaid">
flowchart TD
    A[Problem Definition] --> B[Data Collection]
    B --> C[Model Development]
    C --> D[Deployment]
    D --> E[Operations]
    E -->|Retrain| C
    E -->|Redefine| A
</div>

---

## Example: Sequence Diagram

<div class="mermaid">
sequenceDiagram
    User->>Agent: Ask question
    Agent->>LLM: Generate plan
    LLM-->>Agent: Tool call
    Agent->>Tool: Execute
    Tool-->>Agent: Result
    Agent->>LLM: Incorporate result
    LLM-->>Agent: Final answer
    Agent-->>User: Response
</div>

---

## Example: Flowchart with Subgraphs

<div class="mermaid">
flowchart TB
    subgraph Agent
        A[Perceive] --> B[Reason]
        B --> C[Act]
    end
    subgraph Environment
        D[Tools]
        E[Data]
    end
    C --> D
    C --> E
    D --> A
    E --> A
</div>

=====

<style>
.mkdocs-revealjs-wrapper,
.mkdocs-revealjs-wrapper .reveal {
  aspect-ratio: 16 / 9 !important;
  height: auto !important;
  max-height: 80vh;
}
.reveal:fullscreen .slides,
.reveal:-webkit-full-screen .slides {
  height: 100% !important;
  margin-top: 0 !important;
}
.reveal:fullscreen .slides section,
.reveal:-webkit-full-screen .slides section {
  height: 100% !important;
  padding: 40px 5% !important;
}
</style>

**Keyboard shortcuts:** `F` fullscreen · `O` overview · `S` speaker notes · `←` `→` navigate
