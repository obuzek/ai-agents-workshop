# AI Agents Workshop

???+ abstract "What You'll Learn"
    In this hands-on workshop, you'll build an AI agent that helps doctors manage their patient portal inbox — and learn why doing it naively is dangerous. Across four labs, you'll add observability, reliability, and security to a working agent, grounded in real healthcare constraints.

## Workshop Flow

1. [Prerequisites](./prerequisites.md) — Clone the repo, install dependencies, start the EHR inbox
2. [Slides](./slides.md) — AI Development Lifecycle + Opportunities, Risks & Mitigation
3. [Lab 1: The Naive Agent](./lab-1.md) — Build a naive doctor inbox agent and see where it breaks
4. [Lab 2: Observability](./lab-2.md) — Instrument and trace your agent
5. [Lab 3: Improving Your Agent](./lab-3.md) — Add a critic agent and Granite Guardian
6. [Lab 4: Securing Data Used By The Agent](./lab-4.md) — Harden with Postgres RLS and least-privilege access

???+ tip "Time Estimate"
    The workshop runs for 2 hours: ~30 minutes of presentation followed by four ~20-minute labs.

---

## The Problem

Doctors are overwhelmed with patient portal messages. A single message might contain several unrelated questions — some urgent, most routine. Responding to all of them comes on top of a full patient load.

Can we use an AI agent to help? And can we do it **responsibly** — keeping the doctor in the loop, protecting patient data, and avoiding the temptation to let the AI "just handle it"?

---

## Workshop Structure

### Lab 1: The Naive Agent
Build a background agent that reads patient records and portal messages, identifies concerns, and surfaces them in the inbox UI. No guardrails, no access controls — intentionally problematic.

### Lab 2: Observability
The naive agent is a black box. Add tracing and structured logging so you can see every decision it makes and inspect its reasoning.

### Lab 3: Improving Your Agent
Use observability data to identify failure modes. Add a critic agent to evaluate the primary agent's output, and Granite Guardian for content safety.

### Lab 4: Securing Data Used By The Agent
Move from "trust the code" to database-enforced access control with Postgres Row-Level Security. Map the threat model, apply least-privilege, and test against adversarial inputs.

---

## Additional Resources

- [Additional Resources](./resources.md) — Papers, frameworks, and tools
- [Contributing](./contributing.md) — How to contribute to this workshop

Let's get started! Head to [Prerequisites](./prerequisites.md) to set up your environment.
