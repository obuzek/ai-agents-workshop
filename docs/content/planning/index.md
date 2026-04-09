# Use Case Planning

## Best candidates

For each, list:

* Scenario
* Responsible AI concerns
* Why this framing of the problem?
* Personas
* Data sources (including concerns for each data source)
* Responsible AI tools used
    * Langfuse for observability
    * Guardian models - PII, HAP, hallucination detector, bias, jailbreaking, prompt injection, value alignment, context relevance / answer relevance
    * Data governance tools? Guardium? (and OSS equivalents?)
    * Arize Phoenix - OSS LLM tracing and evaluation
    * Reasoning models
* How each tool supports the use case
* Proposed architectural layout

## Principles

* Where possible, augment instead of replacing human labor - augmenting human capabilities (handled in design)
* Hybrid local / remote (open) AI processing options - can you build on-device processing for more sensitive data before it gets sent over a network? (Granite + Ollama)
* Data governance tools?
* How do you approach a high-risk use case?

## Practices

* API key storage, privileges, RBAC
    * If change made, you'll be notified

### Use Cases

* **Healthcare:**
    * Scenario: Enhanced training for medical staff
        * "You are responsible for building a learning platform for healthcare workers - to help them level up on their abilities to talk to patients." - https://github.com/jjasghar/pete
    * **OLIVIA** Scenario: Agent to help them sort out for a patient, if they've totally forgotten about it, haven't heard back in 4-5 months - stale / stalled messages. Some portal management.
    * Scenario: "Need medical advice, but people may not be comfortable talking about it even with doctors. Can the assistant help you take some initial steps? Bad breath, normal sort of thing - hard to talk about it and get medical help and advice. Understand, but start just with tips - guardian models, reasoning models to explain the recommendations. How do you encode knowing its limitations?"
        * Guardian models - for use cases where someone is seeking advice, how do we build governance around it? Not to go overboard, not to derail, not to end up with consequences. Adversarial robustness, etc.
* **Customer Service:**
* **Human Resources:**
    * Scenario: Navigate internal policies and procedures for the business
        * "You are responsible for building a chatbot to help employees navigate your company's human resource system, freeing up in-person HR people to focus on higher level concerns. help them take action."
* **Security / Cybersecurity:**
* **Sales / Marketing:**
    * Scenario: Content creation - can you build an agent that can help; you with the initial ideation of how to market this? Initial layout of the content you can build on top of it
* **Personal / Life Assistant:**
    * Scenario: "Helps you with work / life balance, long-term goals."
* **Consumer Analysis Assistant:**
    * **SAISHRUTHI** Scenario: "Find the best / most recommended, do an analysis of the ingredients" 


## Citations

### Healthcare use cases - Thomas Wilson - UX for AI, p. 14-16
1. Generative AI in Drug Discovery — AI tools like ChatGPT and DALL-E accelerate drug discovery by generating novel compounds for testing. In healthcare call centers, **AI can automatically draft personalized responses to patient inquiries,** speeding up response times and improving patient satisfaction.
1. AI in Personalized Medicine — Predictive models in healthcare platforms allow for highly personalized treatment plans based on individual genetic information. AI also assists healthcare call centers in triaging patient concerns and routing critical cases to specialized teams more effectively.
1. AutoML for Health Platforms — AutoML platforms help hospitals and healthcare systems deploy machine learning models without needing large data science teams. This technology improves operations by predicting patient admissions and resource needs. In call centers, AutoML automates customer service processes such as appointment scheduling and follow-up care instructions.
1. Explainable AI for Medical Diagnostics — XAI ensures transparency in decision-making, particularly in diagnostics. AI can explain why certain symptoms point to specific diseases, improving trust between doctors and patients. In healthcare platforms, this helps call center representatives give patients more understandable information about their health.
1. NLP in Telemedicine and Call Centers — NLP enables healthcare platforms to automatically transcribe and analyze patient-doctor conversations, making it easier to track patient concerns. NLP enhances sentiment analysis in call centers, allowing agents to understand patient emotions in real time and adjust their responses accordingly. Google Translate APIs ensure patients receive assistance in their native tongue.
1. Edge AI in Medical Devices — Edge AI powers medical devices that can operate autonomously, such as portable ultrasound machines or health monitoring wearables. For call centers, edge AI can provide real-time diagnostic support, reducing the need for manual consultations.
1. AI in Healthcare Cybersecurity — AI-driven security systems protect patient data from breaches. In health platforms and call centers, AI monitors for suspicious activity and prevents unauthorized access to sensitive patient information.
1. MLOps for Health Systems — MLOps streamlines the deployment of machine learning models in hospitals and clinics, enabling efficient resource management and predictive equipment maintenance. Healthcare call centers benefit by using MLOps to integrate AI models that predict patient satisfaction or wait times.
1. Low-Code/No-Code AI for HealthTech — HealthTech startups and hospitals can leverage low-code AI platforms to quickly develop applications for patient management, fraud detection, and health outcome prediction without needing advanced technical expertise. In call centers, these platforms allow for... (continued on next page)
1. Collaborative AI in healthcare enhances the training of medical staff, offering personalized learning modules based on their performance. This is mirrored in healthcare call centers, where AI tools provide real-time support for agents, improving their ability to answer complex medical queries quickly and accurately. 