# Additional Resources

Links for going further with what you did in the labs.

## IBM watsonx Orchestrate

These are the IBM pages the labs cite.

- **[Agent Development Kit (ADK) docs](https://developer.watson-orchestrate.ibm.com/)**: agents, tools, connections and the `orchestrate` CLI
- **[Traces](https://developer.watson-orchestrate.ibm.com/traces/overview)** and the **[Observability SDK](https://developer.watson-orchestrate.ibm.com/traces/observability-sdk.md)**: what Orchestrate records for each run (Lab 2)
- **[Monitoring agents](https://www.ibm.com/docs/en/SSAVQO/administering/agent_observability.html)**: Agent analytics and traces in the Orchestrate UI (Lab 2)
- **[Managing controls](https://developer.watson-orchestrate.ibm.com/controls/managing_controls.md)**: the PII Filter, Content Guardrails and other built-in policies (Lab 2)
- **[Plug-ins](https://developer.watson-orchestrate.ibm.com/plugins/plugins.md)**: your own Python at agent hooks (Lab 2)
- **[Model policies](https://developer.watson-orchestrate.ibm.com/llm/model_policies.md)**: fallback, load balancing and retry in the model gateway
- **[Evaluations](https://developer.watson-orchestrate.ibm.com/evaluate/overview.md)**, **[quick-eval](https://developer.watson-orchestrate.ibm.com/evaluate/quick_eval.md)**, **[rubric evaluations](https://developer.watson-orchestrate.ibm.com/evaluate/rubric.md)** and **[red-teaming](https://developer.watson-orchestrate.ibm.com/evaluate/llm_vulnerability.md)**: testing an agent from the CLI (not used in the labs)
- **[Security, privacy, and data protection](https://www.ibm.com/docs/en/SSAVQO/security/data_privacy_protection.html)**, **[Data isolation](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/base?topic=instance-data-isolation-watsonx-orchestrate)** and **[Managing data retention](https://www.ibm.com/docs/en/SSAVQO/administering/data_retention_agentic_experience.html)**: how Orchestrate stores data (Lab 4)

## IBM watsonx.governance and Granite Guardian

- **[watsonx.governance](https://www.ibm.com/products/watsonx-governance)**: AI use cases, factsheets, evaluation and monitoring
- **[ibm-watsonx-gov](https://ibm.github.io/ibm-watsonx-gov/)**: the Python SDK with metrics such as faithfulness, answer relevance and tool-call accuracy
- **[Granite Guardian](https://www.ibm.com/granite/docs/models/guardian/)**: IBM's models for detecting risks in prompts and answers, including groundedness (Lab 3)

## The Open-Source Edition

- **[AI Agents Workshop, open-source edition](https://obuzek.github.io/ai-agents-workshop/oss/)**: the same agent built with LangGraph, Langfuse, Granite Guardian and Postgres row-level security, all on your laptop. The `lab2/` to `lab4/` folders in this repository come from it.

## Papers

- **[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)** (Yao et al., 2022): the observe, reason, act loop that Orchestrate's `react_core` style runs (Lab 1)
- **[Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)** (Schick et al., 2023): how models learn to call tools
- **[Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)** (Shinn et al., 2023): agents that revise their work from feedback, as in a critic loop (Lab 3)
- **[Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)** (Zheng et al., 2023): where LLM judges agree with people and where they're biased, including toward their own answers (Lab 3)
- **[Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903)** (Wei et al., 2022): step-by-step prompting

## Healthcare Data Rules

- **[HIPAA Privacy Rule: minimum necessary](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/minimum-necessary-requirement/index.html)**: why the agent should only see what its task needs (Labs 1 and 4)
- **[HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)**: audit controls, access control and encryption (Lab 4)
- **[SMART on FHIR](https://docs.smarthealthit.org/)**: signing in to an EHR as a specific user, so an app or agent acts with that user's access (Lab 4)

## Other Agent Frameworks

- **[LangGraph](https://langchain-ai.github.io/langgraph/)**: the framework the open-source edition uses
- **[CrewAI](https://www.crewai.com/)**: role-based multi-agent framework
- **[AutoGen](https://microsoft.github.io/autogen/)**: Microsoft's multi-agent framework

## Blogs

- **[Simon Willison](https://simonwillison.net/)**: LLM experiments, including prompt injection
- **[Eugene Yan](https://eugeneyan.com/)**: applied ML and LLM evaluation
- **[Lilian Weng](https://lilianweng.github.io/)**: long-form overviews, including LLM agents

---

## Workshop Pages

- [Prerequisites](./prerequisites.md): setup
- [Lab 1](./lab-1.md): the naive agent
- [Lab 2](./lab-2.md): observability
- [Lab 3](./lab-3.md): checking the agent's work
- [Lab 4](./lab-4.md): securing the agent's data
