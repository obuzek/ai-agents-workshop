# Contributing to the AI Agents Workshop

Thank you for your interest in contributing! This workshop is a community effort, and we welcome contributions of all kinds.

## Ways to Contribute

### 1. Report Issues

Found a bug or have a suggestion? Please open an issue on GitHub:

- **Bug Reports**: Describe what you expected vs. what happened
- **Feature Requests**: Explain the use case and benefits
- **Documentation**: Point out unclear or missing information

### 2. Improve Documentation

Help make the workshop better:

- Fix typos and grammar
- Clarify confusing sections
- Add examples and use cases
- Translate content to other languages

### 3. Add Code Examples

Contribute new examples or improve existing ones:

- Additional agent implementations
- Tool integrations
- Use case demonstrations
- Best practice examples

### 4. Share Your Experience

Help others learn from your experience:

- Write blog posts about your learnings
- Share your agent implementations
- Present at meetups or conferences
- Answer questions in discussions

## Getting Started

### 1. Fork the Repository

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ai-agents-workshop.git
cd ai-agents-workshop
```

### 2. Set Up Development Environment

```bash
# Install lab code dependencies
uv sync

# Install MkDocs as a global tool (one-time, for docs work)
uv tool install "mkdocs==1.6.1" \
  --with "mkdocs-material==9.7.6" \
  --with "mkdocs-awesome-pages-plugin==2.10.1" \
  --with "mkdocs-git-revision-date-localized-plugin==1.5.1" \
  --with "mkdocs-git-authors-plugin==0.10.0" \
  --with "mkdocs-glightbox==0.5.2" \
  --with "mkdocs-minify-plugin==0.8.0" \
  --with "mkdocs-rss-plugin==1.18.0" \
  --with "mkdocs-table-reader-plugin==3.1.0"
```

### 3. Make Your Changes

```bash
# Create a new branch
git checkout -b feature/your-feature-name

# Make your changes
# Test locally with: mkdocs serve

# Commit your changes
git add .
git commit -m "Description of your changes"
```

### 4. Submit a Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Open a pull request on GitHub
```

## Documentation Guidelines

### Writing Style

- **Clear and Concise**: Use simple language
- **Active Voice**: "You will build" not "An agent will be built"
- **Code Examples**: Include working, tested code
- **Explanations**: Explain why, not just how

### Markdown Formatting

Use consistent formatting:

```markdown
# Main Heading (H1)

## Section Heading (H2)

### Subsection (H3)

**Bold** for emphasis
*Italic* for terms
`code` for inline code

\`\`\`python
# Code blocks with language specified
def example():
    pass
\`\`\`
```

### Code Examples

All code examples should:

- Be complete and runnable
- Include necessary imports
- Have clear comments
- Follow Python best practices (PEP 8)

Example:

```python
# good_example.py
"""
A clear description of what this code does.
"""
import os
from typing import Dict

def process_data(input_data: Dict) -> Dict:
    """
    Process the input data.
    
    Args:
        input_data: Dictionary containing input
        
    Returns:
        Processed data dictionary
    """
    # Implementation here
    return {}
```

## Testing Your Changes

### Local Preview

Test your documentation changes locally:

```bash
cd docs
mkdocs serve
```

Visit `http://127.0.0.1:8003` to preview your changes.

### Build Test

Ensure the site builds without errors:

```bash
mkdocs build
```

## Pull Request Process

1. **Update Documentation**: If you change code, update relevant docs
2. **Test Thoroughly**: Ensure all examples work
3. **Write Clear Commit Messages**: Explain what and why
4. **Reference Issues**: Link to related issues if applicable
5. **Be Patient**: Maintainers will review as soon as possible

### PR Template

When opening a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code example

## Testing
How you tested your changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Examples tested
- [ ] No breaking changes
```

## Code of Conduct

### Our Standards

- **Be Respectful**: Treat everyone with respect
- **Be Constructive**: Provide helpful feedback
- **Be Inclusive**: Welcome diverse perspectives
- **Be Patient**: Remember everyone is learning

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information

## Questions?

- **GitHub Discussions**: Ask questions and share ideas
- **Issues**: Report bugs or request features
- **Email**: Contact maintainers directly for sensitive matters

## Recognition

Contributors will be:

- Listed in the project README
- Credited in release notes
- Acknowledged in documentation

Thank you for helping make this workshop better for everyone!

---

## Additional Resources

- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)
- [Markdown Guide](https://www.markdownguide.org/)
- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)