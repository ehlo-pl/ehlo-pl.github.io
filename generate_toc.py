import os
import re
import glob

POSTS_DIR = os.path.join('content', 'posts')
OUTPUT_FILE = 'toc.md'

def parse_frontmatter(filepath):
    title = os.path.basename(filepath)
    date_str = ""
    is_draft = False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Extract frontmatter (TOML +++ or YAML ---)
            match = re.search(r'^(?:\+\+\+|---)\s*(.*?)\n(?:\+\+\+|---)', content, re.DOTALL | re.MULTILINE)
            if match:
                frontmatter = match.group(1)
                
                # Extract title
                title_match = re.search(r'^title\s*[:=]\s*"(.*?)"', frontmatter, re.MULTILINE)
                if not title_match:
                    title_match = re.search(r'^title\s*[:=]\s*(.*?)$', frontmatter, re.MULTILINE)
                    
                if title_match:
                    title = title_match.group(1).strip('"\' ')
                
                # Extract date
                date_match = re.search(r'^date\s*[:=]\s*(.*?)$', frontmatter, re.MULTILINE)
                if date_match:
                    date_str = date_match.group(1).strip('"\' ')
                    
                # Extract draft status
                draft_match = re.search(r'^draft\s*[:=]\s*(.*?)$', frontmatter, re.MULTILINE | re.IGNORECASE)
                if draft_match:
                    draft_val = draft_match.group(1).strip('"\' ').lower()
                    if draft_val == 'true':
                        is_draft = True
                        
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        
    return {
        'filepath': filepath,
        'title': title,
        'date_str': date_str,
        'is_draft': is_draft,
        'sort_key': date_str if date_str else "0000-00-00"
    }

def main():
    files = glob.glob(os.path.join(POSTS_DIR, '*.md'))
    posts = []
    
    for f in files:
        posts.append(parse_frontmatter(f))
        
    # Sort descending by date string
    posts.sort(key=lambda x: x['sort_key'], reverse=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('# Table of Contents\n\n')
        for post in posts:
            rel_path = os.path.relpath(post['filepath']).replace('\\', '/')
            date_display = f" - {post['date_str'][:10]}" if len(post['date_str']) >= 10 else ""
            status_display = " **[DRAFT]**" if post['is_draft'] else ""
            f.write(f"- [{post['title']}]({rel_path}){date_display}{status_display}\n")
            
    print(f"Generated {OUTPUT_FILE} with {len(posts)} entries.")

if __name__ == "__main__":
    main()
