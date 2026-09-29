#!/usr/bin/env python3
"""Keep old public person URLs usable after WikiTree profile merges."""

from html import escape
import json
from pathlib import Path

try:
    from project_paths import normalized_profile_redirects
except ModuleNotFoundError:
    from tools.project_paths import normalized_profile_redirects


ROOT = Path(__file__).resolve().parents[1]


def publish() -> int:
    site = ROOT / "www" / "people"
    payload = json.loads((ROOT / "data/wikitree/live-profile-overrides.json").read_text())
    redirects = normalized_profile_redirects(payload.get("redirects", {}))
    written = 0
    for old, new in sorted(redirects.items()):
        target = site / f"{new.lower()}.html"
        if old == new or not target.is_file():
            continue
        alias = site / f"{old.lower()}.html"
        href = f"{new.lower()}.html"
        canonical = f"https://glasgow.phenotype.dev/people/{href}"
        page = (
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{escape(old)} merged into {escape(new)}</title>"
            f"<link rel=\"canonical\" href=\"{escape(canonical, quote=True)}\">"
            f"<meta http-equiv=\"refresh\" content=\"0; url={escape(href, quote=True)}\">"
            "</head><body><main>"
            f"<h1>{escape(old)} was merged</h1><p>The current research dossier is "
            f"<a href=\"{escape(href, quote=True)}\">{escape(new)}</a>.</p>"
            "</main></body></html>\n"
        )
        if not alias.exists() or alias.read_text() != page:
            alias.write_text(page)
            written += 1
    return written


if __name__ == "__main__":
    print(f"Published {publish()} WikiTree merge alias page(s).")
