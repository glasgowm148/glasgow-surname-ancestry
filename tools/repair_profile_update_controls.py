"""Upgrade published profile panels without rebuilding person research."""
from pathlib import Path
from bs4 import BeautifulSoup
try:
    from build_research_catalog import _profile_update_controls
    from site_analytics import with_analytics
except ModuleNotFoundError:
    from tools.build_research_catalog import _profile_update_controls
    from tools.site_analytics import with_analytics

WEB = Path(__file__).resolve().parents[1] / 'www'

def repair(web=WEB):
    changed = 0
    for path in sorted((web / 'people').glob('*.html')):
        text = path.read_text()
        if 'id="wikitree-update"' not in text:
            continue
        soup = BeautifulSoup(text, 'html.parser')
        panel = soup.select_one('#wikitree-update')
        if panel is None:
            continue
        original = str(panel)
        updated = _profile_update_controls(original)
        if updated == original:
            repaired = with_analytics(text)
            if repaired != text:
                path.write_text(repaired)
                changed += 1
            continue
        before = [t.get_text() for t in panel.select('textarea')]
        replacement = BeautifulSoup(updated, 'html.parser').select_one('#wikitree-update')
        assert before == [t.get_text() for t in replacement.select('textarea')], path
        panel.replace_with(replacement)
        path.write_text(with_analytics(str(soup)))
        changed += 1
    return {'profile_control_pages': changed}

if __name__ == '__main__':
    print(repair())
