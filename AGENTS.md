# AI Agent Instructions for ai-agents-workshop

This document contains context and instructions for AI agents working on this repository.

## Repository Overview

An **AI Agents Workshop** for ODSC — a 2-hour hands-on session teaching developers how to build, observe, improve, and secure AI agents. Delivered as a static website built with MkDocs.

**Live Site:** https://obuzek.github.io/ai-agents-workshop/

## Project Structure

```
ai-agents-workshop/
├── pyproject.toml                 # Lab code dependencies (uv sync to install)
├── docs/                          # MkDocs documentation site
│   ├── base.yml                   # Base configuration (theme, plugins, markdown)
│   ├── mkdocs.yml                 # Workshop-specific config (inherits base.yml)
│   ├── README.md                  # MkDocs setup and usage instructions
│   ├── theme/                     # Custom theme assets (favicon, logos)
│   └── content/                   # Markdown content (docs_dir: "content")
│       ├── .pages                 # Navigation structure (awesome-pages plugin)
│       ├── index.md               # Workshop home page
│       ├── slides.md              # Slide viewer (ADLC + Risks & Mitigation)
│       ├── prerequisites.md       # Setup instructions
│       ├── getting-started.md     # Core concepts
│       ├── lab-1.md              # Naive Agent Implementation
│       ├── lab-2.md              # Observability
│       ├── lab-3.md              # Improving Your Agent
│       ├── lab-4.md              # Securing Data Used By The Agent
│       ├── resources.md          # Papers, frameworks, learning resources
│       └── contributing.md       # Contribution guidelines
├── .github/
│   └── workflows/
│       └── deploy-docs.yml       # GitHub Actions: auto-deploy on push to main
├── CLAUDE.md                     # Claude Code workflow protocol
└── AGENTS.md                     # This file
```

## Two Separate Environments

This repo deliberately keeps **two environments separate**:

### 1. MkDocs (docs tooling) — global uv tool

MkDocs is installed once as a global tool, not in a project venv:

```bash
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

Do NOT add MkDocs or its plugins to `pyproject.toml`.

### 2. Lab code — project venv via uv

Lab dependencies live in `pyproject.toml` at the repo root:

```bash
uv sync
```

## Development Workflow

### Docs

```bash
cd docs
mkdocs serve        # local preview at http://127.0.0.1:8003
mkdocs gh-deploy    # deploy to GitHub Pages
```

### Lab code

```bash
uv sync             # install/update lab dependencies
uv run python ...   # run lab scripts
```

## Architecture Decisions

### Config Inheritance

- [`base.yml`](docs/base.yml) — shared theme, plugins, markdown extensions
- [`mkdocs.yml`](docs/mkdocs.yml) — workshop-specific settings (inherits base.yml)

### Deployment

GitHub Actions (`.github/workflows/deploy-docs.yml`) auto-deploys on push to `main` when files under `docs/` change. Manual deploy: `cd docs && mkdocs gh-deploy`.

### Adding a Plugin

```bash
uv tool install mkdocs --with <plugin-name>
```

Add the `--with` flag to the install command in `docs/README.md`, `docs/content/contributing.md`, and `.github/workflows/deploy-docs.yml`.

### Adding Lab Dependencies

Add to `pyproject.toml` under `[project] dependencies`, then run `uv sync`.

## Common Tasks

### Add a New Lab

1. Create `docs/content/lab-N.md`
2. Add to navigation in `docs/content/.pages`
3. Test locally with `mkdocs serve`, then deploy

### Fix Build Errors

- **Plugin not found**: `uv tool install mkdocs --with <plugin>`
- **Missing file**: Check paths in `.pages` or `mkdocs.yml`
- **YAML syntax**: `mkdocs build --strict`

## Troubleshooting

### Site not updating after deployment

Wait 1-2 minutes for GitHub Pages to rebuild. Check the Actions tab for errors.

### Port 8003 already in use

```bash
mkdocs serve -a 127.0.0.1:8004
```
