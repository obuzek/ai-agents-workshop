# Lab 1: Introduction to AI Agents

In this lab, you'll build your first AI agent - a simple but functional agent that can respond to queries and demonstrate basic reasoning capabilities.

## Learning Objectives

By the end of this lab, you will:

- Understand the basic structure of an AI agent
- Create a simple agent using Python
- Implement basic prompt engineering
- Test and interact with your agent

## Prerequisites

- Completed [Prerequisites](./prerequisites.md) setup
- Python 3.11+ installed
- API key configured (OpenAI, watsonx.ai, or Ollama running)

## Lab Overview

We'll build a simple agent that can:

1. Accept user queries
2. Process them using an LLM
3. Generate helpful responses
4. Maintain conversation context

## Step 1: Project Setup

Create a new directory for your agent:

```bash
mkdir my-first-agent
cd my-first-agent

# Create a virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install required packages
uv pip install openai python-dotenv
```

## Step 2: Create Your First Agent

Create a file called `simple_agent.py`:

```python
# simple_agent.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SimpleAgent:
    """A basic AI agent that can respond to queries."""
    
    def __init__(self, model="gpt-4o-mini"):
        """Initialize the agent with an LLM."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.conversation_history = []
        
        # Define the agent's system prompt
        self.system_prompt = """
        You are a helpful AI assistant. Your role is to:
        - Answer questions clearly and concisely
        - Break down complex topics into understandable parts
        - Ask for clarification when needed
        - Admit when you don't know something
        
        Always be helpful, honest, and harmless.
        """
    
    def chat(self, user_message: str) -> str:
        """
        Send a message to the agent and get a response.
        
        Args:
            user_message: The user's input message
            
        Returns:
            The agent's response
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Prepare messages for the API call
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history
        
        # Call the LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        # Extract the assistant's response
        assistant_message = response.choices[0].message.content
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
    
    def reset(self):
        """Clear the conversation history."""
        self.conversation_history = []


def main():
    """Run an interactive chat session with the agent."""
    print("Simple AI Agent")
    print("=" * 50)
    print("Type 'quit' to exit, 'reset' to clear history\n")
    
    agent = SimpleAgent()
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
            
        if user_input.lower() == 'quit':
            print("Goodbye!")
            break
            
        if user_input.lower() == 'reset':
            agent.reset()
            print("Conversation history cleared.\n")
            continue
        
        # Get agent response
        try:
            response = agent.chat(user_input)
            print(f"\nAgent: {response}\n")
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()
```

## Step 3: Create Environment File

Create a `.env` file with your API key:

```bash
# .env
OPENAI_API_KEY=your-api-key-here
```

## Step 4: Run Your Agent

```bash
python simple_agent.py
```

Try these example interactions:

```
You: What is an AI agent?
Agent: [Explains AI agents...]

You: Can you give me an example?
Agent: [Provides examples with context from previous message...]

You: reset
Conversation history cleared.

You: quit
Goodbye!
```

## Understanding the Code

### The Agent Class

```python
class SimpleAgent:
    def __init__(self, model="gpt-4o-mini"):
        # Initialize with model and empty history
        self.conversation_history = []
```

The agent maintains conversation history to provide context-aware responses.

### The System Prompt

```python
self.system_prompt = """
You are a helpful AI assistant...
"""
```

The system prompt defines the agent's behavior and personality.

### The Chat Method

```python
def chat(self, user_message: str) -> str:
    # Add message to history
    # Call LLM with full context
    # Return response
```

This method handles the conversation flow and maintains context.

## Exercises

### Exercise 1: Customize the System Prompt

Modify the system prompt to create different agent personalities:

```python
# A coding assistant
self.system_prompt = """
You are an expert programming assistant specializing in Python.
Help users write clean, efficient code with clear explanations.
"""

# A creative writing helper
self.system_prompt = """
You are a creative writing assistant. Help users brainstorm ideas,
develop characters, and improve their storytelling.
"""
```

### Exercise 2: Add Conversation Limits

Prevent the conversation history from growing too large:

```python
def chat(self, user_message: str, max_history=10) -> str:
    # Keep only the last N messages
    if len(self.conversation_history) > max_history:
        self.conversation_history = self.conversation_history[-max_history:]
    # ... rest of the method
```

### Exercise 3: Add Response Streaming

Make the agent stream responses for better UX:

```python
def chat_stream(self, user_message: str):
    """Stream the agent's response token by token."""
    # Add user message
    self.conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    messages = [
        {"role": "system", "content": self.system_prompt}
    ] + self.conversation_history
    
    # Stream the response
    stream = self.client.chat.completions.create(
        model=self.model,
        messages=messages,
        stream=True
    )
    
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    
    print()  # New line after streaming
    
    # Add to history
    self.conversation_history.append({
        "role": "assistant",
        "content": full_response
    })
```

## Alternative: Using Ollama

If you prefer to run models locally:

```python
# simple_agent_ollama.py
import requests
import json

class OllamaAgent:
    def __init__(self, model="llama3.2"):
        self.model = model
        self.conversation_history = []
        self.system_prompt = "You are a helpful AI assistant."
    
    def chat(self, user_message: str) -> str:
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Call Ollama API
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt}
                ] + self.conversation_history,
                "stream": False
            }
        )
        
        result = response.json()
        assistant_message = result["message"]["content"]
        
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
```

## Key Takeaways

1. **Simple agents** need just an LLM and a system prompt
2. **Conversation history** enables context-aware responses
3. **System prompts** define agent behavior and personality
4. **Error handling** is important for production agents

## Next Steps

Now that you have a basic agent working, proceed to [Lab 2: Building Your First Agent](./lab-2.md) where you'll add tool-using capabilities!

---

## Troubleshooting

### API Key Errors

```
Error: Incorrect API key provided
```

Solution: Check your `.env` file and ensure the API key is correct.

### Rate Limiting

```
Error: Rate limit exceeded
```

Solution: Add retry logic or use a different model tier.

### Import Errors

```
ModuleNotFoundError: No module named 'openai'
```

Solution: Ensure you've activated your virtual environment and installed dependencies.