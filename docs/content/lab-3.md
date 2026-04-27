# Lab 3: Improving Your Agent

**Duration:** ~20 minutes

???+ abstract "What You'll Improve"
    You have a working agent and you can see what it's doing. Now let's make it better. In this lab you'll use the observability data from Lab 2 to identify failure modes, then apply targeted improvements: better prompting, error recovery, and guardrails.

---

## Learning Objectives

- Use trace data to identify where the agent fails or loops
- Improve agent reliability with better system prompts and constraints
- Implement graceful error handling and retry logic
- Add a human-in-the-loop approval step for high-stakes actions

---

## Overview

Common failure modes in the naive agent (visible once you have observability):

| Problem | Symptom | Fix |
|---|---|---|
| Infinite loops | Agent keeps calling the same tool | Max iterations + exit conditions |
| Bad tool inputs | Tool errors cascade | Input validation + retry with feedback |
| Hallucinated tools | Agent calls a tool that doesn't exist | Strict tool list enforcement |
| Runaway actions | Agent takes unintended side effects | Human-in-the-loop for destructive actions |

---

## Step 1: Fix Infinite Loops

```python
# TODO: add iteration limits and loop detection
```

---

## Step 2: Add Error Recovery

```python
# TODO: implement retry logic with error feedback to the model
```

---

## Step 3: Strengthen the System Prompt

```python
# TODO: add constraints and clearer behavioral guidelines
```

---

## Step 4: Add a Human Approval Gate

```python
# TODO: add human-in-the-loop for high-stakes tool calls
```

---

## Step 5: Verify Improvements with Observability

Run the same test cases from Lab 1 and compare the traces side by side.

```bash
# TODO: add comparison instructions
```

---

## What Did We Learn?

A few targeted improvements dramatically change agent reliability:

- Clear exit conditions prevent runaway loops
- Error feedback to the model enables self-correction
- Constrained prompts reduce hallucination and scope creep
- Human gates are the last line of defense for irreversible actions

---

## Up Next

| Lab | Problem | Solution |
|---|---|---|
| ~~[Lab 1](lab-1.md)~~ | ~~No structure, no tools, just vibes~~ | ~~A ReAct agent with structured output~~ |
| ~~[Lab 2](lab-2.md)~~ | ~~No visibility into agent behavior~~ | ~~Observability: Langfuse tracing, PII masking, cost tracking~~ |
| ~~[Lab 3](lab-3.md)~~ | ~~Unstable output, hallucinations, overstepping~~ | ~~Evaluation: output validation, grounding checks, guardrails~~ |
| **[Lab 4](lab-4.md)** | Unrestricted data access | Security: scoped tools, access controls, audit trails |
