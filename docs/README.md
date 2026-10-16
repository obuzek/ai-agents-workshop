# AI Agents Workshop Documentation

This directory contains the MkDocs-based static site for the AI Agents Workshop.

The site is published in two editions, each a fully independent MkDocs project:

| Edition | Source | URL |
|---|---|---|
| Open source | `docs/oss/` | https://obuzek.github.io/ai-agents-workshop/oss/ |
| IBM (watsonx / TechZone) | `docs/ibm/` | https://obuzek.github.io/ai-agents-workshop/ibm/ |

The bare URL (https://obuzek.github.io/ai-agents-workshop/) redirects to the open-source
edition, and so does any link from before the split (e.g. `/ai-agents-workshop/lab-1/` →
`/ai-agents-workshop/oss/lab-1/`). That redirect logic lives in `root/`.

## Setup (one-time)

MkDocs is managed as a global `uv` tool, separate from the lab code environment.

Install MkDocs and all required plugins:

```bash
uv tool install "mkdocs==1.6.1" \
  --with "mkdocs-material==9.7.6" \
  --with "pymdown-extensions==10.21.2" \
  --with "mkdocs-revealjs==0.8.5" \
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

**Serve one edition locally:**

```bash
cd docs/oss && mkdocs serve          # http://127.0.0.1:8003
cd docs/ibm && mkdocs serve          # http://127.0.0.1:8004
```

**Build everything** (both editions plus the root redirects) into `docs/site/`:

```bash
docs/build.sh            # extra args are passed to mkdocs build
```

**Deploy:** GitHub Actions (`.github/workflows/deploy-docs.yml`) runs `build.sh` and pushes
`docs/site/` to the `gh-pages` branch on every push to `main` that touches `docs/`.
`mkdocs gh-deploy` no longer works here — it only publishes a single edition and would
wipe the other one.

## Project Structure

```
docs/
├── build.sh              # Builds all editions + root redirects into site/
├── root/                 # Site-root index.html / 404.html (redirect to /oss/)
├── ibm/                  # IBM edition — same layout as oss/
└── oss/
    ├── base.yml          # Base MkDocs configuration (theme, plugins, extensions)
    ├── mkdocs.yml        # Edition-specific configuration (inherits from base.yml)
    ├── theme/            # Custom theme files (favicon, logos)
    └── content/          # Documentation content (docs_dir in base.yml)
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

Slides live in `<edition>/content/slides.md` and are rendered by the
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
