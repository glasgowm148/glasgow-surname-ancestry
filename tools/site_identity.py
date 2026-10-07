"""One place for the site's name, owner line and correction route.

Every builder that prints the site's name, a page-title suffix, the footer or
the "who runs this" line reads it from here, so the site keeps one name.

Owner decision pending (7 October 2026): ``OWNER_NAME`` and ``CONTACT_URL``
are deliberately ``None`` until the owner says what name and contact route he
wants published.  While they are unset, pages print honest text (what a
correction should contain and that a direct contact route is being set up)
and never a dead button.  Set both values here and rebuild; nothing else needs
to change.
"""
from __future__ import annotations

from html import escape
import re

SITE_NAME = "Glasgow Surname Project"
SITE_SHORT_NAME = "Glasgow"
SITE_TAGLINE = "Family history research on people named Glasgow and their families"
SITE_RAIL_CAPTION = "Surname Project"
SITE_RAIL_NOTE = "People named Glasgow, their families and the records that connect them."
FOOTER_SUMMARY = "Family history research, with sources and notes on uncertain relationships."
SITE_URL = "https://glasgow.phenotype.dev"
TITLE_SEPARATOR = " · "

# Who runs the site and where corrections go.  Leave as None until the owner
# chooses; do not invent a name or an address.
OWNER_NAME: str | None = None
CONTACT_URL: str | None = None  # e.g. "mailto:…" or a hosted form URL

# Related projects.  "Glasgow Name Study" always means the WikiTree study,
# never this site.
WIKITREE_STUDY_NAME = "WikiTree Glasgow Name Study"
WIKITREE_STUDY_URL = "https://www.wikitree.com/wiki/Space:Glasgow_Name_Study"
DISCUSSION_GROUP_NAME = "Glasgow DNA project discussion group"
DISCUSSION_GROUP_URL = "https://groups.io/g/glasgowdnaproject/"

FEEDBACK_PATH = "/feedback/"

# Earlier names of the site found in page titles and the shared rail
# (site audit S3-03 / S1-10).  Longest first so that a longer variant wins.
LEGACY_TITLE_SUFFIXES = (
    "Y-DNA Timeline | The Glasgow Surname Project",
    "The Glasgow Surname Project", "The Glasgow surname project",
    "Glasgow Surname Project", "Glasgow surname archive", "Glasgow Surname Archive",
    "Glasgow source library", "Glasgow Source Library", "Glasgow Sources",
    "The family behind the surname", "Glasgow archive", "Root-Based Clusters",
    "The family atlas", "The family tree", "Glasgow",
)
# A legacy suffix that also named a section keeps the section in the title.
LEGACY_SUFFIX_SECTIONS = {
    "glasgow source library": "Source library",
    "glasgow sources": "Source library",
}
_SEPARATORS = r"(?:\s+(?:–|—|-)\s+|\s*(?:·|\||&middot;|&#183;)\s*)"
# Whole titles that were only a site name (not a page name such as "The family tree").
_SITE_NAME_ONLY = {"glasgow surname project", "the glasgow surname project", "glasgow surname archive",
                   "glasgow archive", "glasgow source library", "glasgow sources", "glasgow"}


def page_title(page: str, section: str | None = None) -> str:
    """Return "<page> · <section> · Glasgow Surname Project" (plain text).

    The section is left out when it is empty or repeats the page name.
    Callers escape the result for HTML.
    """
    parts = [part.strip() for part in (page, section) if part and part.strip()]
    if len(parts) == 2 and parts[1].casefold() in parts[0].casefold():
        parts = parts[:1]
    if parts and parts[-1] == SITE_NAME:
        parts = parts[:-1]
    return TITLE_SEPARATOR.join([*parts, SITE_NAME])


