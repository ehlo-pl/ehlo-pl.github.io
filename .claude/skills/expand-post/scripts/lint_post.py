#!/usr/bin/env python3
"""Deep-lint a single blog post before finishing it.

Usage:
    python lint_post.py content/posts/2026-01-jmap-fundamentals.md

Reports, with line numbers: broken/mismatched code fences, AI-tell phrases,
second-person voice, and frontmatter schema gaps. Exit code is non-zero when
any issue is found, so it can gate a workflow.
"""

import re
import sys

import frontmatter as fm

# Languages we expect; used to catch capitalized/odd fence tags like ```Bash / ```Json
KNOWN_LANGS = {
    'bash', 'sh', 'shell', 'console', 'powershell', 'ps1', 'python', 'py',
    'json', 'yaml', 'yml', 'toml', 'ini', 'text', 'txt', 'html', 'xml', 'go',
    'javascript', 'js', 'sql', 'diff', 'dns', 'conf', 'cfg', '',
}

# Lines that clearly are prose, not code, if they show up inside a fence.
PROSE_IN_FENCE = re.compile(
    r'^\s*(Response example|What this does|Json\{|apiUrl\b|primaryAccounts\b)',
    re.IGNORECASE,
)


def lint_fences(lines):
    issues = []
    open_line = None      # line number where the currently-open fence started
    open_lang = None
    for i, line in enumerate(lines, start=1):
        m = re.match(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*(.*)$', line)
        if not m:
            if open_line is not None and PROSE_IN_FENCE.match(line):
                issues.append((i, 'fence',
                               f'prose leaking inside code fence opened at L{open_line}: '
                               f'{line.strip()[:50]!r}'))
            continue
        lang, trailing = m.group(1), m.group(2).strip()
        if open_line is None:
            # opening fence
            open_line, open_lang = i, lang
            if lang and lang not in KNOWN_LANGS and lang.lower() in KNOWN_LANGS:
                issues.append((i, 'fence',
                               f'code fence language should be lowercase: ```{lang} '
                               f'-> ```{lang.lower()}'))
            elif lang and lang.lower() not in KNOWN_LANGS:
                issues.append((i, 'fence', f'unrecognized fence language: ```{lang}'))
            if trailing:
                issues.append((i, 'fence',
                               f'text stuck to opening fence: ```{lang}{trailing!r} '
                               '(missing newline?)'))
        else:
            # closing fence
            if lang:
                issues.append((i, 'fence',
                               f'closing fence has a language tag (```{lang}); '
                               'closing fences should be bare ```'))
            open_line, open_lang = None, None
    if open_line is not None:
        issues.append((open_line, 'fence',
                       f'code fence opened here is never closed (unbalanced ```)'))
    return issues


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = argv[1]
    try:
        content = fm.read_text(path)
    except OSError as e:
        print(f'cannot read {path}: {e}')
        return 2

    lines = content.splitlines()
    raw, body = fm.split_frontmatter(content)

    issues = []
    issues += lint_fences(lines)
    for kind, lineno, matched in fm.find_ai_tells(content):
        issues.append((lineno, kind, f'{matched!r}'))
    for f in fm.missing_fields(raw):
        issues.append((0, 'frontmatter', f'missing field: {f}'))
    ph = fm.count_placeholders(body)
    if ph:
        issues.append((0, 'placeholder', f'{ph} skeleton placeholder(s) still present'))

    issues.sort(key=lambda x: (x[0], x[1]))
    print(f'== {path} ==')
    if not issues:
        print('  clean — no issues found.')
        return 0
    for lineno, kind, msg in issues:
        loc = f'L{lineno}' if lineno else '  --'
        print(f'  {loc:>5}  [{kind}] {msg}')
    print(f'\n  {len(issues)} issue(s).')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
