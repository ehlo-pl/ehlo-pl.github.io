# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Hugo static blog about open-source email infrastructure (SMTP, DKIM/DMARC/SPF, Postfix,
JMAP, mail server comparisons, PowerShell mail tooling). Config in `hugo.toml`. The theme
**PaperMod** is vendored as a git submodule at `themes/PaperMod` — don't edit theme files;
treat it as read-only. Published to `blog.ehlo.pl` via GitHub Pages.

## Commands

Hugo **extended** is required. After a fresh clone: `git submodule update --init --recursive`.

- `hugo server -D` — local preview including drafts (`-D`).
- `hugo --minify` — production build into `public/`.
- `python generate_toc.py` — regenerate the posts index at `content/lists/toc.md` (sorted
  by date, marks drafts). Run after adding or renaming posts.

Post toolkit (stdlib-only Python, resolves paths to repo root, run from anywhere):

- `python .claude/skills/expand-post/scripts/post_status.py` — dashboard of every post
  (placeholders, AI-tells, frontmatter gaps, word count). `--drafts` to filter.
- `python .claude/skills/expand-post/scripts/lint_post.py content/posts/<file>.md` — deep-lint
  one post; non-zero exit if issues remain.
- `python .claude/skills/expand-post/scripts/normalize_frontmatter.py <file> [--write]` — upgrade
  bare frontmatter to the full schema (dry-run diff by default).
- `python .claude/skills/expand-post/scripts/new_post.py "<topic>"` — scaffold a fresh draft.

## Deployment

`.github/workflows/deploy.yml`: push to `main` → download Hugo extended (pinned `HUGO_VERSION`, sha256-checked;
bump deliberately and test locally) → `actions/configure-pages` (step id `pages`) supplies the base URL →
`hugo --minify --baseURL "${{ steps.pages.outputs.base_url }}"` → `upload-pages-artifact` + `deploy-pages`.
Custom domain from `static/CNAME`. **Never drop the `Setup Pages` step**: without it the base URL is empty and
every link points to `example.org`. Only `main` deploys;
feature branches do not. Work happens on feature branches (e.g. `feature/YYYYMMDD.N`).

## Content architecture

- Posts live in `content/posts/*.md`; images in `content/posts/assets/`, referenced as
  `![alt](assets/<name>.png)`.
- Frontmatter is **TOML** (`+++` fences) with six fields: `title`, `date`, `draft`,
  `description`, `tags` (lowercase-hyphenated; skeleton posts also carry a `week-NN` series
  tag — keep it), `categories`. `generate_toc.py` also tolerates legacy YAML (`---`) posts.
- **Draft lifecycle:** `draft = true` stays until the *author* flips it to `false` — that flip
  is their publish signal. Never flip it yourself.

## Writing conventions

Source of truth for anything content-related: `.claude/skills/expand-post/SKILL.md` and its
`references/style-guide.md`. Finished exemplar: `content/posts/EXO-bypass-ExchangeOnlineManagement.md`.

- **Rule zero — never fabricate.** These are protocol/config posts; the failure mode is
  plausible-but-wrong. Draft conceptual prose, RFC references, and config syntax only from
  authoritative sources (RFCs, official docs, `context7` for library APIs). For anything
  needing the author's real lab captures, telnet transcripts, or screenshots, emit a
  `> **NEEDS YOUR LAB:** …` callout instead of inventing.
- **Voice:** first-person, discovery-driven, human non-native English. Don't sand it into
  corporate or chatbot prose (no "Got it —", no "As you can see", no second-person "your
  machine" framing).
- Code fences are lowercase-language-tagged (` ```bash `, ` ```powershell `, ` ```toml `);
  keep prose outside fences.

## Environment

Primary shell is PowerShell on Windows; the working tree lives under a OneDrive-synced path.

## AI-assistance notice

Every post shows an *AI-assisted* badge in the post meta and a closing note (topics and experience
are the author's, AI helped with writing; the author takes responsibility). Policy page: `content/ai.md`.

- Defaults live in `hugo.toml` `[params]`: `aiAssisted`, `aiTool`, `aiScope`, `aiPolicy`. Do **not** add
  these to every post; set them in front matter only for exceptions (`aiAssisted = false`, or a narrower
  `aiScope = ["editing"]`). They are outside the six-field schema on purpose.
- AI-generated illustrations get a caption saying so (`figure` shortcode, `caption="Illustration: AI-generated, …"`).

## Theme overrides

PaperMod stays read-only; these files in `layouts/` are copies of theme files with local changes.
When the submodule is updated, diff each against `themes/PaperMod/layouts/…` and re-apply the change.

| File | Local change |
|---|---|
| `_default/baseof.html` | `.Language.Direction` (newer Hugo API) |
| `_default/rss.xml` | `.Language.Locale`; AI-assisted note in item `<description>` |
| `partials/templates/opengraph.html` | `.Language.Locale` |
| `_default/single.html` | `partial "ai_note.html"` after the post content |
| `partials/post_meta.html` | *AI-assisted* badge |

New files (not copies): `partials/ai_note.html`, `partials/extend_head.html` (theme hook, `ai-assisted`
meta tag), `assets/css/extended/ai-note.css`, `lposts/single.html`.