def normalise_title(title: str) -> str:
    """Give an existing <title> text the one site name and separator.

    Only a known site-name suffix after a separator is replaced, so a title
    such as "Alexander Glasgow" is never cut short.  Works on HTML text.
    """
    text = re.sub(r"\s+", " ", title or "").strip()
    section = None
    for _ in range(3):  # "X · Glasgow Sources · Glasgow Surname Project"
        for suffix in LEGACY_TITLE_SUFFIXES:
            match = re.search(_SEPARATORS + re.escape(suffix) + r"\s*$", text)
            if match:
                section = section or LEGACY_SUFFIX_SECTIONS.get(suffix.casefold())
                text = text[:match.start()].strip()
                break
        else:
            break
    text = re.sub(_SEPARATORS + r"$", "", text).strip()
    if text.casefold() in _SITE_NAME_ONLY:
        text = ""
    if section and "source" in text.casefold():
        section = None
    return page_title(text, section) if text else SITE_NAME


def owner_sentence() -> str:
    """Plain-text "who runs this" sentence, honest while the owner is unset."""
    if OWNER_NAME:
        return f"The {SITE_NAME} is run by {OWNER_NAME}."
    return (f"The {SITE_NAME} is a one-name study of the Glasgow surname. "
            "The name of the person who runs it is not yet published here.")


def contact_link_html(label: str = "Send a correction", css_class: str = "") -> str:
    """A working link: the contact route when set, else the correction guide."""
    cls = f' class="{escape(css_class, quote=True)}"' if css_class else ""
    if CONTACT_URL:
        external = not CONTACT_URL.startswith(("/", "mailto:"))
        rel = ' rel="noopener noreferrer" target="_blank"' if external else ""
        return f'<a{cls} href="{escape(CONTACT_URL, quote=True)}"{rel}>{escape(label)}</a>'
    return f'<a{cls} href="{FEEDBACK_PATH}">How to report a correction</a>'


def who_runs_this_html(heading_level: int = 2, heading_id: str = "who-runs-this", include_contact: bool = True) -> str:
    """The "Who runs this" block for About and the feedback page."""
    h = f"h{heading_level}"
    paragraphs = [escape(owner_sentence())]
    paragraphs.append(
        f'This site brings together research for the <a href="{WIKITREE_STUDY_URL}" target="_blank" '
        f'rel="noopener noreferrer">{escape(WIKITREE_STUDY_NAME)}</a>.')
    if not include_contact:
        pass
    elif CONTACT_URL:
        paragraphs.append(f"To send a correction, a record or a photograph: {contact_link_html()}.")
    else:
        paragraphs.append(
            "A direct contact route for corrections is being set up. Until it is ready, "
            f'<a href="{FEEDBACK_PATH}">this page explains what a useful correction contains</a> '
            "and where you can raise it now.")
    body = "".join(f"<p>{text}</p>" for text in paragraphs)
    return f'<section class="site-identity-who" id="{heading_id}"><{h}>Who runs this site</{h}>{body}</section>'


def footer_html() -> str:
    """The shared footer: one name, the owner line and stable About links."""
    owner = f"<p>{escape(owner_sentence())}</p>" if OWNER_NAME else ""
    correction = contact_link_html("Send a correction") if CONTACT_URL else f'<a href="{FEEDBACK_PATH}">Report a correction</a>'
    links = (
        '<a href="/about/">About the project</a>'
        '<a href="/evidence/">How to read the evidence</a>'
        '<a href="/latest-findings/">Latest findings</a>'
        '<a href="/changes/">Change log</a>'
        '<a href="/privacy/">Privacy</a>'
        + correction
        + f'<a href="{WIKITREE_STUDY_URL}" target="_blank" rel="noopener noreferrer">WikiTree Name Study &nearr;</a>'
        + f'<a href="{DISCUSSION_GROUP_URL}" target="_blank" rel="noopener noreferrer">Discussion group &nearr;</a>'
    )
    return (f'<footer class="g-footer"><div><span class="g-footer-name">{escape(SITE_NAME)}</span>'
            f'<p>{escape(FOOTER_SUMMARY)}</p>{owner}</div>'
            f'<nav class="g-footer-links" aria-label="Project information">{links}</nav></footer>')


def rail_bottom_html() -> str:
    """Rail foot: no repeated menu links, just the project line."""
    return ('<div class="g-rail-bottom"><div class="v3-rail-note">'
            f'<span>{escape(SITE_NAME)}</span><p>{escape(SITE_RAIL_NOTE)}</p></div></div>')


def og_site_name_tag() -> str:
    return f'<meta property="og:site_name" content="{escape(SITE_NAME, quote=True)}">'
