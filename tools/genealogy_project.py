"""Read the Glasgow project overlay without invoking any data rebuild."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from genealogy.config import ProjectConfig


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "genealogy.toml"


def load_project_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load and validate the overlay through the required toolkit dependency."""
    config = ProjectConfig.load(path).to_dict()
    required = ("project", "research", "surname", "adapters", "privacy", "paths", "exports")
    missing = [section for section in required if section not in config]
    if missing:
        raise ValueError(f"genealogy configuration is missing sections: {', '.join(missing)}")
    return config


def load_toolkit_project_config(path: Path = CONFIG_PATH) -> ProjectConfig:
    """Load the overlay through the reusable toolkit and return its model."""
    return ProjectConfig.load(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the complete declarative overlay")
    args = parser.parse_args()
    config = load_project_config()
    if args.json:
        print(json.dumps(config, indent=2, sort_keys=True))
        return
    project = config["project"]
    print(f"{project['name']} ({project['id']})")
    print("No catalogue rebuild requested or performed.")


if __name__ == "__main__":
    main()
