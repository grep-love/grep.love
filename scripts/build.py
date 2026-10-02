#!/usr/bin/env python3
"""Build the static website and raw pattern endpoints."""
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def pattern_card(entry, pattern):
    escape = html.escape
    name = escape(entry['name'])
    aliases = ', '.join(
        f'<a href="{escape(alias)}">/{escape(alias)}</a>'
        for alias in entry['aliases']
    )
    alias_note = f'<p class="alias">Also available at {aliases}</p>' if aliases else ''
    return f'''<article class="pattern">
      <div class="pattern-top">
        <h3>{escape(entry['title'])}</h3>
        <a class="endpoint" href="{name}">/{name} ↗</a>
      </div>
      <p>{escape(entry['description'])}</p>
      <pre class="sample"><code>{escape(entry['example'])}</code></pre>
      <details>
        <summary>Pattern &amp; scope</summary>
        <pre><code>{escape(pattern.strip())}</code></pre>
        <p>{escape(entry['limitations'])}</p>
      </details>
      {alias_note}
    </article>'''


def build(site_url='http://localhost:8000', output=None):
    catalog = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
    repository = os.environ.get('GITHUB_REPOSITORY', '')
    if repository and not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid GITHUB_REPOSITORY')
    # URLs are embedded in copyable shell commands as well as HTML.
    if not re.fullmatch(r'https?://[A-Za-z0-9.:-]+(?:/[A-Za-z0-9._/-]*)?', site_url):
        raise ValueError('SITE_URL must be an HTTP(S) website URL without query parameters')

    names = set()
    patterns = []
    for entry in catalog:
        for name in [entry['name'], *entry['aliases']]:
            if not re.fullmatch(r'[a-z][a-z0-9-]*', name) or name in names:
                raise ValueError(f'Invalid or duplicate endpoint: {name}')
            names.add(name)
        data = (ROOT / 'patterns' / entry['name']).read_bytes()
        lines = data.decode('ascii').splitlines()
        if (not data.endswith(b'\n') or b'\r' in data or not lines
                or any(not line.strip() or line.startswith('#') for line in lines)):
            raise ValueError(f"{entry['name']}: require nonblank ASCII regex lines and a final LF")
        patterns.append((entry, data))

    out = Path(output) if output is not None else ROOT / '_site'
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / 'site', out)
    cards = []
    manifest = []
    for entry, data in patterns:
        for name in [entry['name'], *entry['aliases']]:
            (out / name).write_bytes(data)
        manifest.append({
            **entry,
            'sha256': hashlib.sha256(data).hexdigest(),
            'engine': 'POSIX ERE',
            'flags': '-E',
            'locale': 'C',
        })
        cards.append(pattern_card(entry, data.decode('ascii')))

    replacements = {
        '{{CARDS}}': '\n'.join(cards),
        '{{SITE_URL}}': html.escape(site_url.rstrip('/')),
        '{{REPO_URL}}': f'https://github.com/{repository}' if repository else 'contributing.html',
    }
    for page in out.glob('*.html'):
        contents = page.read_text(encoding='utf-8')
        for placeholder, value in replacements.items():
            contents = contents.replace(placeholder, value)
        page.write_text(contents, encoding='utf-8')
    (out / 'catalog.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (out / '.nojekyll').touch()
    print(f'Built {len(names)} endpoints in {out}')


if __name__ == '__main__':
    build(site_url=os.environ.get('SITE_URL', 'http://localhost:8000'))
