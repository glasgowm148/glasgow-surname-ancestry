#!/usr/bin/env python3
"""Extract compact British Isles geometry from Natural Earth country GeoJSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


COUNTRIES = ("United Kingdom", "Ireland")


def polygons(geometry: dict) -> list:
    coordinates = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        coordinates = [coordinates]
    if geometry["type"] != "MultiPolygon" and geometry["type"] != "Polygon":
        raise ValueError(f"Unsupported geometry: {geometry['type']}")
    return [
        [
            [[round(point[0], 4), round(point[1], 4)] for point in ring]
            for ring in polygon
        ]
        for polygon in coordinates
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    features = {row["properties"]["ADMIN"]: row for row in source["features"]}
    output = {
        "source": "Natural Earth 1:50m admin 0 countries (public domain)",
        "countries": [polygons(features[name]["geometry"]) for name in COUNTRIES],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
