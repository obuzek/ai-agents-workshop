# AI Agents Workshop Documentation

This directory contains the MkDocs-based static site for the AI Agents Workshop.

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Git

### Setup

1. **Create a virtual environment:**

```bash
cd docs
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

### Development

**Serve locally:**

```bash
mkdocs serve
```

Visit `http://127.0.0.1:8003` to view the site.

**Build the site:**

```bash
mkdocs build
```

The built site will be in the `site/` directory.

### Using Make

Alternatively, use the Makefile:

```bash
# Create virtual environment
make venv

# Activate it
source ~/.venv/ai-agents-workshop-docs/bin/activate

# Serve the site
make serve

# Build the site
make build

# Deploy to GitHub Pages
make deploy
```

## Project Structure

```
docs/
├── base.yml              # Base MkDocs configuration
├── mkdocs.yml           # Main MkDocs configuration
├── requirements.txt     # Python dependencies
├── Makefile            # Build automation
├── .gitignore          # Git ignore rules
├── theme/              # Custom theme files
│   ├── favicon.ico
│   ├── logo.png
│   └── logo-small.png
└── docs/               # Documentation content
    ├── .pages          # Navigation structure
    ├── index.md        # Home page
    ├── prerequisites.md
    ├── getting-started.md
    ├── lab-1.md
    ├── lab-2.md
    ├── lab-3.md
    ├── resources.md
    ├── contributing.md
    └── images/         # Image assets
```

## Configuration

The site uses a two-tier configuration:

- **`base.yml`**: Shared configuration (theme, plugins, markdown extensions)
- **`mkdocs.yml`**: Workshop-specific settings (inherits from base.yml)

This pattern allows for:
- Consistent styling across multiple workshops
- Easy customization per workshop
- Maintainable configuration

## Features

### Plugins

- **awesome-pages**: Flexible navigation structure
- **git-revision-date-localized**: Last updated dates
- **git-authors**: Contributor tracking
- **glightbox**: Image lightbox
- **minify**: HTML optimization
- **search**: Full-text search
- **with-pdf**: PDF generation (optional)

### Markdown Extensions

- **Admonitions**: Callout boxes
- **Code highlighting**: Syntax highlighting
- **Mermaid diagrams**: Flowcharts and diagrams
- **Tabbed content**: Multiple content tabs
- **Task lists**: Checkboxes
- And many more...

## Deployment

### GitHub Pages

Deploy to GitHub Pages:

```bash
mkdocs gh-deploy
```

This will:
1. Build the site
2. Push to the `gh-pages` branch
3. Make it available at `https://ibm.github.io/ai-agents-workshop/`

### Manual Deployment

Build and deploy manually:

```bash
mkdocs build
# Copy the site/ directory to your web server
```

## Contributing

See [CONTRIBUTING.md](docs/contributing.md) for guidelines on:

- Reporting issues
- Improving documentation
- Adding code examples
- Submitting pull requests

## Troubleshooting

### Plugin Not Found

If you see "plugin is not installed" errors:

```bash
pip install -r requirements.txt
```

### Build Errors

Check for:
- Missing files referenced in navigation
- Invalid YAML syntax
- Broken internal links

Use strict mode to catch issues:

```bash
mkdocs build --strict
```

### Port Already in Use

If port 8003 is busy:

```bash
mkdocs serve -a 127.0.0.1:8004
```

## License

Copyright © 2025 IBM Research

Licensed under the Apache License, Version 2.0.