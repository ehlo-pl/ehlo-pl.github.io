#!/usr/bin/env python3
"""Dashboard of every post's finish-state — 'what to work on next'.

Usage:
    python post_status.py            # all posts, unfinished first
    python post_status.py --drafts   # only draft = true
    python post_status.py --csv      # machine-readable

For each post: draft flag, skeleton-placeholder count, AI-tell count,
missing frontmatter fields, and word count.
"""

import os
import sys

import frontmatter as fm


def analyze(path):
    content = fm.read_text(path)
    raw, body = fm.split_frontmatter(content)
    return {
        'name': os.path.basename(path),
        'draft': fm.is_draft(raw),
        'placeholders': fm.count_placeholders(body),
        'ai_tells': len(fm.find_ai_tells(content)),
        'missing': fm.missing_fields(raw),
        'words': fm.word_count(body),
    }


def main(argv):
    drafts_only = '--drafts' in argv
    as_csv = '--csv' in argv

    rows = [analyze(p) for p in fm.all_posts()]
    if drafts_only:
        rows = [r for r in rows if r['draft']]

    # Most-unfinished first: placeholders, then AI tells, then missing fields.
    rows.sort(key=lambda r: (r['placeholders'] + r['ai_tells'] + len(r['missing'])),
              reverse=True)

    if as_csv:
        print('name,draft,placeholders,ai_tells,missing_fields,words')
        for r in rows:
            print(f"{r['name']},{r['draft']},{r['placeholders']},{r['ai_tells']},"
                  f"{'|'.join(r['missing'])},{r['words']}")
        return 0

    print(f"{'post':<52} {'draft':<6} {'[ph]':>4} {'AI':>3} {'words':>6}  missing")
    print('-' * 100)
    for r in rows:
        miss = ','.join(r['missing']) if r['missing'] else '-'
        print(f"{r['name'][:51]:<52} {str(r['draft']):<6} {r['placeholders']:>4} "
              f"{r['ai_tells']:>3} {r['words']:>6}  {miss}")

    total = len(rows)
    unfinished = sum(1 for r in rows
                     if r['placeholders'] or r['ai_tells'] or r['missing'])
    print('-' * 100)
    print(f'{total} posts, {unfinished} with placeholders / AI-tells / '
          'frontmatter gaps.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
