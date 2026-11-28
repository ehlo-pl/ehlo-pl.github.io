import os
import re
import glob
import tomllib

POSTS_DIR = os.path.join('content', 'posts')
OUTPUT_FILE = os.path.join('content', 'lists', 'toc.md')

# Frontmatter must open on the first line; later '---' / '+++' lines belong to the body.
FRONTMATTER_RE = re.compile(r'\A(\+\+\+|---)[ \t]*\n(.*?)^\1[ \t]*$', re.DOTALL | re.MULTILINE)


def parse_yaml(text):
    """Minimal parser for legacy YAML frontmatter: scalars, inline lists and block lists."""
    data = {}
    key = None
    for line in text.splitlines():
        item = re.match(r'^\s*-\s+(.*)$', line)
        if item and key:
            if not isinstance(data[key], list):
                data[key] = []
            data[key].append(item.group(1).strip().strip('"\''))
            continue
        pair = re.match(r'^(\w+)\s*:\s*(.*)$', line)
        if not pair:
            continue
        key, value = pair.group(1).lower(), pair.group(2).strip()
        if value.startswith('[') and value.endswith(']'):
            data[key] = [v.strip().strip('"\'') for v in value[1:-1].split(',') if v.strip()]
        else:
            data[key] = value.strip('"\'')
    return data


def parse_post(filepath):
    meta = {}
    line_count = 0

    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        line_count = len(content.splitlines())

        match = FRONTMATTER_RE.match(content)
        if match:
            fence, frontmatter = match.groups()
            meta = tomllib.loads(frontmatter) if fence == '+++' else parse_yaml(frontmatter)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

    tags = meta.get('tags') or []
    if isinstance(tags, str):
        tags = [tags]

    return {
        'filepath': filepath,
        'title': str(meta.get('title') or os.path.basename(filepath)).strip(),
        'date_str': str(meta.get('date') or ''),
        'is_draft': str(meta.get('draft', False)).lower() == 'true',
        'line_count': line_count,
        'tags': tags,
    }


def escape_cell(text):
    return text.replace('|', '\\|')


def format_section(heading, posts):
    # Newest first; posts without a date end up at the bottom.
    posts = sorted(posts, key=lambda p: (p['date_str'][:10], p['title'].lower()), reverse=True)

    lines = [
        f"## {heading} ({len(posts)})",
        '',
        '| Date | Title | Lines | Tags |',
        '|---|---|---:|---|',
    ]
    for post in posts:
        # Links are resolved from the folder that holds the TOC, not from the repo root.
        rel_path = os.path.relpath(post['filepath'], os.path.dirname(OUTPUT_FILE)).replace('\\', '/')
        if ' ' in rel_path:
            rel_path = f"<{rel_path}>"
        date_display = post['date_str'][:10] or '-'
        tags_display = ', '.join(post['tags']) or '-'
        lines.append(
            f"| {date_display} | [{escape_cell(post['title'])}]({rel_path}) "
            f"| {post['line_count']} | {escape_cell(tags_display)} |"
        )
    return '\n'.join(lines) + '\n'


def main():
    files = sorted(glob.glob(os.path.join(POSTS_DIR, '*.md')))
    posts = [parse_post(f) for f in files]

    published = [p for p in posts if not p['is_draft']]
    drafts = [p for p in posts if p['is_draft']]

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('# Table of Contents\n\n')
        f.write(format_section('Published', published))
        f.write('\n')
        f.write(format_section('DRAFT', drafts))

    print(f"Generated {OUTPUT_FILE}")
    print(f"  Published: {len(published)}")
    print(f"  Drafts:    {len(drafts)}")
    print(f"  Total:     {len(posts)}")


if __name__ == "__main__":
    main()
