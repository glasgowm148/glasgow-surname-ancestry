#!/usr/bin/env python3
"""Collect maintained held identities, draft reviews, amendments and open studies."""
from pathlib import Path
from html import escape
import hashlib
import json
import re
import sys
import csv
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.free_space_edition import Renderer, public_text, shell_page
from tools.public_privacy import from_sources
from tools import repair_research_questions as questions

START, END = '<!-- research-queue:start -->', '<!-- research-queue:end -->'
NEW_START, NEW_END = '<!-- queue-new-profiles:start -->', '<!-- queue-new-profiles:end -->'
# Queue pages are a workroom: every one says so before its own status (S3-11).
WORKROOM_KICKER = 'Research workroom: leads, not findings'
# Reader words for stored statuses; the stored value (filters, data JSON) is unchanged.
STATUS_WORDS = {'On hold': 'On hold: needs another record'}


def queue_asset(ext):
    digest = hashlib.sha256((ROOT / ('tools/research_queue.' + ext)).read_bytes()).hexdigest()[:10]
    return '/assets/research/research-queue.' + ext + '?v=' + digest


def status_words(status):
    return STATUS_WORDS.get(status, status)

MATCH_LABELS = {'matched': 'Matched profile', 'compatible_candidate': 'Compatible candidate',
                'partly_matched': 'Partly matched',
                'no_compatible_profile': 'No compatible profile found', 'unnamed_record': 'Unnamed record',
                'already_linked': 'Already linked', 'research_question': 'Linked research question',
                'superseded': 'Superseded draft', 'disregarded': 'Excluded from profile creation'}


def apply_batch_progress(rows, root=ROOT):
    """Keep the fixed review denominator separate from unsaved amendments."""
    registry = json.loads((root / 'research/research-queue-matches.json').read_text())
    baseline_path = registry.get('current_batch')
    if not baseline_path:
        return None
    baseline = json.loads((root / baseline_path).read_text())['rows']
    path = (root / baseline_path).with_name('progress.json')
    results = json.loads(path.read_text()).get('baseline_results', {})
    complete = {'existing_profile', 'new_profile', 'disregarded', 'study'}
    baseline_ids = {r['id'] for r in baseline}
    if set(results) - baseline_ids:
        raise ValueError('Review results contain an item outside the frozen baseline')
    member_ids = {m['id']: r['id'] for r in baseline for m in r.get('members', [r])}
    for row in rows:
        ids = {row['id']} if row['id'] in baseline_ids else {
            member_ids.get(m['id'], m['id']) for m in row.get('members', [row])}
        checked = [results.get(ident, {}) for ident in ids]
        done = bool(checked) and all(r.get('disposition') in complete for r in checked)
        row['identity_review'] = dict(complete=done, baseline_ids=sorted(ids),
                                      dispositions=sorted({r['disposition'] for r in checked if r.get('disposition')}))
        if done and row['kind'] == 'Profile identity':
            row['research_status'] = row['status']
            status = row.get('match_review', {}).get('status')
            row['status'] = {'compatible_candidate': 'Compatible profile linked',
                             'partly_matched': 'Record matches recorded',
                             'no_compatible_profile': 'New profile suggested',
                             'unnamed_record': 'Record only',
                             'disregarded': 'Excluded from profile creation'}.get(status, row['status'])
    reviewed = sum(r.get('disposition') in complete for r in results.values())
    total = len(baseline)
    return dict(baseline_items=total, reviewed_items=reviewed, remaining_items=total-reviewed,
                percent_complete=round(100*reviewed/total, 1) if total else 100,
                reviewed_on=json.loads(path.read_text())['reviewed_on'])


def apply_match_reviews(rows, root=ROOT):
    path = root / 'research/research-queue-matches.json'
    if not path.exists():
        return rows
    data = json.loads(path.read_text())
    for row in rows:
        review = data.get('reviews', {}).get(row['id'])
        if not review:
            continue
        status = review['status']
        if status not in MATCH_LABELS:
            raise ValueError('Unknown identity review status: ' + status)
        profiles = review.get('profile_ids', [])
        if status in {'matched', 'compatible_candidate', 'already_linked'} and not profiles:
            raise ValueError('A linked review requires profile identifiers: ' + row['id'])
        # The completed review replaces name-score leads, including exclusions.
        row['profiles'] = list(dict.fromkeys(profiles))
        row['name'] = review.get('current_name', row.get('name', ''))
        row['match_review'] = dict(status=status, label=MATCH_LABELS[status],
                                  reviewed_on=review.get('reviewed_on', data['reviewed_on']),
                                  assessment=review['assessment'])
        row['canonical_groups'] = review.get('canonical_groups') or ([review['canonical_group']] if review.get('canonical_group') else [])
        if row['kind'] == 'Profile identity' and status == 'matched':
            row['status'] = 'Matched profile'
        if status == 'superseded':
            row['status'] = 'Superseded draft'
    return rows


