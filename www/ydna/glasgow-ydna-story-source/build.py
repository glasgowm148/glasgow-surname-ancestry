#!/usr/bin/env python3
"""Build the standalone explorer. Python standard library only.

Usage:
    python3 build.py
    python3 build.py --output /path/to/site/ydna/index.html
"""
import argparse
import json
import os
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=root / 'index.html')
    parser.add_argument('--site-base', help='Relative URL from the output directory to the www root')
    args = parser.parse_args()
    try:
        template = (root / 'source/template.html').read_text(encoding='utf-8')
        data = json.loads((root / 'data.json').read_text(encoding='utf-8'))
        site_root = root.parents[1]
        output_parent = args.output.resolve().parent
        if args.site_base:
            site_base = args.site_base
        elif output_parent.is_relative_to(site_root.resolve()):
            site_base = os.path.relpath(site_root.resolve(), output_parent)
        else:
            site_base = '..'
        site_base = site_base.rstrip('/') + '/'
        public_output = args.output.resolve() == (site_root / 'ydna' / 'index.html').resolve()
        parts = {
            'CSS': '\n'.join((root / 'source' / f).read_text(encoding='utf-8') for f in ('style.css', 'story.css')),
            'JS': (root / 'source/app.js').read_text(encoding='utf-8'),
            'SITE_BASE': site_base,
            'ROUTE_REDIRECT': '<script data-clean-index-redirect>if(location.protocol!=="file:"&&location.pathname.endsWith("/index.html"))location.replace("/ydna"+location.search+location.hash);</script>' if public_output else '',
            'DATA': json.dumps(data, ensure_ascii=False, indent=2).replace('</', '<\\/'),
        }
        for name, content in parts.items():
            token = '__' + name + '__'
            if template.count(token) != 1:
                raise ValueError(f'Expected exactly one {token} in the template')
            template = template.replace(token, content)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(template, encoding='utf-8')
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f'Build failed: {exc}\n')
    print(f'Built {args.output} ({args.output.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
