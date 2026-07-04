#!/usr/bin/env python3
"""Upgrade a post's bare frontmatter to the full finished-post schema.

Usage:
    python normalize_frontmatter.py content/posts/GraphAPIAuditEvents.md          # diff
    python normalize_frontmatter.py content/posts/GraphAPIAuditEvents.md --write   # apply

Adds any missing description/tags/categories fields as TODO scaffolding,
preserving existing date/draft/title lines verbatim. Only touches TOML (+++)
frontmatter; prints a warning and does nothing for YAML or missing frontmatter.
"""

import difflib
import re
import sys

import frontmatter as fm

# TODO scaffolding for fields a finished post needs.
SCAFFOLD = {
    'description': 'description = "TODO: one-line summary for listings and SEO"',
    'tags': 'tags = ["TODO"]',
    'categories': 'categories = ["TODO"]',
}


def title_from_frontmatter(raw):
    t = fm.get_field(raw, 'title')
    return t or ''


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    write = '--write' in argv
    if len(args) != 1:
        print(__doc__)
        return 2
    path = args[0]
    content = fm.read_text(path)

    if not content.startswith('+++'):
        print(f'{path}: not TOML (+++) frontmatter — skipping to avoid mangling.')
        return 1

    raw, _ = fm.split_frontmatter(content)
    missing = [f for f in ('description', 'tags', 'categories')
               if f not in fm.present_fields(raw)]
    if not missing:
        print(f'{path}: frontmatter already complete.')
        return 0

    # Insert scaffolding lines just before the closing +++ delimiter.
    m = re.match(r'^(\+\+\+\s*\n.*?\n)(\+\+\+\s*\n)(.*)$', content, re.DOTALL)
    head, close, body = m.group(1), m.group(2), m.group(3)
    additions = ''.join(SCAFFOLD[f] + '\n' for f in missing)
    new_content = head + additions + close + body

    diff = difflib.unified_diff(
        content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=path, tofile=path + ' (normalized)',
    )
    sys.stdout.writelines(diff)

    if write:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(new_content)
        print(f'\n{path}: added {", ".join(missing)}.')
    else:
        print(f'\n(dry run — re-run with --write to apply. Would add: '
              f'{", ".join(missing)})')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
