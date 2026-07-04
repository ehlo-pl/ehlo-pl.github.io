#!/usr/bin/env python3
"""Scaffold a new draft post using the finished-post structure.

Usage:
    python new_post.py "DKIM key rotation"
    python new_post.py "DKIM key rotation" --slug dkim-rotation

Creates content/posts/<slug>.md with full frontmatter and the gold-standard
section arc (Discovery -> What is it -> How it works -> Example -> Why it
matters -> Closing). Refuses to overwrite an existing file.
"""

import datetime
import os
import sys

import frontmatter as fm

TEMPLATE = '''+++
title = '{title}'
date = {date}
draft = true
description = "TODO: one-line summary for listings and SEO"
tags = ["TODO"]
categories = ["TODO"]
+++

## The Discovery

TODO: what made this worth writing — the moment you stumbled on it, first person.

## What Is {title}?

TODO: plain-language explanation of the thing and where it fits.

## How It Works

TODO: the mechanism, step by step. Cite RFCs / official docs; do not invent.

## Example

```bash
# TODO: real, runnable commands with real values
```

> **NEEDS YOUR LAB:** capture / screenshot from your lab goes here.

## Why This Matters

TODO: the practical payoff — when you'd reach for this and when you wouldn't.

## Closing Thought

TODO: your honest take and where you might go next.

# References

- TODO: authoritative links (RFCs, official docs, project pages)
'''


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        return 2
    topic = args[0]

    slug = topic
    if '--slug' in argv:
        slug = argv[argv.index('--slug') + 1]
    slug = fm.slugify(slug)

    path = os.path.join(fm.POSTS_DIR, slug + '.md')
    if os.path.exists(path):
        print(f'refusing to overwrite existing file: {path}')
        return 1

    # Hugo-style local datetime with offset, matching recent posts.
    now = datetime.datetime.now().astimezone().replace(microsecond=0)
    content = TEMPLATE.format(title=topic.replace("'", ''), date=now.isoformat())

    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    print(f'created {path}')
    print('Next: fill the TODOs, then run lint_post.py before flipping draft = false.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
