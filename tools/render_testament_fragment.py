"""Render associated manuscript material separately from a testament's text."""
from html import escape


def render_associated_fragment(fragment):
    if not fragment or not fragment.get("partial_transcription"):
        return ""
    reading = fragment["partial_transcription"]
    heading = "\n".join(reading["heading"])
    lines = "\n".join(f"{number:02d}  {line}" for number, line in enumerate(reading["lines"], 1))
    people = "".join(
        f'<li><strong>{escape(person["name"])}:</strong> {escape(person["finding"])}</li>'
        for person in fragment["reading_findings"]
    )
    questions = "".join(f'<li>{escape(question)}</li>' for question in fragment["next_steps"])
    return (
        '<details class="tx-extra tx-fragment" id="associated-fragment">'
        '<summary>Andro Huchesoun: associated testament fragment'
        '<span>Partial transcription, the children clause, and why strip 396A is in this PDF.</span></summary>'
        '<div class="tx-extra-body"><p class="r-kicker">Associated research material</p>'
        '<h2>A separate confirmation, with an unresolved connection</h2>'
        '<p><strong>Partial transcription only.</strong> The heading and several clauses are readable; '
        'the complete names, kinship grammar and legal roles have not been recovered.</p>'
        f'<p>{escape(fragment["interpretation"])}</p>'
        '<h3>What the names establish</h3><ul>' + people + '</ul>'
        '<h3>Read the supplied strip</h3>'
        f'<a href="{escape(fragment["image_url"], quote=True)}">'
        f'<img src="{escape(fragment["image_url"], quote=True)}" '
        'alt="Unaltered PDF page 3: the supplementary confirmation strip marked 396A" '
        'loading="lazy" style="display:block;max-width:100%;height:auto"></a>'
        '<p class="tx-key">Original supplied image. Click to enlarge. Image credit: '
        'Crown copyright, National Records of Scotland / ScotlandsPeople.</p>'
        '<h3>Heading</h3><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'
        + escape(heading) + '</pre><h3>Partial line-by-line reading</h3>'
        '<p>[...] marks unread text of unspecified length; [word?] is tentative. '
        'Brackets within a word expand an abbreviation. Gaps are not reconstructed from an expected formula.</p>'
        '<pre style="white-space:pre-wrap;overflow-wrap:anywhere">' + escape(lines) + '</pre>'
        f'<p><a href="{escape(fragment["reading_url"], quote=True)}" download>Download the partial reading</a></p>'
        '<h3 id="fragment-research-question">Why was it included with John?</h3>'
        f'<p><strong>{escape(fragment["research_question"])}</strong></p>'
        f'<p>{escape(fragment["attachment_limit"])}</p>'
        '<p>SCAN describes digitising complete registers in sequence, including loose leaves. '
        'That permits an archival or image-grouping explanation, but does not establish why this particular strip was included. '
        '<a href="https://www.ukoln.ac.uk/qa-focus/documents/case-studies/case-study-19/">Read SCAN\'s digitisation account</a>.</p>'
        f'<p>{escape(fragment["family_lead"])}</p>'
        '<h3>What would move this forward?</h3><ol>' + questions + '</ol>'
        '</div></details>'
    )
