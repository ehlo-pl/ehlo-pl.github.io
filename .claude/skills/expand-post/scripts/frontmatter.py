"""Shared frontmatter + draft-analysis helpers for the expand-post toolkit.

Stdlib only. The frontmatter parsing mirrors generate_toc.py (repo root) so the
whole toolkit reads posts the same way. Import this from the sibling scripts.
"""

import os
import re
import glob

# Resolve the repo root from this file's location:
# <repo>/.claude/skills/expand-post/scripts/frontmatter.py  ->  <repo>
REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
)
POSTS_DIR = os.path.join(REPO_ROOT, 'content', 'posts')

# Fields a finished post carries (see EXO-bypass-ExchangeOnlineManagement.md).
FULL_SCHEMA = ['title', 'date', 'draft', 'description', 'tags', 'categories']

# AI-tell phrases lifted from real dumped drafts in this repo.
AI_PREAMBLES = [
    r'Got it\s*[—-]',
    r'Sure!',
    r'Certainly[,!]',
    r'Below is a complete',
    r"Here'?s (?:a|the|how)",
    r'Great question',
    r"I'?d be happy to",
]
AI_TRAILING = [
    r'Would you like me to',
    r'Let me know if',
    r'Do you want me to',
    r'Shall I ',
    r'Feel free to ask',
]
AI_SECOND_PERSON = [
    r'\byour machine\b',
    r'\byou want to\b',
    r'\bas you can see\b',
    r'\byour system\b',
]


def read_text(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def split_frontmatter(content):
    """Return (raw_frontmatter, body). raw_frontmatter is '' if none found.

    Handles both TOML (+++) and YAML (---) delimiters, like generate_toc.py.
    """
    m = re.match(r'^(\+\+\+|---)\s*\n(.*?)\n(\+\+\+|---)\s*\n?(.*)$',
                 content, re.DOTALL)
    if not m:
        return '', content
    return m.group(2), m.group(4)


def present_fields(raw_frontmatter):
    """Names of frontmatter keys that are present (TOML '=' or YAML ':')."""
    fields = set()
    for line in raw_frontmatter.splitlines():
        km = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*[:=]', line)
        if km:
            fields.add(km.group(1).lower())
    return fields


def get_field(raw_frontmatter, name):
    """Raw string value of a frontmatter field, or None."""
    m = re.search(r'^\s*' + re.escape(name) + r'\s*[:=]\s*(.*?)\s*$',
                  raw_frontmatter, re.MULTILINE | re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip().strip('"\'')


def is_draft(raw_frontmatter):
    val = get_field(raw_frontmatter, 'draft')
    return (val or '').lower() == 'true'


def missing_fields(raw_frontmatter):
    present = present_fields(raw_frontmatter)
    return [f for f in FULL_SCHEMA if f not in present]


def count_placeholders(body):
    """Skeleton-post markers: [bracketed lines] and the Preparation notes block."""
    brackets = re.findall(r'^\s*\[[^\]\n]+\]\s*$', body, re.MULTILINE)
    prep = re.findall(r'Preparation notes', body)
    return len(brackets) + len(prep)


def find_ai_tells(text):
    """List of (kind, line_number, matched_text) across the whole file text."""
    hits = []
    groups = [
        ('preamble', AI_PREAMBLES),
        ('trailing-question', AI_TRAILING),
        ('second-person', AI_SECOND_PERSON),
    ]
    for lineno, line in enumerate(text.splitlines(), start=1):
        for kind, patterns in groups:
            for pat in patterns:
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    hits.append((kind, lineno, m.group(0)))
    return hits


def word_count(body):
    return len(re.findall(r'\S+', body))


def all_posts():
    """Absolute paths of every markdown post, sorted."""
    return sorted(glob.glob(os.path.join(POSTS_DIR, '*.md')))


def slugify(topic):
    slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')
    return slug or 'untitled'