def consolidate_record_reviews(rows):
    """Group shared research cases, retaining each person and event assessment."""
    groups, result = {}, []
    for row in rows:
        keys = row.get('canonical_groups', [])
        if row['kind'] != 'Profile identity' or len(keys) != 1:
            result.append(row)
            continue
        groups.setdefault(keys[0], []).append(row)
    for key, members in groups.items():
        if len(members) == 1:
            result.extend(members)
            continue
        first = dict(members[0])
        first.update(id='group-' + hashlib.sha256(key.encode()).hexdigest()[:12],
                     name=members[0]['name'] + ' · grouped research review',
                     members=members, canonical_groups=[key],
                     profiles=list(dict.fromkeys(p for row in members for p in row['profiles'])),
                     assessment=f'{len(members)} linked research notes for one research case. Each person and event remains separately assessed below.')
        if len({m.get('match_review', {}).get('status') for m in members}) > 1:
            first['match_review'] = dict(status='grouped', label='Mixed record identities',
                                        reviewed_on=max(m.get('match_review', {}).get('reviewed_on', '') for m in members),
                                        assessment=first['assessment'])
        result.append(first)
    return sorted(result, key=lambda row: (row['status'], row['name'].casefold()))


def profile_href(profile_id, web=ROOT / 'www'):
    if (web / 'people' / (profile_id.lower() + '.html')).is_file():
        return '/people/' + profile_id.lower() + '.html'
    return 'https://www.wikitree.com/wiki/' + profile_id


def new_profile_suggestions(root=ROOT):
    registry = json.loads((root / 'research/research-queue-matches.json').read_text())
    subjects = json.loads((root / 'research/latest-findings-subjects/subjects.json').read_text())
    suggestions = []
    for group in subjects['groups']:
        for person in group['people']:
            ident = 'subject-' + group['slug'] + '-' + person['anchor']
            review = registry['reviews'].get(ident, {})
            if review.get('status') != 'no_compatible_profile' or review.get('profile_ids'):
                continue
            text = person['wikitext']
            if not all(x in text for x in ('== Biography ==', '== Sources ==', '<references />', '<ref')):
                raise ValueError('New profile suggestion lacks a complete sourced draft: ' + ident)
            suggestions.append(dict(id=ident, name=person['name'],
                                    url='/research/subjects/' + group['slug'] + '/#' + person['anchor'],
                                    assessment=review['assessment'], reviewed_on=review.get('reviewed_on', registry['reviewed_on']),
                                    minimum_fields=person['minimum_fields'], draft_wikitext=text,
                                    duplicate_check=person['duplicate_check'],
                                    sources=[s for f in person['facts'] for s in f['sources']]))
    return suggestions


def render_new_profiles(suggestions):
    if not suggestions:
        return ''
    items = ''.join('<li><a href="' + escape(p['url'], quote=True) + '"><strong>' + escape(p['name']) +
                    '</strong> — complete sourced draft</a><p>' + escape(p['assessment']) +
                    '</p><small>Existing-profile search reviewed ' + escape(p['reviewed_on']) + '</small></li>'
                    for p in suggestions)
    return (NEW_START + '<section id="wikitree-new-profiles" class="r-section rq-section"><h2>Needs updated on WikiTree: suggested new profiles</h2>' +
            '<p>' + str(len(suggestions)) + ' people have sourced drafts after existing-profile searches found no compatible match. ' +
            'Each linked draft gives creation fields, citations, the actual duplicate-search scope and remaining source or family qualifications. ' +
            'These suggestions are separate from the existing-profile amendments above; none has been created on WikiTree.</p><details><summary>Read the new-profile suggestions (' +
            str(len(suggestions)) + ')</summary><ul>' + items + '</ul></details></section>' + NEW_END)


