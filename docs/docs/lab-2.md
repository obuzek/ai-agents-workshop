# Lab 2: Observability

**Duration:** ~20 minutes

???+ abstract "What You'll Add"
    The naive agent from Lab 1 is a black box — you can see inputs and outputs, but not what's happening in between. In this lab you'll instrument your agent with tracing, structured logging, and a simple dashboard so you can inspect every decision it makes.

---

## Learning Objectives

- Understand why observability matters for agentic systems
- Add structured logging to the agent reasoning loop
- Trace tool calls with inputs, outputs, and timing
- Use a tracing framework to visualize agent behavior

---

## Overview

Observability for agents goes beyond simple logging. You need to capture:

| Signal | What it tells you |
|---|---|
| **Traces** | The full decision path through the agent loop |
| **Spans** | Individual operations (LLM calls, tool calls) and their timing |
| **Logs** | Structured events with context for debugging |
| **Metrics** | Aggregate statistics (latency, token usage, error rates) |

---

## Step 1: Add Structured Logging

```python
# TODO: add structured logging setup
```

---

## Step 2: Instrument LLM Calls

```python
# TODO: wrap LLM calls with trace spans
```

---

## Step 3: Instrument Tool Calls

```python
# TODO: wrap tool execution with trace spans and log inputs/outputs
```

---

## Step 4: Visualize the Trace

```bash
# TODO: add instructions for viewing traces
```

---

## What Did We Learn?

With observability in place you can now:

- See exactly which tools were called and in what order
- Identify slow steps in the agent loop
- Debug failures by inspecting the full trace
- Audit agent behavior after the fact

---

???+ tip "Up Next"
    Head to [Lab 3: Improving Your Agent](./lab-3.md) to use what you've learned from observability to make the agent more reliable.
