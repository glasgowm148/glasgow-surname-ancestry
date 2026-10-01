"""Read the complete public document, including its maintained lazy fragments.

Release validators and evidence checks use this view; browser entry pages remain
small. Only hash-named fragments inside the public site can be expanded.
"""
from pathlib import Path
from bs4 import BeautifulSoup


def read_html(path, site_root=None):
    path=Path(path);text=path.read_text(encoding='utf-8')
    if 'data-r-fragment=' not in text:return text
    if site_root is None:
        site_root=next((p for p in path.resolve().parents if p.name=='www'), None)
    if site_root is None:raise ValueError('Fragment reader needs a public site root')
    site_root=Path(site_root).resolve()
    soup=BeautifulSoup(text,'html.parser')
    for details in soup.select('details[data-r-fragment]'):
        url=details['data-r-fragment']
        if not url.startswith('/assets/research/fragments/') or '..' in Path(url).parts:
            raise ValueError('Only public research fragments may be expanded')
        target=(site_root/url.lstrip('/')).resolve();target.relative_to(site_root)
        fragment=BeautifulSoup(target.read_text(encoding='utf-8'),'html.parser').find('details')
        if fragment is None:raise ValueError(f'Malformed fragment: {url}')
        details.clear()
        for child in list(fragment.contents):details.append(child.extract())
    return str(soup)
