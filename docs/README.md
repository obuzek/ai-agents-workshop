# AI Agents Workshop Documentation

This directory contains the MkDocs-based static site for the AI Agents Workshop.

## Setup (one-time)

MkDocs is managed as a global `uv` tool, separate from the lab code environment.

Install MkDocs and all required plugins:

```bash
uv tool install "mkdocs==1.6.1" \
  --with "mkdocs-material==9.7.6" \
  --with "mkdocs-revealjs" \
  --with "mkdocs-awesome-pages-plugin==2.10.1" \
  --with "mkdocs-git-revision-date-localized-plugin==1.5.1" \
  --with "mkdocs-git-authors-plugin==0.10.0" \
  --with "mkdocs-glightbox==0.5.2" \
  --with "mkdocs-minify-plugin==0.8.0" \
  --with "mkdocs-rss-plugin==1.18.0" \
  --with "mkdocs-table-reader-plugin==3.1.0"
```

This installs `mkdocs` once globally. You do not need a virtual environment for docs work.

## Development

**Serve locally** (from the `docs/` directory):

```bash
cd docs
mkdocs serve
```

Visit `http://127.0.0.1:8003` to view the site.

**Deploy to GitHub Pages:**

```bash
cd docs
mkdocs gh-deploy
```

This builds the site and pushes it to the `gh-pages` branch, making it available at `https://obuzek.github.io/ai-agents-workshop/`.

## Project Structure

```
docs/
├── base.yml              # Base MkDocs configuration (theme, plugins, extensions)
├── mkdocs.yml            # Workshop-specific configuration (inherits from base.yml)
├── theme/                # Custom theme files (favicon, logos)
└── content/              # Documentation content (docs_dir in base.yml)
    ├── .pages            # Navigation structure
    ├── index.md          # Home page
    ├── slides.md         # Presentation page (iframe wrapper)
    ├── slides/
    │   └── presentation.html  # Reveal.js slide deck (edit this for slide content)
    ├── prerequisites.md
    ├── getting-started.md
    ├── lab-1.md          # Naive Agent Implementation
    ├── lab-2.md          # Observability
    ├── lab-3.md          # Improving Your Agent
    ├── lab-4.md          # Securing Data Used By The Agent
    ├── resources.md
    └── contributing.md
```

## Editing slides

Slides live in `content/slides.md` and are rendered by the
[mkdocs-revealjs](https://pypi.org/project/mkdocs-revealjs/) plugin.
Edit the file and the dev server picks up changes automatically.

**Slide separators:** use `---` (surrounded by blank lines) between slides.
End the presentation with `=====` — anything after that renders as normal MkDocs content.

```markdown
## Slide Title

- Bullet point one
- Bullet point two

---

## Next Slide

Content here.

=====

Normal page content here (not part of the presentation).
```

**Per-slide attributes** (background color, transitions, etc.) go in an HTML comment
at the top of the slide:

```markdown
<!-- .slide: data-background="#0f62fe" -->

# Section Header
```

**Speaker notes** go after `Note:` and are hidden from the audience
(press `S` in the presentation to open the speaker view):

```markdown
## My Slide

- Point A
- Point B

Note: Remind attendees to check prerequisites before this section.
```

**AI generation:** the content is plain Markdown — ask an LLM to rewrite or expand
any section. Keep `---` separators, `<!-- .slide: -->` directives for section headers,
and the `=====` terminator.

## Troubleshooting

**Plugin not found:**

```bash
uv tool install mkdocs --with <missing-plugin-name>
```

**Build errors** — use strict mode to surface broken links or missing files:

```bash
mkdocs build --strict
```

**Port already in use:**

```bash
mkdocs serve -a 127.0.0.1:8004
```
