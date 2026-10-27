# AI Agents Workshop

???+ abstract "What You'll Learn"
    In this hands-on workshop you'll deploy an AI agent to **IBM watsonx Orchestrate** that helps doctors manage their patient portal inbox, and see why the naive version isn't safe to use. Across four labs you'll read the agent's traces, mask patient data, check the agent's work with judge agents, and work out who should be able to reach the data it touches.

## Which Model We Use

Your agent runs on **Claude Sonnet 5.5**. We use it because it's a high-end model at a reasonable cost. In our tests it returned concerns for all 12 patients and took about 40 seconds per patient.

In Orchestrate, the model is one line in the agent's definition (`llm:` in `agent.yaml`). Orchestrate's model gateway can route to many model backends, including open-weights models on watsonx.ai, so you can try another model by changing that line and redeploying. Run your checks again when you do: the first model we tried, gpt-oss-120b, often stopped after one tool call and missed concerns.

## Workshop Flow

1. [Prerequisites](./prerequisites.md): log in to IBM Cloud, run the installer, start the EHR inbox
2. [Slides](./slides.md): the AI Development Lifecycle, and the opportunities, risks and mitigations of agents in healthcare
3. [Lab 1: The Naive Agent](./lab-1.md): deploy the inbox agent to Orchestrate and see where it breaks
4. [Lab 2: Observability](./lab-2.md): read your agent's traces and mask patient data with a control and a plug-in
5. [Lab 3: Improving Your Agent](./lab-3.md): check the agent's concerns with three judge agents
6. [Lab 4: Securing Data Used By The Agent](./lab-4.md): find every copy of the agent's data and decide who can read it

???+ tip "Time Estimate"
    The workshop runs for 2 hours: about 30 minutes of presentation, then four labs of 15 to 25 minutes each.

---

## The Problem

Doctors are overwhelmed with patient portal messages. A single message might contain several unrelated questions. Some are urgent; most are routine. Responding to all of them comes on top of a full patient load.

Can we use an AI agent to help? And can we do it **responsibly**: keep the doctor in the loop, protect patient data, and resist letting the AI "just handle it"?

---

## Workshop Structure

### [Lab 1: The Naive Agent](./lab-1.md)
Deploy a background agent to watsonx Orchestrate. It reads a patient's record and portal messages and lists concerns in the inbox UI. It has no guardrails and no access controls, on purpose.

### [Lab 2: Observability](./lab-2.md)
Orchestrate records a trace of every run without any code from you. Open a trace, find the patient data in it, and try two masking layers: the built-in PII Filter control and a Python plug-in.

### [Lab 3: Improving Your Agent](./lab-3.md)
Learn how claim extraction, grounding checks, LLM-as-judge and a critic catch made-up evidence and off-task answers. Run three judge agents on Orchestrate against your agent's concerns and read their verdicts.

### [Lab 4: Securing Data Used By The Agent](./lab-4.md)
The agent's output is patient data too. List every copy of the agent's data, check what IBM documents about how Orchestrate stores it, and discuss why access control belongs in the data layer and why the clinician's identity has to travel with every request.

---

## Additional Resources

- [Additional Resources](./resources.md): IBM docs, papers and tools
- [Contributing](./contributing.md): how to contribute to this workshop

Head to [Prerequisites](./prerequisites.md) to set up your environment.
