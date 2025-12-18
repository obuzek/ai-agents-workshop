# AI Agent Instructions for ai-agents-workshop

This document contains context and instructions for AI agents working on this repository.

## Repository Overview

This is an **AI Agents Workshop** - a hands-on educational workshop teaching developers how to build AI agents. The workshop is delivered as a static website built with MkDocs and Material theme.

**Live Site:** https://pages.github.ibm.com/ombuzek/ai-agents-workshop/

## Project Structure

```
ai-agents-workshop/
├── docs/                          # MkDocs documentation site
│   ├── base.yml                   # Base configuration (theme, plugins, markdown)
│   ├── mkdocs.yml                 # Workshop-specific config (inherits base.yml)
│   ├── requirements.txt           # Python dependencies for MkDocs
│   ├── Makefile                   # Build automation
│   ├── README.md                  # Setup and usage instructions
│   ├── .gitignore                 # Excludes .venv/, site/, .cache/
│   ├── theme/                     # Custom theme assets
│   │   ├── favicon.ico
│   │   ├── logo.png
│   │   └── logo-small.png
│   └── docs/                      # Markdown content
│       ├── .pages                 # Navigation structure (awesome-pages plugin)
│       ├── index.md               # Workshop home page
│       ├── prerequisites.md       # Setup instructions
│       ├── getting-started.md     # Core concepts
│       ├── lab-1.md              # Build first simple agent
│       ├── lab-2.md              # Add tool-using capabilities
│       ├── lab-3.md              # Advanced patterns (placeholder)
│       ├── resources.md          # Papers, frameworks, learning resources
│       ├── contributing.md       # Contribution guidelines
│       └── images/               # Image assets
├── .github/
│   └── workflows/
│       └── deploy-docs.yml       # GitHub Actions (disabled - enterprise restriction)
└── AGENTS.md                     # This file
```

## Architecture Decisions

### Configuration Pattern

Uses **config inheritance** (from mcp-workshop template):
- [`base.yml`](docs/base.yml) - Shared configuration for theme, plugins, markdown extensions
- [`mkdocs.yml`](docs/mkdocs.yml) - Workshop-specific settings that inherit from base.yml
- This pattern allows consistency across multiple workshops while enabling customization

### Why This Pattern?

- **Maintainability**: Update theme/plugins once in base.yml
- **Consistency**: All workshops share the same look and feel
- **Flexibility**: Each workshop can override specific settings
- **Scalability**: Easy to create new workshops by copying and customizing mkdocs.yml

### PDF Generation Disabled

The `with-pdf` and `pdf-export` plugins are **commented out** because they require system libraries (pango, cairo) that may not be installed. This prevents build failures on systems without these dependencies.

To enable PDF generation:
1. Install system libraries: `brew install pango cairo` (macOS)
2. Uncomment PDF plugin sections in base.yml and mkdocs.yml

## Development Workflow

### Local Development

```bash
cd docs
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
# Visit http://127.0.0.1:8003
```

### Making Changes

1. **Edit markdown files** in `docs/docs/`
2. **Test locally** with `mkdocs serve`
3. **Commit changes** to main branch
4. **Deploy** with `mkdocs gh-deploy --remote-name mine`

### Deployment

**Manual deployment** (GitHub Actions disabled due to enterprise restrictions):

```bash
cd docs
source .venv/bin/activate
mkdocs gh-deploy --remote-name mine
```