def collect(web=ROOT / 'www', root=ROOT):
    rows, drafts, used_files, fingerprints = [], [], set(), set()
    overrides=json.loads((root/'research/research-queue-overrides.json').read_text()).get('draft_replacements',{})
    def add(ident, name, kind, status, assessment, url, profiles=(), sources=()):
        rows.append(dict(id=ident, name=name, kind=kind, status=status,
                         assessment=assessment, url=url, profiles=list(profiles), sources=list(sources)))
    opr = json.loads((root / 'surname-research/indexes/scotlandspeople-opr-marriages-to-1700.json').read_text())
    for d in opr['new_drafts']:
        used_files.add(d['path'])
        add('opr-' + '-'.join(map(str, d['rows'])), d['title'], 'Profile identity',
            'On hold' if 'HOLD' in d['status'].upper() else 'Draft review', d['assessment'],
            '/branches/scottish-families/#opr-marriage-identity-' + '-'.join(map(str, d['rows'])),
            sources=[dict(title=opr['source_title'], url=opr['source_url'])])
    subjects = json.loads((root / 'research/latest-findings-subjects/subjects.json').read_text())
    for group in subjects['groups']:
        for p in group['people']:
            # A reviewed canonical handoff still owns its source draft after its
            # wording changes; textual fingerprints alone would resurrect it.
            used_files.update(p.get('draft_sources', []))
            fingerprints.add(re.sub(r'\s+', '', p['wikitext']))
            status = 'On hold' if 'HOLD' in p['status'].upper() else 'Draft review'
            add('subject-' + group['slug'] + '-' + p['anchor'], p['name'], 'Profile identity',
                status, p['identity_note'], '/research/subjects/' + group['slug'] + '/#' + p['anchor'],
                [c['id'] for c in p.get('candidates', [])],
                [s for f in p['facts'] for s in f.get('sources', [])])
    # Include the older draft register as well as the recent handoff catalogue.
    # Archived/completed drafts and OPR drafts already represented above are omitted.
    policy = from_sources()
    with (root / 'surname-research/indexes/groni-death-match-audit-2026-09-23.csv').open() as source:
        death_audit = {r['registration_number']: r for r in csv.DictReader(source)}
    for path in sorted((root / 'surname-research/new-people').glob('*.md')):
        raw = path.read_text(); top = raw[:700]
        if path.stem in overrides or str(path.relative_to(root)) in used_files or re.search(r'ARCHIVED DRAFT|LIVE PROFILE CREATED|DRAFT RETIRED', top, re.I):
            continue
        block = re.search(r'```wikitext\s*\n(.*?)\n```', raw, re.S | re.I)
        body = block[1] if block else raw[raw.find('[[Category:'):].strip() if '[[Category:' in raw else ''
        if not body or re.sub(r'\s+', '', body) in fingerprints:
            continue
        registration = re.search(r'D/\d{4}/\d+/\d+/\d+/\d+', raw)
        audit = death_audit.get(registration[0]) if registration else None
        if audit and audit['assessment'] in {'new_profile_created', 'existing_profile'}:
            continue
        # Only the public-safe historical account is rendered, never raw captures.
        text, _ = public_text(body, policy, path.stem)
        if not text.strip():
            continue
        held = bool(re.search(r'\bHOLD\b', top, re.I)) or bool(audit and audit['assessment']=='lead_attached')
        if not held and not re.search(r'READY TO CREATE', top, re.I):
            continue
        heading = re.search(r'^#\s+(.+)$', raw, re.M)
        name = re.sub(r'^(HOLD|READY TO CREATE)\s*[—:–-]\s*', '', heading[1]) if heading else re.sub(r'^\d{4}_[^_]+_[^_]+_', '',path.stem).replace('_', ' ')
        ident = 'draft-' + path.stem.lower().replace('_', '-')
        url = '/research/queue/' + ident + '/'
        paragraph = next((p.strip() for p in raw.split('\n\n') if p.strip() and not p.lstrip().startswith(('#', '```', '|', '-', '[[', '{{', '==', '<'))), '')
        assessment = re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', paragraph)
        assessment = re.sub(r'[*>`]', '', assessment).strip()[:850]
        if audit and audit['assessment']=='lead_attached':assessment='A compatible profile candidate remains: '+audit['reason']+' Reconcile the record identity before creating a distinct profile.'
        status = 'On hold' if held else 'Draft review'
        add(ident, name, 'Profile identity', status,
            assessment or 'Saved identity and source review; check the full draft before creating a profile.', url,
            re.findall(r'[A-Za-z]+-\d+',audit.get('candidate_wikitree_ids','')) if audit else ())
        drafts.append(dict(id=ident, name=name, status=status, assessment=assessment, wikitext=text, url=url))
    for path in sorted((web / 'people').glob('*.json')):
        if path.name.endswith('.network.json'):
            continue
        person = json.loads(path.read_text()); update = person.get('wikitree_update') or {}
        if update.get('pending'):
            assessment = update.get('summary', 'Reviewed amendment awaits a live WikiTree save.')
            review = update.get('application_review') or {}
            if review.get('assessment'):
                assessment += ' Application review (' + review.get('reviewed_on', 'undated') + '): ' + review['assessment']
            add('update-' + person['id'].lower(), person['name'], 'WikiTree amendment',
                'Pending update', assessment,
                urlparse(person['canonical_url']).path + '#wikitree-update', [person['id']])
    for slug, name, date, question, context in questions.QUESTIONS:
        add('question-' + slug, name, 'Research question', 'Open question', question,
            '/people/' + slug + '.html', [slug])
    for region, title, question, context, url in questions.ADDITIONAL_QUESTIONS:
        ident = hashlib.sha256((title + url).encode()).hexdigest()[:12]
        add('study-' + ident, title, 'Research question', 'Open question', question, url)
    # Identical already-published handoffs collapse, while distinct events remain separate.
    apply_match_reviews(rows, root)
    unique = {}; order = {'On hold': 0, 'Draft review': 1, 'Pending update': 2, 'Open question': 3,
                          'Matched profile': 4, 'Superseded draft': 5}
    for row in rows:
        unique.setdefault((row['url'], row['name']), row)
    return sorted(unique.values(), key=lambda r: (order[r['status']], r['name'].casefold())), drafts


def render(rows, progress=None):
    statuses = sorted({r['status'] for r in rows}); kinds = sorted({r['kind'] for r in rows})
    matches = sorted({r['match_review']['label'] for r in rows if r.get('match_review')})
    options = lambda values: ''.join(f'<option>{escape(v)}</option>' for v in values)
    body = []
    for r in rows:
        profiles = ', '.join(f'<a href="{escape(profile_href(p), quote=True)}">{escape(p)}</a>' for p in r['profiles'])
        sources = ' '.join(f'<a href="{escape(s["url"], quote=True)}" rel="noopener">{escape(s["title"])}</a>' for s in r['sources'])
        review = r.get('match_review') or {}
        match = '<strong>' + escape(review.get('label', 'Not yet reviewed')) + '</strong>'
        if review:
            match += '<small>Checked ' + escape(review['reviewed_on']) + '</small><details><summary>Identity assessment</summary><p>' + escape(review['assessment']) + '</p></details>'
        assessment = escape(r['assessment']) if r['assessment'] != review.get('assessment') else 'Identity check recorded; read the assessment.'
        members = r.get('members', [])
        related = '<details><summary>Separate people and research notes (' + str(len(members)) + ')</summary><ul>' + ''.join(
            '<li><a href="' + escape(m['url'], quote=True) + '">' + escape(m['name']) + '</a> — ' +
            escape(m.get('match_review', {}).get('assessment', m['assessment'])) +
            ' ' + ', '.join('<a href="' + escape(profile_href(pid), quote=True) + '">' + escape(pid) + '</a>' for pid in m['profiles']) + '</li>'
            for m in members) + '</ul></details>' if members else ''
        search = ' '.join((r['name'], r['assessment'], ' '.join(r['profiles']), review.get('assessment', ''),
                           ' '.join(m['name'] + ' ' + m.get('match_review', {}).get('assessment', m['assessment']) for m in members))).casefold()
        done = 'complete' if r.get('identity_review', {}).get('complete') else 'pending'
        body.append(f'<tr data-reviewed="{done}" data-status="{escape(r["status"], quote=True)}" data-kind="{escape(r["kind"], quote=True)}" data-match="{escape(review.get("label", ""), quote=True)}" data-search="{escape(search, quote=True)}"><td><a href="{escape(r["url"], quote=True)}">{escape(r["name"])}</a><small>{profiles}</small>{related}</td><td>{escape(status_words(r["status"]))}</td><td>{escape(r["kind"])}</td><td>{match}</td><td>{assessment}<small>{sources}</small></td></tr>')
    progress_html = ''
    review_control = ''
    if progress:
        progress_html = ('<p id="rq-progress" role="status"><strong>' +
                         str(progress['reviewed_items']) + ' of ' + str(progress['baseline_items']) +
                         ' reviewed (' + str(progress['percent_complete']) + '%)</strong> · ' +
                         str(progress['remaining_items']) + ' records need identity review.</p>' +
                         '<p>Existing-profile matches include explicitly tentative candidates. ' +
                         'A completed identity review does not complete an open study or save a WikiTree amendment.</p>')
        review_control = '<label>Identity review<select id="rq-review"><option value="">All items</option><option value="pending">Needs review</option><option value="complete">Reviewed</option></select></label>'
    return START + f'<section id="research-queue" class="r-section rq-section"><details class="rq-disclosure"><summary><span>Held and pending research</span><small>{len(rows)} record reviews, amendments and open studies</small></summary>{progress_html}<p>One worklist for the maintained research registers. Repeated research notes for one research case are grouped; expand them to see each person’s separate identity assessment. On hold means identity or source checks remain; a draft review still requires a current duplicate check before creation. Profile match records the completed identity check separately from outstanding research. Pending updates have not been saved on WikiTree. Each row links to its full evidence and next steps.</p><p><a href="/research/profile-matches/">Profile matching audit · all 140 original items →</a></p><div class="rq-controls"><label>Search research<input id="rq-query" type="search" placeholder="Person, place, profile or question"></label><label>Status<select id="rq-status"><option value="">All statuses</option>{options(statuses)}</select></label><label>Work type<select id="rq-kind"><option value="">All work</option>{options(kinds)}</select></label><label>Profile match<select id="rq-match"><option value="">All matches</option>{options(matches)}</select></label>{review_control}<button id="rq-clear" type="button">Clear</button></div><p id="rq-count" role="status">{len(rows)} research items</p><div class="rq-table-wrap"><table><thead><tr><th>Person or study</th><th>Status</th><th>Work type</th><th>Profile match</th><th>Assessment and evidence</th></tr></thead><tbody>'+''.join(body)+'</tbody></table></div></details></section>'+END


def publish_match_audit(web, template):
    baseline_path = ROOT / 'research/queue-match-audit-2026-09-30/baseline.json'
    registry_path = ROOT / 'research/research-queue-matches.json'
    if not baseline_path.exists() or not registry_path.exists():
        return
    baseline = json.loads(baseline_path.read_text())['rows']
    registry = json.loads(registry_path.read_text())
    if {r['id'] for r in baseline} - registry['reviews'].keys():
        return
    rows = [dict(row) for row in baseline]
    apply_match_reviews(rows)
    overrides = json.loads((ROOT/'research/research-queue-overrides.json').read_text())['draft_replacements']
    for row in rows:
        if row['id'].startswith('draft-'):
            replacement = next((v for k,v in overrides.items() if 'draft-' + k.lower().replace('_','-') == row['id']), None)
            if replacement:
                row['url'] = replacement['url']
        row['assessment'] = row['match_review']['assessment']
    from collections import Counter
    counts = Counter(row['match_review']['label'] for row in rows)
    summary = ' · '.join(f'{count} {label.lower()}' for label,count in sorted(counts.items()))
    main = '<main class="r-main" id="main"><header class="r-page-head"><span class="r-kicker">' + WORKROOM_KICKER + '</span><h1>Profile matching audit</h1><p>All 140 original worklist items reviewed on 30 September 2026. This includes 116 identity reviews, 10 already-linked amendments and 14 research questions. A compatible candidate is linked for comparison; identity remains qualified. No live WikiTree changes were made.</p><p>' + escape(summary) + '</p><p><a href="/catalogue/#research-queue">Current research queue</a> · <a href="/data/research-queue-match-audit.json">Download the reviewed matches</a></p></header>' + render(rows).replace('class="rq-disclosure"', 'class="rq-disclosure" open') + '</main>'
    page = shell_page(template, main, 'Profile matching audit', '/research/profile-matches/index.html')
    page = page.replace('</head>', '<link rel="stylesheet" href="' + queue_asset('css') + '"></head>')
    page = page.replace('</body>', '<script src="' + queue_asset('js') + '" defer></script></body>')
    target = web/'research/profile-matches/index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page)
    (web/'data/research-queue-match-audit.json').write_text(json.dumps(dict(schema_version=1, reviewed_on=registry['reviewed_on'], rows=rows), ensure_ascii=False, indent=2)+'\n')


def build(web=ROOT / 'www'):
    rows, drafts = collect(web)
    source_items = len(rows)
    rows = consolidate_record_reviews(rows)
    progress = apply_batch_progress(rows)
    suggestions = new_profile_suggestions()
    template = (web / 'about/index.html').read_text()
    publish_match_audit(web, template)
    overrides=json.loads((ROOT/'research/research-queue-overrides.json').read_text())['draft_replacements']
    for stem, replacement in overrides.items():
        target=web/'research/queue'/('draft-'+stem.lower().replace('_','-'))/'index.html'
        if target.exists():
            main=f'<main class="r-main" id="main"><header class="r-page-head"><span class="r-kicker">{WORKROOM_KICKER}</span><h1>Research note superseded</h1><p>{escape(replacement["reason"])}</p><a href="{escape(replacement["url"],quote=True)}">Open the current page →</a></header></main>'
            target.write_text(shell_page(template,main,'Research lead', '/'+target.relative_to(web).as_posix()))
    for d in drafts:
        body = Renderer([]).render(d['wikitext'])
        main = f'<main class="r-main" id="main"><header class="r-page-head"><span class="r-kicker">{WORKROOM_KICKER} · {escape(status_words(d["status"]))}</span><h1>{escape(d["name"])}</h1><p>{escape(d["assessment"])}</p><p><a href="/catalogue/#research-queue">← Held and pending research</a></p></header><article class="fsp-reading">{body}</article><details><summary>Saved WikiTree evidence draft</summary><textarea readonly style="width:100%;min-height:300px">{escape(d["wikitext"])}</textarea></details></main>'
        target = web / d['url'].strip('/') / 'index.html'; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(shell_page(template, main, d['name'], d['url'] + 'index.html'))
    for route in ('catalogue/index.html', 'catalogue.html'):
        path = web / route
        if not path.exists(): continue
        page = path.read_text(); section = render(rows, progress)
        if suggestions:
            section = section.replace('<div class="rq-controls">', '<p><a href="#wikitree-new-profiles">Needs updated on WikiTree · ' + str(len(suggestions)) + ' suggested new profiles with complete drafts →</a></p><div class="rq-controls">', 1)
        page = re.sub(re.escape(START) + r'.*?' + re.escape(END), '', page, flags=re.S)
        page = re.sub(re.escape(NEW_START) + r'.*?' + re.escape(NEW_END), '', page, flags=re.S)
        # Retire the old separate OPR-only queue now all those rows are represented.
        page = re.sub(r'<!-- opr-marriage-identities:start -->.*?<!-- opr-marriage-identities:end -->', '', page, flags=re.S)
        page = page.replace('</main>', section + render_new_profiles(suggestions) + '</main>', 1)
        page = re.sub(r'<(?:link|script)\b[^>]*(?:href|src)="/assets/research/research-queue\.[^" ]+"[^>]*>(?:</script>)?', '', page)
        page = page.replace('</head>', '<link rel="stylesheet" href="' + queue_asset('css') + '"></head>')
        page = page.replace('</body>', '<script src="' + queue_asset('js') + '" defer></script></body>')
        if 'id="research-queue-jump"' not in page:
            page = page.replace('</h1>', f'</h1><p id="research-queue-jump"><a href="/catalogue/#research-queue">Held and pending research · {len(rows)} items →</a></p>', 1)
        else:
            page = re.sub(r'(<p id="research-queue-jump">).*?(</p>)', lambda m:m[1]+f'<a href="/catalogue/#research-queue">Held and pending research · {len(rows)} items →</a>'+m[2], page, flags=re.S)
        pending = sum(row['kind'] == 'WikiTree amendment' for row in rows)
        page = re.sub(r'(<a\b[^>]*href="\?needsUpdate=1"[^>]*>\s*<strong>[^<]+</strong>\s*<span>)\d+ profiles ranked by significance', lambda m: m[1] + f'{pending} profiles ranked by significance', page)
        path.write_text(page)
    for ext in ('css', 'js'):
        (web / ('assets/research/research-queue.' + ext)).write_text((ROOT / ('tools/research_queue.' + ext)).read_text())
    (web / 'data/research-queue.json').write_text(json.dumps(dict(schema_version=1, rows=rows, review_progress=progress), ensure_ascii=False, indent=2)+'\n')
    (web / 'data/wikitree-new-profile-suggestions.json').write_text(json.dumps(dict(schema_version=1, people=suggestions), ensure_ascii=False, indent=2)+'\n')
    return dict(research_queue_items=len(rows), source_items=source_items, additional_public_drafts=len(drafts), suggested_new_profiles=len(suggestions))


if __name__ == '__main__':
    print(build())
