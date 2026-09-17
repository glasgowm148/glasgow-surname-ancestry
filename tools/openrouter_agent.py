#!/usr/bin/env python3
"""Minimal OpenRouter chat runner for the project's AI-assisted workflows."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "stealth/union-alpha"
FREE_MODELS = {"openrouter/free", DEFAULT_MODEL}
AGENT_MODELS = {"research": DEFAULT_MODEL, "review": DEFAULT_MODEL, "mechanical": DEFAULT_MODEL}


def resolve_model(agent: str, override: str | None = None) -> str:
    if agent not in AGENT_MODELS:
        raise ValueError(f"unknown agent {agent!r}; choose from {', '.join(AGENT_MODELS)}")
    selected = override or AGENT_MODELS[agent]
    if selected not in FREE_MODELS and not selected.endswith(":free"):
        raise ValueError("model must be a free OpenRouter model (use openrouter/free or a :free variant)")
    return selected


def load_dotenv(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE entries without overwriting shell variables."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def complete(
    prompt: str,
    *,
    agent: str = "research",
    model: str | None = None,
    system: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    timeout: int = 120,
) -> dict[str, Any]:
    """Request one completion and return the decoded OpenRouter response."""
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPEN_ROUTER")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY or OPEN_ROUTER is not set")
    selected_model = resolve_model(agent, model)
    messages = ([{"role": "system", "content": system}] if system else [])
    messages.append({"role": "user", "content": prompt})
    payload = {"model": selected_model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    request = Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.environ.get("OPENROUTER_SITE_URL", "https://glasgow.phenotype.dev"),
            "X-Title": os.environ.get("OPENROUTER_APP_NAME", "Glasgow Surname Ancestry"),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"OpenRouter request failed: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", help="prompt text; otherwise read stdin")
    parser.add_argument("--agent", choices=sorted(AGENT_MODELS), default="research")
    parser.add_argument("--model", help="optional explicit OpenRouter model")
    parser.add_argument("--system", help="optional system message")
    parser.add_argument("--max-tokens", type=int, default=2048)
    args = parser.parse_args()
    prompt = args.prompt or sys.stdin.read().strip()
    if not prompt:
        parser.error("provide a prompt argument or pipe prompt text on stdin")
    try:
        result = complete(prompt, agent=args.agent, model=args.model, system=args.system, max_tokens=args.max_tokens)
    except (RuntimeError, ValueError) as error:
        parser.exit(1, f"error: {error}\n")
    choices = result.get("choices") or []
    if not choices:
        parser.exit(1, "error: OpenRouter returned no choices\n")
    print(choices[0].get("message", {}).get("content", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
