#!/usr/bin/env python3
"""Rebuild the self-contained atlas from an existing model. Python standard library only.

This does not refresh the catalogue or modify model.json. In the original catalogue
repository, use the existing build.py for canonical data refreshes instead.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PUBLIC_DIR = ROOT / "www" / "onetree" / "glasgow-one-tree-polished-3"


def validate(model: dict[str, Any]) -> dict[str, int]:
    rows = model.get("people")
    if not isinstance(rows, list) or not rows:
        raise ValueError("model.people must be a non-empty array.")
    people: dict[str, dict[str, Any]] = {}
    for person in rows:
        if not isinstance(person, dict) or not isinstance(person.get("id"), str):
            raise ValueError("Every person needs a string ID.")
        ident = person["id"]
        if ident in people:
            raise ValueError(f"Duplicate ID: {ident}")
        people[ident] = person
    root = model.get("root")
    if root not in people:
        raise ValueError("The collection root is missing.")
    for ident, person in people.items():
        if ident == root:
            continue
        edge = person.get("edge", {})
        parent = edge.get("parent")
        if parent not in people:
            raise ValueError(f"Missing display attachment: {ident} -> {parent}")
        if edge.get("type") == "recorded" and not any(
            relative.get("id") == parent and relative.get("role") == edge.get("role")
            for relative in person.get("parents", [])
        ):
            raise ValueError(f"Display edge is not a structured parent reference: {ident}")
        if person.get("kind") == "person" and not re.fullmatch(
            r"[a-z0-9_-]+", person.get("catalogueId", "")
        ):
            raise ValueError(f"Invalid catalogue ID: {ident}")
    done = {root}
    for ident in people:
        path: set[str] = set()
        node = ident
        while node not in done:
            if node in path:
                raise ValueError(f"Cycle in display attachments: {node}")
            path.add(node)
            node = people[node]["edge"]["parent"]
        done.update(path)
    real = [p for p in people.values() if p.get("kind") == "person"]
    return {
        "profiles": len(real),
        "recorded_display_parent_links": sum(
            p.get("edge", {}).get("type") == "recorded" for p in real
        ),
        "structured_parent_references": sum(len(p.get("parents", [])) for p in real),
        "spouse_mentions": sum(len(p.get("partners", [])) for p in real),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=PUBLIC_DIR / "model.json")
    parser.add_argument("--template", type=Path, default=PUBLIC_DIR / "template.html")
    parser.add_argument("--output", type=Path, default=PUBLIC_DIR / "index.html")
    args = parser.parse_args()
    try:
        if args.output.resolve() in {args.model.resolve(), args.template.resolve()}:
            raise ValueError("Output must not overwrite the model or template.")
        model = json.loads(args.model.read_text(encoding="utf-8"))
        checks = validate(model)
        template = args.template.read_text(encoding="utf-8")
        if template.count("__MODEL__") != 1:
            raise ValueError("Template must contain exactly one __MODEL__ placeholder.")
        payload = json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace(
            "<", r"\u003c"
        )
        html = template.replace("__MODEL__", payload)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_name(args.output.name + ".tmp")
        temporary.write_text(html, encoding="utf-8")
        temporary.replace(args.output)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Build failed: {exc}\n")
    print(f"Built {args.output} with {checks['profiles']:,} profiles. Source model unchanged.")


if __name__ == "__main__":
    main()
