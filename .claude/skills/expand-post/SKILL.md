---
name: expand-post
description: >-
  Expand and finish draft blog posts in content/posts of this Hugo email-infrastructure
  blog. Fills skeleton posts (bracketed placeholders + "Preparation notes") and cleans
  up LLM-dump drafts (chatbot preambles, broken code fences, second-person voice, bare
  frontmatter) into finished technical posts in the author's voice. Use whenever the user
  wants to finish, expand, draft, or polish a post.
---

# expand-post

Help finish draft posts on this Hugo blog (`content/posts/`). Target style: typical
technical blogpost — **not too funny, not too professional.** The finished exemplar is
`content/posts/EXO-bypass-ExchangeOnlineManagement.md`; the full conventions live in
[`references/style-guide.md`](references/style-guide.md) — read it before writing.

## Rule zero: never fabricate

These are protocol and config posts (SMTP, DKIM, DMARC, Postfix, JMAP). The failure mode
is plausible-but-wrong. For **every** section, split the content into two kinds:

- **(a) You can draft it** — conceptual prose, protocol explanation, config syntax, code
  examples — *from authoritative sources*: RFCs, official docs, `context7` for library
  APIs. Cite them. If you cannot verify a specific RFC number, flag / config directive,
  or command output, do **not** invent it.
- **(b) Only the author has it** — real lab captures, telnet transcripts, screenshots,
  validation output. Skeleton placeholders literally ask for these
  (`[Real examples from mailpit/lab captures]`, `[Telnet to lab server, screenshot
  exchanges]`, `[Validation screenshots from lab setup]`). **Never fake them.** Emit a
  callout instead:

  ```
  > **NEEDS YOUR LAB:** telnet capture against the lab server showing the EHLO/MAIL/RCPT
  > exchange for this section.
  ```

This split is the whole quality story. When unsure which bucket something is in, treat it
as (b) and flag it.

## Two kinds of draft

Run `python scripts/lint_post.py <file>` first — it tells you which one you have.

1. **Skeleton post** — clean TOML frontmatter (`tags`/`categories`/`description`, a
   `week-NN` series tag), real `##` headers, bodies of `[bracketed placeholders]`, and a
   trailing `**Preparation notes:**` block. To finish: write real content into each
   section (bucket a vs b), keep the existing headers and frontmatter, and **delete the
   `Preparation notes` block**.
2. **LLM-dump post** — bare frontmatter (`date`/`draft`/`title` only), pasted from a
   chatbot. To finish: strip AI tells (preambles like "Got it —", trailing questions like
   "Would you like me to…"), fix broken code fences, rewrite second-person ("your machine"
   → article voice), expand thin sections, and normalize frontmatter.

## Workflow

1. `python scripts/lint_post.py content/posts/<file>.md` — see issues + draft type.
2. Read [`references/style-guide.md`](references/style-guide.md).
3. Rewrite following the style guide and rule zero. Preserve the author's genuine,
   slightly-imperfect English — do not over-polish into corporate tone.
4. If frontmatter is bare: `python scripts/normalize_frontmatter.py <file> --write`, then
   fill the `TODO` values with real `description`/`tags`/`categories`.
5. `python scripts/lint_post.py <file>` again — should come back clean (any remaining
   `> **NEEDS YOUR LAB:**` callouts are intentional and expected).
6. **Leave `draft = true`.** The author reviews and flips it to `false` — that is their
   "done" signal, not yours.

## Toolkit (`scripts/`)

| Script | Use |
| --- | --- |
| `post_status.py` | Dashboard of every post — placeholders, AI-tells, frontmatter gaps, word count. Run with no args to pick what to finish next; `--drafts` to filter. |
| `lint_post.py <file>` | Deep-lint one post before/after editing. Non-zero exit if issues remain. |
| `normalize_frontmatter.py <file> [--write]` | Upgrade bare frontmatter to the full schema. Dry-run diff by default. |
| `new_post.py "<topic>"` | Scaffold a fresh draft with full frontmatter + the gold-standard section arc. |

Scripts are stdlib-only Python and share `frontmatter.py` (which mirrors the repo-root
`generate_toc.py` parser). Run them from anywhere; paths resolve to the repo root.
