# Style guide — finishing ehlo.pl posts

Derived from the one genuinely finished post,
`content/posts/EXO-bypass-ExchangeOnlineManagement.md`, plus the best-written draft,
`content/posts/freeipa-and-postfix.md`. As more posts are truly finished, refresh this
against them — the sample is currently small.

Target: **typical technical blogpost — not too funny, not too professional.** Written in
English by a non-native speaker; keep it human, not corporate.

## Frontmatter schema (TOML, `+++`)

A finished post carries all six fields:

```toml
+++
title = 'ExoHelper: Lightweight EXO Access Without ExchangeOnlineManagement'
date = '2026-07-04T11:12:23+02:00'
draft = true
description = "Calling Exchange Online REST API directly from PowerShell without the heavy module"
tags = ["powershell", "exchange-online", "microsoft-365", "rest-api", "exo"]
categories = ["PowerShell"]
+++
```

- `description` — one sentence; used in listings and search. Always fill it.
- `tags` — lowercase, hyphenated, specific. Skeleton posts also carry a `week-NN` series
  tag; keep it.
- `categories` — the broad bucket (e.g. `"Classical Protocols"`, `"PowerShell"`).
- Leave `draft = true` — the author flips it when they publish.

## Section arc

Follow the discovery-driven arc of the exemplar. Not every post needs every heading, but
this is the spine:

1. **The Discovery / Intro** — first person: what you stumbled on, why it caught your eye.
2. **What Is X?** — plain-language explanation, where it fits.
3. **How It Works** — the mechanism, step by step. Cite RFCs / official docs.
4. **Example** — real, runnable code with real values.
5. **Why This Matters** — the practical payoff; when you'd use it and when you wouldn't.
6. **Closing Thought** — honest opinion, where you might go next.
7. **References** — authoritative links.

## Voice — what makes it sound like the author

- **First person, discovery-driven.** "I was quite surprised when I stumbled across…"
- **Real values in code**, not `<PLACEHOLDER>` where a real example is possible.
- **Personal asides are welcome** — "What was funny — it even did not ask me for
  authentication", "Probably I'd never use it in real production — too big a risk." These
  are the personality. Keep them.
- **Do not sand off the author's English.** Minor imperfections read as genuine. Fix
  broken grammar that impedes meaning; don't rewrite into flawless marketing prose.
- **No chatbot voice.** No "Got it —", no "Below is a complete example", no "Would you
  like me to…", no "As you can see". No second-person "your machine" framing — write
  about the setup, not the reader's setup.

## Markdown conventions

- Code fences are **lowercase-language-tagged**: ` ```bash `, ` ```powershell `,
  ` ```toml `, ` ```ini `. Never ` ```Bash ` or ` ```Json `. Closing fence is bare ` ``` `.
- Keep prose **outside** fences — never let "Response example:" or JSON snippets leak
  inside a ` ```bash ` block (a classic dump artifact).
- Quotes / notes use blockquotes: `> **Note:** …` and plain `>` for quoted material.
- Screenshots: `![alt text](assets/<name>.png)`, stored under
  `content/posts/assets/` (see the existing `2026-07-04T114510.png`). If you don't have
  the image, use a `> **NEEDS YOUR LAB:**` callout instead — never invent one.
- `---` horizontal rules between major sections are fine (see `freeipa-and-postfix.md`).
- References section: a list of `[label](url)` to RFCs, official docs, project pages.

## Rule zero (repeat)

Draft from authoritative sources; **flag** — never fabricate — anything that needs the
author's real lab output. See `SKILL.md`.
