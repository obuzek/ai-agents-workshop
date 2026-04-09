# Prerequisites

Before starting the AI Agents Workshop, you'll need to set up your development environment. This page will guide you through the required installations and configurations.

## Required Software

### Python 3.11+

The workshop requires Python 3.11 or higher.

=== "macOS"
    ```bash
    # Using Homebrew
    brew install python@3.11
    
    # Verify installation
    python3 --version
    ```

=== "Linux"
    ```bash
    # Ubuntu/Debian
    sudo apt update
    sudo apt install python3.11 python3.11-venv python3-pip
    
    # Verify installation
    python3 --version
    ```

=== "Windows"
    Download and install Python from [python.org](https://www.python.org/downloads/)
    
    Make sure to check "Add Python to PATH" during installation.

### Git

Git is required for cloning the workshop repository.

=== "macOS"
    ```bash
    # Using Homebrew
    brew install git
    ```

=== "Linux"
    ```bash
    # Ubuntu/Debian
    sudo apt install git
    ```

=== "Windows"
    Download and install from [git-scm.com](https://git-scm.com/download/win)

### UV (Python Package Manager)

We recommend using `uv` for fast, reliable Python package management.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

## Optional Tools

### Visual Studio Code

A great IDE for Python development with excellent AI agent development extensions.

- Download from [code.visualstudio.com](https://code.visualstudio.com/)
- Recommended extensions:
    - Python
    - Pylance
    - Jupyter

### Docker (Optional)

For containerized deployments and testing.

- Download from [docker.com](https://www.docker.com/products/docker-desktop)

## API Keys

You'll need API keys for the LLM providers used in the workshop.

### OpenAI API Key (Recommended)

1. Sign up at [platform.openai.com](https://platform.openai.com/)
2. Navigate to API Keys section
3. Create a new API key
4. Set the environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Alternative: IBM watsonx.ai

If you prefer to use IBM's watsonx.ai:

1. Sign up at [watsonx.ai](https://www.ibm.com/watsonx)
2. Get your API key and project ID
3. Set environment variables:

```bash
export WATSONX_API_KEY="your-api-key-here"
export WATSONX_PROJECT_ID="your-project-id"
```

### Alternative: Local Models with Ollama

For running models locally without API keys:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.2

# Verify it's running
ollama list
```

## Clone the Workshop Repository

```bash
# Clone the repository
git clone https://github.com/obuzek/ai-agents-workshop.git

# Navigate to the workshop directory
cd ai-agents-workshop

# Create a virtual environment and install lab dependencies
uv sync
```

## Verify Your Setup

Run this quick verification script to ensure everything is set up correctly:

```python
# verify_setup.py
import sys
import os

def check_python_version():
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python version {version.major}.{version.minor} is too old")
        return False

def check_api_keys():
    keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "WATSONX_API_KEY": os.getenv("WATSONX_API_KEY"),
    }
    
    has_key = False
    for key, value in keys.items():
        if value:
            print(f"✓ {key} is set")
            has_key = True
        else:
            print(f"○ {key} not set (optional)")
    
    return has_key

def main():
    print("Checking prerequisites...\n")
    
    python_ok = check_python_version()
    api_ok = check_api_keys()
    
    print("\n" + "="*50)
    if python_ok and api_ok:
        print("✓ All prerequisites met! You're ready to start.")
    elif python_ok:
        print("⚠ Python is ready, but no API keys found.")
        print("  You can use Ollama for local models.")
    else:
        print("✗ Please install Python 3.11 or higher.")

if __name__ == "__main__":
    main()
```

Run the verification:

```bash
python verify_setup.py
```

## Troubleshooting

### Python Version Issues

If you have multiple Python versions installed:

```bash
# Use python3.11 explicitly
python3.11 -m venv .venv
```

### API Key Not Found

Make sure to export the environment variable in your current shell session, or add it to your shell profile:

```bash
# Add to ~/.bashrc, ~/.zshrc, or equivalent
echo 'export OPENAI_API_KEY="your-key"' >> ~/.bashrc
source ~/.bashrc
```

### Package Installation Errors

If you encounter issues with `uv sync`, ensure you have uv installed and are in the repo root:

```bash
uv --version
uv sync
```

## Next Steps

Once your environment is set up, proceed to [Getting Started](./getting-started.md) to learn about AI agents and begin the workshop!

---

## Additional Resources

- [Python Documentation](https://docs.python.org/3/)
- [UV Documentation](https://github.com/astral-sh/uv)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Ollama Documentation](https://ollama.com/docs)