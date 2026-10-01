"""Read public PRONI catalogue descriptions through their standard HTTP form."""
from pathlib import Path
import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings()
BASE = 'https://apps.proni.gov.uk/eCatNI_IE/'
OUT = Path(__file__).parent

def fields(html):
    soup = BeautifulSoup(html, 'html.parser')
    data = {x['name']: x.get('value', '') for x in soup.select('input[name]')
            if x.get('type') == 'hidden' or
            (x.get('type') == 'radio' and x.has_attr('checked'))}
    for x in soup.select('select[name]'):
        opt = x.select_one('option[selected]') or x.select_one('option')
        data[x['name']] = opt.get('value', '')
    return soup, data

session = requests.Session()
session.verify = False
adapter = requests.adapters.HTTPAdapter(max_retries=2)
session.mount('https://', adapter)
for ref in ['D1939/18/3/24']:
    r = session.get(BASE + 'SearchPage.aspx', timeout=10)
    soup, data = fields(r.text)
    data.update({'ctl00$ContentPlaceHolder1$txtPRONIRef': ref,
                 'ctl00$ContentPlaceHolder1$txtWords': '',
                 'ctl00$ContentPlaceHolder1$SearchArchiveBtn': 'Search'})
    session.post(BASE + 'SearchPage.aspx', data=data, timeout=10)
    r = session.get(BASE + 'SearchResults.aspx', timeout=10)
    soup, data = fields(r.text)
    more = soup.select_one('input[name$="$btnItemView"]')
    if more:
        data[more['name']] = more['value']
        r = session.post(BASE + 'SearchResults.aspx', data=data, timeout=10)
    stem = 'proni-' + ref.replace('/', '-')
    (OUT / (stem + '.html')).write_text(r.text)
    text = BeautifulSoup(r.text, 'html.parser').get_text('\n', strip=True)
    (OUT / (stem + '.txt')).write_text('Fetched 30 September 2026\nURL: ' + r.url + '\nReference: ' + ref + '\n\n' + text)
    print(ref, r.url, text, flush=True)
