#!/usr/bin/env python3
"""Add the minimal Glasgow Name Study navigation to captured FSP sources."""

from pathlib import Path


PAGE_DIR = Path("research/free-space-pages/pages")
PRE1500_DIR = Path("surname-research/free-space-pages")
SKIP = {
    10, 13, 15, 27, 63, 65,  # redirects, dead title, duplicate capture, or live aliases
    47, 48, 49, 50, 51, 52, 53, 54, 55, 56,  # preserve the established haplogroup-page designs
}
NAV = (
    "<small>'''Glasgow Name Study:''' [[Space:Glasgow Name Study|project home]] · "
    "[[Space:Glasgow Research|research directory]] · "
    "[https://glasgow.phenotype.dev/ digital workbench]</small>\n"
)
PRE1500_NAV = (
    "<small>'''Glasgow Name Study:''' [[Space:Glasgow Name Study|project home]] · "
    "[https://www.wikitree.com/wiki/Space:Bearers_of_the_%27%27de_Glasgu%27%27_Name_and_the_Emergence_of_the_Glasgow_Surname%2C_c.1175%E2%80%931500 chronological bearer register] · "
    "[[Space:Glasgow Research|research directory]] · "
    "[https://glasgow.phenotype.dev/catalogue research catalogue]</small>\n"
)
PRE1500_SKIP = {
    "README.md",
    "all_origins.md",
    "Glasgow_Name_Study.md",
    "Glasgow_Branches_In_15th_and_16th_Century_Scotland.md",
    "Glasgow_Branches_In_Early_Ireland.md",
    "Glasgow_Families_of_County_Londonderry.md",
}
ROLE_BY_NUMBER = {
    5: "current evidence hub",
    12: "current deep-Y-DNA guide",
    14: "current evidence hub",
    16: "current evidence hub",
    17: "current DNA project guide",
    18: "current specialist study",
    19: "legacy narrative",
    20: "hypothesis and network study",
    21: "project home and current synthesis",
    22: "legacy origins notebook",
    23: "project directory and work register",
    24: "current surname-origin summary",
    25: "indexed record notebook",
    26: "specialist notebook",
    28: "record notebook",
    29: "active relationship hypothesis",
    30: "active identity study",
    31: "record-access guide",
    45: "candidate and exclusion notebook",
    46: "personal genetic notebook",
    47: "DNA branch guide",
    48: "DNA branch guide",
    49: "DNA branch guide",
    50: "DNA branch guide",
    51: "DNA branch guide",
    52: "DNA branch guide",
    53: "DNA project-results notebook",
    54: "DNA branch guide",
    55: "DNA branch guide",
    56: "DNA branch guide",
    57: "current specialist study",
    66: "controlled medieval-origin hypothesis",
    68: "methods guide",
}


def page_number(path: Path) -> int:
    return int(path.name.split("-", 1)[0])


def main() -> None:
    for path in sorted(PAGE_DIR.glob("*.wiki")):
        if page_number(path) in SKIP:
            continue
        text = path.read_text()
        prefix = ""
        if "[[Category:Glasgow Name Study]]" not in text:
            prefix += "[[Category:Glasgow Name Study]]\n"
        if "[[Space:Glasgow Name Study" not in text[:1200]:
            prefix += NAV
        if prefix:
            text = prefix + "\n" + text
        if "'''Project status:''" not in text:
            role = ROLE_BY_NUMBER.get(page_number(path), "specialist person, place, branch or record study")
            status = (
                f"<small>'''Project status:''' {role}; architecture reviewed "
                "29 August 2026. Claims remain subject to the evidence statement on this page.</small>\n"
            )
            marker = "</small>"
            position = text.find(marker)
            if position >= 0:
                position += len(marker)
                text = text[:position] + "\n\n" + status + text[position:]
            else:
                text = status + "\n" + text
        path.write_text(text)

    for path in sorted(PRE1500_DIR.glob("*.md")):
        if path.name in PRE1500_SKIP:
            continue
        text = path.read_text()
        prefix = ""
        if "[[Category:Glasgow Name Study]]" not in text:
            prefix += "[[Category:Glasgow Name Study]]\n"
        if "Space:Bearers_of_the_%27%27de_Glasgu" not in text[:1200]:
            prefix += PRE1500_NAV
        if prefix:
            text = prefix + "\n" + text
        if "'''Project status:''" not in text:
            status = (
                "<small>'''Project status:''' individual pre-1500 documentary subject; "
                "architecture reviewed 29 August 2026. This is a free-space research page, "
                "not a WikiTree person profile.</small>\n"
            )
            marker = "</small>"
            position = text.find(marker)
            if position >= 0:
                position += len(marker)
                text = text[:position] + "\n\n" + status + text[position:]
            else:
                text = status + "\n" + text
        path.write_text(text)


if __name__ == "__main__":
    main()
