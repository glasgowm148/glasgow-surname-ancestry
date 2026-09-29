"""Single source for the public catalogue's light stylesheet and cache key."""

from pathlib import Path
import re

CATALOGUE_ASSET_VERSION = "20260927-one-tree-layout-2"
CSS_SOURCE = Path(__file__).with_name("catalogue-light.css")


def load_catalogue_css() -> str:
    css = CSS_SOURCE.read_text(encoding="utf-8")
    if ":root{color-scheme:light;" not in css or "color-scheme:dark" in css or "#07100e" in css:
        raise ValueError("Catalogue stylesheet must use the maintained light palette")
    return css


def write_catalogue_css(destination: Path) -> None:
    """Restore the maintained stylesheet during both builds and site repairs."""
    destination.write_text(load_catalogue_css() + "\n", encoding="utf-8")


def ensure_catalogue_stylesheet(page: str) -> str:
    """Load the catalogue layout in the unified route, including hashed shells."""
    if re.search(r'<link\b(?=[^>]*\bhref=["\']/people/catalogue\.css(?:\?[^"\']*)?["\'])[^>]*>', page, re.I):
        return page
    link = f'<link rel="stylesheet" href="/people/catalogue.css?v={CATALOGUE_ASSET_VERSION}">'
    shell = re.search(r'<link\b(?=[^>]*\bhref=["\']/assets/unified/site\.css(?:\?[^"\']*)?["\'])[^>]*>', page, re.I)
    if shell:
        return page[:shell.start()] + link + page[shell.start():]
    return page.replace('</head>', link + '</head>', 1)


def repair_clean_catalogue_stylesheet(web_root: Path) -> bool:
    path = web_root / 'catalogue/index.html'
    if not path.exists():
        return False
    original = path.read_text(encoding='utf-8')
    updated = ensure_catalogue_stylesheet(original)
    if updated == original:
        return False
    path.write_text(updated, encoding='utf-8')
    return True


def refresh_catalogue_stylesheet_references(web_root: Path) -> int:
    """Bust old dark-CSS URLs on pages retained by a targeted site repair."""
    pattern = re.compile(r'(people/catalogue\.css\?v=)[^"\'\s<>]+')
    changed = 0
    for path in web_root.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        updated = pattern.sub(lambda match: match.group(1) + CATALOGUE_ASSET_VERSION, original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed
