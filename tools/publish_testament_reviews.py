"""Publish detailed original-image reviews and approved manuscript material."""

from collections import Counter, defaultdict
from html import escape
from pathlib import Path
import json
import re
try:
    from tools.site_identity import SITE_NAME, page_title
except ModuleNotFoundError:
    from site_identity import SITE_NAME, page_title
try:
    from tools.public_manuscript_previews import approved_preview, restore_approved_previews
except ModuleNotFoundError:
    from public_manuscript_previews import approved_preview, restore_approved_previews

try:
    from tools.render_testament_walkthrough import (
        load_walkthrough, render_walkthrough, preview_walkthrough, render_supplied_original,
    )
except ModuleNotFoundError:
    from render_testament_walkthrough import (
        load_walkthrough, render_walkthrough, preview_walkthrough, render_supplied_original,
    )

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "www"
OUT = WEB / "research/transcriptions"
ALIASES = {"william-lanark-1673": "william-1673"}
AUXILIARY = {"george-1605"}
MARKER_START = "<!-- testament-original-review:start -->"
MARKER_END = "<!-- testament-original-review:end -->"
LICENSED_ASSET_URL = re.compile(r"/assets/research/testament-(?:crops|originals)/[^\"'\s]+")


def e(value):
    return escape(str(value), quote=True)


def paragraphs(values):
    return "".join(f"<p>{e(value)}</p>" for value in values)


def scrub_licensed_asset_urls(path):
    """Preserve approved manuscript URLs and remove unapproved public URLs."""
    if not path.is_file():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    def scrub(value):
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items()}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        if isinstance(value, str) and LICENSED_ASSET_URL.search(value):
            return LICENSED_ASSET_URL.sub(lambda match: match[0] if approved_preview(match[0]) else "Licensed scan withheld; consult cited source", value)
        return value

    cleaned = scrub(payload)
    if cleaned != payload:
        path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bullets(values):
    return "<ul>" + "".join(f"<li>{e(value)}</li>" for value in values) + "</ul>" if values else ""


def reviews():
    result = {}
    aliases = []
    for path in sorted((ROOT / "research/transcriptions").glob("originals-*/*.json")):
        review = json.loads(path.read_text(encoding="utf-8"))
        ident = review["id"]
        if not re.fullmatch(r"[a-z0-9-]+", ident):
            raise ValueError(f"Unsafe review identifier: {ident}")
        if ident in ALIASES:
            aliases.append(review)
            continue
        if ident not in result or review.get("reviewed_at", "") >= result[ident].get("reviewed_at", ""):
            result[ident] = review
    for alternate in aliases:
        ident = ALIASES[alternate["id"]]
        if ident not in result:
            result[ident] = dict(alternate, id=ident)
        else:
            result[ident]["source_files"] = list(dict.fromkeys(
                result[ident].get("source_files", []) + alternate.get("source_files", [])))
    return result


def profile_links(profiles):
    links = []
    for ident, label in profiles:
        local = f"/people/{ident.lower()}.html"
        if ident.startswith("record-"):
            if (WEB / local.lstrip("/")).is_file():
                links.append(f'<span><a href="{e(local)}">{e(label)}</a> (record-defined account)</span>')
            else:
                links.append(f'<span>{e(label)} (record-defined identity unresolved)</span>')
            continue
        wiki = f"https://www.wikitree.com/wiki/{ident}"
        if (WEB / local.lstrip("/")).is_file():
            links.append(f'<span><a href="{e(local)}">{e(label)}</a> '
                         f'(<a href="{e(wiki)}">{e(ident)} on WikiTree</a>)</span>')
        else:
            links.append(f'<span><a href="{e(wiki)}">{e(label)} ({e(ident)})</a></span>')
    return '<div class="tx-profile-list">' + "".join(links) + "</div>" if links else (
        '<p class="tx-no-text">No existing profile has been identified securely for this record.</p>')


def kin_card(walkthrough):
    try:
        from tools.render_transcription_kin_cards import render_kin_card
    except ModuleNotFoundError:
        from render_transcription_kin_cards import render_kin_card
    return render_kin_card(walkthrough)


def compact_card(item, walkthrough, *, preview, index_only, related):
    try:
        from tools.render_transcription_compact_cards import render_compact_card
    except ModuleNotFoundError:
        from render_transcription_compact_cards import render_compact_card
    return render_compact_card(item, walkthrough, preview=preview, index_only=index_only, related=related)


def review_body(review):
    ident = review["id"]
    lines = []
    for part in review.get("transcription", []):
        rows = "".join(f'<li><span>{e(line)}</span></li>' for line in part.get("lines", []))
        lines.append(f'<section class="tx-folio"><h3>Image / passage {e(part["page"])}</h3>'
                     f'<ol class="tx-lines">{rows}</ol></section>')
    sources = [Path(path).name for path in review.get("source_files", [])]
    original_url = f'/assets/research/testament-originals/{ident}.pdf'
    original_link = (f'<p><a href="{e(original_url)}">Read the complete supplied original (PDF)</a></p>'
                     if approved_preview(original_url) else "")
    return (
        render_walkthrough(review)
        + '<details class="tx-extra" id="case-analysis"><summary>Full case analysis'
        '<span>Interpretation, supporting evidence, changed readings and remaining questions.</span></summary><div class="tx-extra-body">'
        '<div class="tx-evidence-grid">'
        '<section class="tx-interpretation"><p class="r-kicker">Modern interpretation</p>'
        '<h2>What the record says</h2>' + paragraphs(review.get("plain_english", [])) + '</section>'
        '<section class="tx-evidence"><p class="r-kicker">Evidence and limits</p>'
        '<h2>What it establishes</h2>' + bullets(review.get("findings", [])) + '</section></div>'
        '<section class="tx-revision"><h2>What changed in this reading</h2>'
        + bullets(review.get("changes_from_previous", [])) + '</section>'
        '<section class="tx-open"><p class="r-kicker">Still open</p><h2>Do not fill these gaps with assumptions</h2>'
        + bullets(review.get("unresolved", [])) + '</section></div></details>'
        '<details class="tx-extra" id="working-reading"><summary>Full working transcription'
        '<span>Line-oriented readings, unresolved text and a downloadable plain-text version.</span></summary><div class="tx-extra-body">'
        '<section class="tx-transcript"><div class="tx-section-head">'
        '<div><p class="r-kicker">LLM-assisted working transcription</p><h2>Read the manuscript passages</h2></div>'
        f'<a class="tx-text-download" href="/research/transcriptions/{e(ident)}/reading.txt" download>Download text</a></div>'
        '<p class="tx-key">Square brackets mark uncertainty, editorial expansions or missing text. '
        'Ellipses mark omitted or unresolved wording. Numbering identifies lines in this working reading, '
        'not official manuscript line numbers. This is not a complete diplomatic edition.</p>'
        + "".join(lines) + '</section></div></details>'
        '<details class="tx-extra"><summary>Source files and reading provenance'
        '<span>Original references, pages examined and the limits of this review.</span></summary><div class="tx-extra-body">'
        '<section class="tx-provenance"><h2>Source coverage and reading provenance</h2>'
        + paragraphs([review.get("confidence_statement", "Selective working reading; unresolved text remains.")])
        + f'<p><strong>Reviewed:</strong> {e(review.get("reviewed_at", "Not recorded"))}. '
        f'<strong>Method:</strong> {e(review.get("reviewer", "LLM-assisted image review"))}.</p>'
        '<h3>Pages examined</h3>' + bullets(review.get("reviewed_pages", []))
        + '<h3>Supplied local source files</h3>' + bullets(sources)
        + original_link
        + '<p>The full originals remain in the local research archive. Selected unaltered crops are shown above '
        'for reading and commentary, with separate switchable highlights. Image credit: Crown copyright, '
        'National Records of Scotland / ScotlandsPeople. Duplicate downloads are not independent evidence. '
        'Consult the original using the reference above through '
        '<a href="https://www.scotlandspeople.gov.uk/search-records/legal-records/wills">ScotlandsPeople</a>.</p></section></div></details>'
    )


def text_reading(review):
    text = [review["title"], review["record"], f'Reviewed: {review.get("reviewed_at", "")}',
            "LLM-assisted working reading. Brackets/ellipses mark uncertainty or omissions; not a diplomatic edition.", ""]
    for part in review.get("transcription", []):
        text += ["IMAGE / PASSAGE " + str(part["page"])]
        text += [f"{number}. {line}" for number, line in enumerate(part.get("lines", []), 1)]
        text += [""]
    for key, title in (("plain_english", "MODERN INTERPRETATION"), ("findings", "EVIDENCE"),
                       ("changes_from_previous", "CHANGES"), ("unresolved", "UNRESOLVED")):
        text += [title, *review.get(key, []), ""]
    return "\n".join(text)


def shell(template, main, title, path):
    page = re.sub(r"<title>.*?</title>", lambda _: f"<title>{e(page_title(title))}</title>",
                  template, count=1, flags=re.S)
    page = re.sub(r'<main\b[^>]*>.*?</main>', lambda _: main, page, count=1, flags=re.S)
    page = re.sub(r'(data-g-path=")[^"]*', lambda m: m[1] + path, page, count=1)
    page = re.sub(r'(<body\b[^>]*class=")([^"]*)', lambda m: m[1] + m[2] + " tx-page", page, count=1)
    page = page.replace("</head>", '<link rel="stylesheet" href="/assets/research/transcriptions.css?v=originals-1">'
                        '<link rel="stylesheet" href="/assets/research/testament-reviews.css?v=1">'
                        '<link rel="stylesheet" href="/assets/research/testament-walkthrough.css?v=1">'
                        '<link rel="stylesheet" href="/assets/research/testament-study.css?v=2">'
                        '<link rel="stylesheet" href="/assets/research/testament-kinship.css?v=1">'
                        '<link rel="stylesheet" href="/assets/research/transcription-kin-cards.css?v=7">'
                        '<script defer src="/assets/research/testament-walkthrough.js?v=2"></script></head>', 1)
    page = re.sub(r'<meta\b(?=[^>]*\bname="description")[^>]*>',
                  '<meta name="description" content="Original-register working transcriptions, source coverage, '
                  'family evidence and unresolved readings from the Glasgow testament research.">', page, count=1)
    return page


COURTS = (
    ("edinburgh", "Edinburgh", "Edinburgh Commissary Court", "CC8"),
    ("glasgow", "Glasgow", "Glasgow Commissary Court", "CC9"),
    ("lanark", "Lanark", "Lanark Commissary Court", "CC14"),
    ("other", "Other courts", "Other testament records", ""),
)


def court_area(record):
    for key, _, _, reference in COURTS:
        if reference and re.search(r"\b" + reference + r"/", record):
            return key
    return "other"


def repair(extracted_text, render_reading, *, update_dossiers=True):
    restore_approved_previews()
    try:
        from tools.render_testament_kinship import render_name_audit, feature_link, publish_family_report
    except ModuleNotFoundError:
        from render_testament_kinship import render_name_audit, feature_link, publish_family_report
    changed = Counter()
    data = json.loads((ROOT / "research/transcriptions/index.json").read_text(encoding="utf-8"))
    # The original manifest retains the earlier readings; image reviews are independently versioned.
    attempts = data.get("attempts", data.get("transcriptions", []))
    old = {item["id"]: item for item in attempts}
    fresh = reviews()
    template = (WEB / "research/index.html").read_text(encoding="utf-8")
    cases = {**old}
    for ident, review in fresh.items():
        if ident not in cases:
            cases[ident] = {"id": ident, "title": review["title"], "date": review.get("date", ""),
                            "record": review["record"], "profiles": review.get("profiles", [])}

    def write(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        changed["testament_review_outputs"] += 1

    cards = []
    area_cards = defaultdict(list)
    area_years = defaultdict(list)
    related = []
    profile_cases = defaultdict(list)
    for ident, item in sorted(cases.items(), key=lambda pair: (re.search(r"\d{4}", pair[0])[0]
                                                               if re.search(r"\d{4}", pair[0]) else "9999", pair[0])):
        review = fresh.get(ident)
        title = review["title"] if review else item["title"]
        record = review["record"] if review else item.get("record", "")
        date = review.get("date", "") if review else item.get("date", "")
        summary = (review.get("plain_english") or [item.get("summary", "")])[0] if review else item.get("summary", "")
        profiles = review.get("profiles", []) if review else item.get("profiles", [])
        supplied_sources = [path for path in item.get("source_files", []) if (ROOT / path).is_file()]
        label = "Related baptism, not a testament" if ident in AUXILIARY else (
            "Illustrated manuscript reading" if review else (
                "Original supplied; fresh reading pending" if supplied_sources else
                "Earlier reading; original not yet matched"))
        index_only = item.get("evidence_basis") == "index"
        if index_only:
            label = "Indexed record; manuscript transcription pending"
        href = f"/research/transcriptions/{ident}/"
        year_match = re.search(r"\d{4}", ident)
        year = year_match[0] if year_match else "Undated"
        action = "View supplied original" if supplied_sources and not review else "Follow the manuscript"
        if index_only:
            action = "View indexed record"
        walkthrough = load_walkthrough(ident)
        card = compact_card(item, walkthrough,
                            preview=preview_walkthrough(ident, item.get("original_preview") if supplied_sources else None),
                            index_only=index_only, related=ident in AUXILIARY)
        (related if ident in AUXILIARY else cards).append(card)
        if ident not in AUXILIARY:
            area = court_area(record)
            area_cards[area].append(card)
            area_years[area].append(year)
        legacy = extracted_text(item) if item.get("start") else ""
        history = ""
        if legacy:
            history = ('<details class="tx-reading tx-history"><summary>Earlier saved reading and research notes'
                       '<span>Preserved for comparison; later corrections above take precedence. '
                       'These may include pages absent from the newly supplied scans.</span></summary>'
                       '<div class="tx-manuscript">' + render_reading(legacy) + '</div></details>')
        elif item.get("summary") and not index_only:
            history = '<section class="tx-history"><h2>Earlier saved assessment</h2>' + paragraphs([item["summary"]]) + '</section>'
        if review:
            try:
                from tools.render_testament_index_entry import render_index_confirmation
                from tools.render_testament_fragment import render_associated_fragment
            except ModuleNotFoundError:
                from render_testament_index_entry import render_index_confirmation
                from render_testament_fragment import render_associated_fragment
            body = render_index_confirmation(item.get("index_confirmation") or review.get("index_confirmation")) + render_name_audit(ident) + render_associated_fragment(review.get("associated_fragment")) + review_body(review)
            if review.get("associated_fragment"):
                write(OUT / ident / "associated-fragment.json",
                      json.dumps(review["associated_fragment"], ensure_ascii=False, indent=2) + "\n")
            write(OUT / ident / "reading.txt", text_reading(review))
            for profile in profiles:
                profile_cases[profile[0]].append((href, title, profile[1], review.get("reviewed_at", "")))
        elif supplied_sources:
            body = render_supplied_original(item, supplied_sources)
        elif index_only:
            try:
                from tools.render_testament_index_entry import render_index_entry
            except ModuleNotFoundError:
                from render_testament_index_entry import render_index_entry
            body = render_index_entry(item, walkthrough)
        else:
            body = '<p class="tx-no-text">No local original has yet been matched to this catalogue entry. '
            body += 'The earlier assessment is retained below, not labelled as freshly transcribed.</p>'
        main = (f'<main class="tx-main tx-case" id="main"><nav class="tx-breadcrumb" aria-label="Research trail">'
                f'<a href="/research/">Research</a><span>/</span><a href="/research/transcriptions/">Transcriptions</a></nav>'
                f'<header class="tx-hero"><p class="r-kicker">{e(label)}</p><h1>{e(title)}</h1>'
                f'<p>{e(date)}</p><p class="tx-reference">{e(record)}</p></header>'
                + body + '<details class="tx-associated"><summary>All associated profiles and identity comparisons'
                '<span>Includes possible and rejected associations, not just proved relatives.</span></summary>'
                + profile_links(profiles) + '</details>' + history
                + '<p class="tx-back"><a href="/research/transcriptions/">Back to all transcriptions</a></p></main>')
        write(OUT / ident / "index.html", shell(template, main, title, href + "index.html"))

    count = len(cards)
    fresh_count = len([ident for ident in fresh if ident not in AUXILIARY])
    overview = data.get("overview_url", "https://www.wikitree.com/wiki/Space:Glasgow_Wills_%26_Testaments")
    area_nav = []
    area_sections = []
    for key, name, court, _ in COURTS:
        if not area_cards[key]:
            continue
        years = area_years[key]
        span = years[0] if years[0] == years[-1] else f"{years[0]}-{years[-1]}"
        area_nav.append(f'<a href="#court-{key}"><span>{e(name)}</span><small>{len(area_cards[key])} records &middot; {e(span)}</small></a>')
        area_sections.append(f'<section class="tx-court-section" id="court-{key}" aria-labelledby="court-title-{key}">'
                             '<header class="tx-court-heading"><div><p class="r-kicker">'
                             f'{e(court)}</p><h2 id="court-title-{key}">{e(name)}</h2></div>'
                             f'<p>{e(span)}<span>{len(area_cards[key])} testament records</span></p></header>'
                             '<div class="tx-ledger">' + "".join(area_cards[key]) + '</div></section>')
    main = ('<main class="tx-main tx-index" id="main"><nav class="tx-breadcrumb" aria-label="Research trail">'
            '<a href="/research/">Research</a><span>/</span><span>Transcriptions</span></nav>'
            '<header class="tx-hero tx-index-hero"><div><p class="r-kicker">The manuscript collection</p>'
            '<h1>Read the wills.<br>Follow the evidence.</h1>'
            '<p>Names, families and the strokes that connect them. Explore the original handwriting, '
            'then work through each reading word by word.</p>'
            f'<a class="tx-overview" href="{e(overview)}">WikiTree wills and testaments study <span aria-hidden="true">&nearr;</span></a></div>'
            '<figure class="tx-index-cover">'
            + ('<img src="/assets/research/testament-crops/john-1577-family.jpg" alt="The widow-and-children passage in John Glasgow\'s 1577 testament">'
               if approved_preview('/assets/research/testament-crops/john-1577-family.jpg') else '<p class="tx-licensed-withheld">Licensed scan withheld; consult cited source</p>')
            +
            '<figcaption><span>From the original register</span><strong>1577</strong>'
            '<span>John Glasgow &middot; Edinburgh</span></figcaption></figure></header>'
            '<dl class="tx-review-counts">'
            f'<div><dt>Testament cases</dt><dd>{count}</dd></div>'
            f'<div><dt>Originals revisited</dt><dd>{fresh_count}</dd></div>'
            f'<div><dt>Awaiting fresh reading</dt><dd>{count - fresh_count}</dd></div></dl>'
            + feature_link() + '<section class="tx-browse-courts" aria-label="Browse records by court area">'
            '<div><p class="r-kicker">Find a record</p><h2>Three courts. Over two centuries.</h2>'
            '<p>Grouped by the court that kept the record, then ordered from earliest to latest. '
            'The large year is the record year, which may differ from the year of death.</p></div>'
            '<nav class="tx-area-nav" aria-label="Court areas">' + "".join(area_nav) + '</nav></section>'
            + "".join(area_sections))
    if related:
        main += ('<section class="tx-related" aria-labelledby="tx-related-title"><p class="r-kicker">Filed with the testaments</p>'
                 '<h2 id="tx-related-title">A baptism, not another will</h2>'
                 '<p>George\'s 1605 image is a parish baptism. It is retained here as a corrected source identification '
                 'and excluded from testament totals.</p><div class="tx-ledger">' + "".join(related) + '</div></section>')
    main += ('<details class="tx-method"><summary>How the illustrated readings work</summary>'
             '<p>These are <strong>LLM-assisted working transcriptions</strong>, not certified editions. '
             'Examining every supplied page does not mean every word has been deciphered. '
             'A widow is not automatically the children\'s mother; an executor, witness or creditor is not automatically a relative. '
             'Each case shows what was read, what changed and what remains unresolved.</p></details>')
    main += '</main>'
    write(OUT / "index.html", shell(template, main, "Wills and testament transcriptions", "/research/transcriptions/index.html"))
    publish_family_report(write, shell, template, fresh, OUT)
    for path in OUT.rglob("*.json"):
        scrub_licensed_asset_urls(path)

    if not update_dossiers:
        return changed

    # Generate the local links after case files exist; no uncertain relationship is added to the tree.
    for ident, links in profile_cases.items():
        path = WEB / "people" / f"{ident.lower()}.html"
        if not path.is_file():
            continue
        page = path.read_text(encoding="utf-8")
        page = re.sub(re.escape(MARKER_START) + ".*?" + re.escape(MARKER_END), "", page, flags=re.S)
        items = "".join(f'<li><a href="{e(href)}">{e(title)}</a> '
                        f'<span>{e(label)}; reviewed {e(date)}</span></li>' for href, title, label, date in links)
        box = (MARKER_START + '<aside class="tx-person-update" aria-label="Original record re-examination">'
               '<p class="tx-person-kicker">Original records re-examined</p><h2>Latest testament evidence</h2>'
               '<p>Read the fresh manuscript passages and the qualifications on identity and kinship. '
               'Inclusion here does not itself establish a family relationship.</p><ul>' + items + '</ul></aside>' + MARKER_END)
        page, inserted = re.subn(r'(<main\b[^>]*>)', lambda m: m[1] + box, page, count=1)
        if not inserted:
            page, inserted = re.subn(r'(<div\b[^>]*\bid="g-page"[^>]*>)', lambda m: m[1] + box, page, count=1)
        if inserted:
            if '/assets/research/testament-reviews.css' not in page:
                page = page.replace('</head>', '<link rel="stylesheet" href="/assets/research/testament-reviews.css?v=1"></head>', 1)
            write(path, page)
    return changed
