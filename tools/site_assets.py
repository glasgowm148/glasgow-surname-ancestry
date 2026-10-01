#!/usr/bin/env python3
"""Audit and safely deduplicate local stylesheet and script tags in a site."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit

from html.parser import HTMLParser


def _local_key(value: str, base_url: str) -> str | None:
    resolved = urljoin(base_url, value)
    parts = urlsplit(resolved)
    base = urlsplit(base_url)
    original = urlsplit(value)
    if original.scheme or original.netloc or parts.netloc != base.netloc or not parts.path:
        return None
    return parts.path  # query variants intentionally share one asset key


def deduplicate_assets(html: str, *, base_url: str = "https://site.invalid/") -> tuple[str, list[str]]:
    """Remove duplicate local CSS/JS tags, retaining the last tag at first position.

    Returns ``(html, duplicate_paths)``. Inline and remote scripts are untouched.
    """
    # Generated pages use quoted attributes. Avoid tokenising every text node on
    # an already clean page; unusual markup still goes through the full parser.
    tags = re.findall(r'<(?:base|script|link)\b[^>]*>', html, re.I)
    attrs = lambda tag: dict((k.lower(), v) for k, _, v in re.findall(r'([\w-]+)\s*=\s*([\"\'])(.*?)\2', tag, re.S))
    if not any(re.search(r'\b(?:src|href)\s*=\s*[^\s\"\']', tag, re.I) for tag in tags):
        resolved_base = base_url
        for tag in tags:
            values = attrs(tag)
            if tag.lower().startswith('<base') and values.get('href'):
                resolved_base = urljoin(base_url, values['href']);break
        keys = []
        for tag in tags:
            values = attrs(tag)
            if tag.lower().startswith('<script'):
                value = values.get('src')
            elif tag.lower().startswith('<link') and 'stylesheet' in values.get('rel', '').lower().split():
                value = values.get('href')
            else:continue
            key = _local_key(value, resolved_base) if value else None
            if key:keys.append(key)
        if len(keys) == len(set(keys)):return html, []
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.tokens = []
            self.tags = []
            self.open_scripts = []
        def handle_starttag(self, tag, attrs):
            self.tags.append([len(self.tokens), tag, dict(attrs), self.get_starttag_text(), None])
            if tag == "script": self.open_scripts.append(self.tags[-1])
            self.tokens.append(self.get_starttag_text())
        def handle_startendtag(self, tag, attrs):
            self.tags.append([len(self.tokens), tag, dict(attrs), self.get_starttag_text(), len(self.tokens)])
            self.tokens.append(self.get_starttag_text())
        def handle_endtag(self, tag):
            index = len(self.tokens); self.tokens.append(f"</{tag}>")
            if tag == "script" and self.open_scripts:
                self.open_scripts.pop()[4] = index
        def handle_data(self, data): self.tokens.append(data)
        def handle_comment(self, data): self.tokens.append(f"<!--{data}-->")
        def handle_decl(self, decl): self.tokens.append(f"<!{decl}>")
        def handle_entityref(self, name): self.tokens.append(f"&{name};")
        def handle_charref(self, name): self.tokens.append(f"&#{name};")
        def handle_pi(self, data): self.tokens.append(f"<?{data}>")
    parser = Parser(); parser.feed(html); parser.close()
    seen: dict[str, object] = {}
    duplicates: list[str] = []
    replacements: dict[int, tuple[int, int]] = {}
    removed: set[int] = set()
    # A document base changes resolution for relative asset references.
    document_base = base_url
    for index, tag, attrs, raw, end in parser.tags:
        if tag == "base" and attrs.get("href"):
            document_base = urljoin(base_url, attrs["href"])
            break
    for index, tag, attrs, raw, end in parser.tags:
        attr = "href" if tag == "link" else "src"
        if tag == "link" and "stylesheet" not in (attrs.get("rel", "").lower().split()):
            continue
        value = attrs.get(attr)
        if not value:
            continue
        if tag not in {"link", "script"} or (tag == "script" and not attrs.get("src")):
            continue
        key = _local_key(value, document_base)
        if key is None:
            continue
        if key in seen:
            first = seen[key]
            duplicates.append(key)
            old_record = next(item for item in parser.tags if item[0] == first)
            old_end = old_record[4] if old_record[4] is not None else first
            new_end = end if tag == "script" and end is not None else index
            replacements[first] = (index, new_end)
            removed.update(range(first + 1, old_end + 1))
            removed.update(range(index, new_end + 1))
            seen[key] = first
        else:
            seen[key] = index
    if not duplicates: return html, []
    output = []
    for index, token in enumerate(parser.tokens):
        if index in replacements:
            start, end = replacements[index]
            output.extend(parser.tokens[start:end + 1])
        elif index not in removed:
            output.append(token)
    return "".join(output), duplicates


def duplicate_ids(html: str) -> list[str]:
    """Report duplicate IDs without changing document content."""
    class IDs(HTMLParser):
        def __init__(self): super().__init__(); self.ids = []
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key == "id": self.ids.append(value)
    soup = IDs(); soup.feed(html)
    counts: dict[str, int] = {}
    for identifier in soup.ids:
        counts[identifier] = counts.get(identifier, 0) + 1
    return sorted(identifier for identifier, count in counts.items() if count > 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("site_root", type=Path, nargs="?", default=Path(__file__).parents[1] / "www")
    args = parser.parse_args()
    root = args.site_root.resolve()
    changed = issues = 0
    for path in sorted(root.rglob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated, duplicates = deduplicate_assets(original, base_url="https://site.invalid/" + path.relative_to(root).as_posix())
        ids = duplicate_ids(original)
        if duplicates or ids:
            issues += len(duplicates) + len(ids)
            print(f"{path.relative_to(root)}: assets={duplicates} duplicate_ids={ids}")
        if args.write and updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"{changed} files changed; {issues} issues")
    return 1 if args.check and issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
