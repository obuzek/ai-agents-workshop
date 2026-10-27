# AI Agents Workshop

???+ abstract "What You'll Learn"
    In this hands-on workshop, you'll build an AI agent that helps doctors manage their patient portal inbox — and learn why doing it naively is dangerous. Across four labs, you'll add observability, reliability, and security to a working agent, grounded in real healthcare constraints.

## Which Model We Use

Your agent runs on **Claude Sonnet 5.5**. We use it because it's a high-end model at a reasonable cost.

watsonx Orchestrate can be configured with many different model backends. That includes your choice of open-weights models through watsonx.ai, for example for on-prem setups. In Orchestrate, the model is one line in the agent's definition, so you can try others.

## Workshop Flow

1. [Prerequisites](./prerequisites.md) — Clone the repo, install dependencies, start the EHR inbox
2. [Slides](./slides.md) — AI Development Lifecycle + Opportunities, Risks & Mitigation
3. [Lab 1: The Naive Agent](./lab-1.md) — Build a naive doctor inbox agent and see where it breaks
4. [Lab 2: Observability](./lab-2.md) — Instrument and trace your agent
5. [Lab 3: Improving Your Agent](./lab-3.md) — Check the agent's work with grounding and a critic agent
6. [Lab 4: Securing Data Used By The Agent](./lab-4.md) — Protect the data your agent reads and writes

???+ tip "Time Estimate"
    The workshop runs for 2 hours: ~30 minutes of presentation followed by four ~20-minute labs.

---

## The Problem

Doctors are overwhelmed with patient portal messages. A single message might contain several unrelated questions — some urgent, most routine. Responding to all of them comes on top of a full patient load.

Can we use an AI agent to help? And can we do it **responsibly** — keeping the doctor in the loop, protecting patient data, and avoiding the temptation to let the AI "just handle it"?

---

## Workshop Structure

### [Lab 1: The Naive Agent](./lab-1.md)
Build a background agent that reads patient records and portal messages, identifies concerns, and surfaces them in the inbox UI. No guardrails, no access controls — intentionally problematic.

### [Lab 2: Observability](./lab-2.md)
The naive agent is a black box. Add tracing and structured logging so you can see every decision it makes and inspect its reasoning.

### [Lab 3: Improving Your Agent](./lab-3.md)
Use observability data to identify failure modes. Add a critic agent to evaluate the primary agent's output, and Granite Guardian for groundedness detection.

### [Lab 4: Securing Data Used By The Agent](./lab-4.md)
Agent output is sensitive data too. Discuss why access control belongs in the data layer, not the prompt or the UI: row-level security keyed to the caller, least-privilege credentials, audit logging, and keeping the clinician's identity attached end to end. Then see how the Lab 4 code scopes the agent's tools to one patient.

---

## Additional Resources

- [Additional Resources](./resources.md) — Papers, frameworks, and tools
- [Contributing](./contributing.md) — How to contribute to this workshop

Let's get started! Head to [Prerequisites](./prerequisites.md) to set up your environment.