This pushes to the `gh-pages` branch on the `mine` remote (user's fork).

## Key Files to Know

### Navigation Structure

[`docs/docs/.pages`](docs/docs/.pages) - Defines navigation using awesome-pages plugin
- Uses emoji icons for visual hierarchy
- Organized into logical sections (Home, Getting Started, Labs, Resources)
- Easy to reorder or add new pages

### Configuration Files

- [`base.yml`](docs/base.yml) - Theme, plugins, markdown extensions
  - Line 8: `remote_name: "origin"` - Default git remote for deployment
  - Line 150-156: PDF plugins (commented out)
  
- [`mkdocs.yml`](docs/mkdocs.yml) - Workshop metadata
  - Line 6: `site_url` - Update if deploying to different URL
  - Line 11-12: Repository links
  - Line 64-82: PDF plugin config (commented out)

### Content Guidelines

When editing or adding content:

1. **Use admonitions** for callouts:
   ```markdown
   ???+ tip "Pro Tip"
       Content here
   ```

2. **Code blocks** with language specified:
   ```markdown
   ```python
   def example():
       pass
   ```
   ```

3. **Mermaid diagrams** for flowcharts:
   ```markdown
   ```mermaid
   flowchart LR
       A --> B
   ```
   ```

4. **Tabbed content** for multi-platform instructions:
   ```markdown
   === "macOS"
       Instructions for macOS
   
   === "Linux"
       Instructions for Linux
   ```

## Common Tasks

### Add a New Lab

1. Create `docs/docs/lab-N.md`
2. Add to navigation in `docs/docs/.pages`:
   ```yaml
   - "🧪 Lab N: Title": lab-N.md
   ```
3. Test locally, commit, deploy

### Update Theme Assets

Replace files in `docs/theme/`:
- `favicon.ico` - Browser tab icon
- `logo.png` - Main logo (used in header)
- `logo-small.png` - Small logo variant

### Add a Plugin

1. Add to `docs/requirements.txt`
2. Configure in `docs/base.yml` under `plugins:`
3. Test build: `mkdocs build --strict`

### Fix Build Errors

Common issues:
- **Plugin not found**: Install with `pip install -r requirements.txt`
- **Missing file**: Check paths in `.pages` or `mkdocs.yml`
- **YAML syntax**: Validate with `yamllint` or online validator
- **PDF errors**: Ensure PDF plugins are commented out

## Important Notes

### Enterprise Environment

- **GitHub Actions disabled** - Must use manual deployment
- **IBM GitHub Enterprise** - Site hosted at `pages.github.ibm.com`
- **Remote name**: User deploys to `mine` remote (their fork)

### Template Source

Based on **mcp-workshop** (most recent workshop template as of Nov 2025):
- Advanced config inheritance pattern
- Extensive plugin ecosystem
- Custom theme directory
- Production-ready setup

### Dependencies

All Python dependencies in [`docs/requirements.txt`](docs/requirements.txt):
- Core: mkdocs, mkdocs-material
- Plugins: awesome-pages, git-revision-date, git-authors, glightbox, minify, rss
- Markdown: pymdown-extensions, markdown-blockdiag
- PDF (optional): mkdocs-with-pdf, weasyprint (requires system libraries)

## Troubleshooting

### "Cannot load library 'libpango-1.0-0'"

PDF plugins require system libraries. Solution: Comment out PDF plugins in base.yml and mkdocs.yml (already done).

### "Plugin not installed"

Run: `pip install -r docs/requirements.txt`

### Site not updating after deployment

- Wait 1-2 minutes for GitHub Pages to rebuild
- Check Settings → Pages for deployment status
- Try force refresh (Cmd+Shift+R / Ctrl+Shift+R)

### Port 8003 already in use

Use different port: `mkdocs serve -a 127.0.0.1:8004`

## Best Practices

1. **Always test locally** before deploying
2. **Use strict mode** to catch errors: `mkdocs build --strict`
3. **Keep base.yml generic** - workshop-specific settings go in mkdocs.yml
4. **Document changes** in commit messages
5. **Update this file** when making architectural changes

## Future Enhancements

Potential improvements:
- Complete Lab 3 content (currently placeholder)
- Add more code examples and exercises
- Create video tutorials
- Add interactive demos
- Implement search analytics
- Add more diagrams and visualizations

## Contact

For questions about this workshop structure, refer to:
- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [mcp-workshop](../mcp-workshop/) - Template source