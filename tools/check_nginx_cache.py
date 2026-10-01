#!/usr/bin/env python3
"""Verify the maintained cache includes using an isolated local nginx process."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REVALIDATE = "public, max-age=0, must-revalidate"
IMMUTABLE = "public, max-age=31536000, immutable"


def check(binary: str) -> None:
    with tempfile.TemporaryDirectory(prefix="glasgow-nginx-cache-") as directory:
        prefix = Path(directory)
        site = prefix / "www"
        fixtures = {
            "index.html": "A public page",
            "assets/site.js": "window.example = 1;",
            "data/index.json": "[]",
            "data/catalogue-details/details-0123456789abcdef.json": "[]",
            "assets/research/fragments/person-0123456789abcdef.html": "<details>Evidence</details>",
            "assets/research/fragments/person-technical.html": "<details>Evidence</details>",
        }
        for name, content in fixtures.items():
            path = site / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        configuration = prefix / "nginx.conf"
        configuration.write_text(f'''pid "{prefix}/nginx.pid";
error_log "{prefix}/error.log";
events {{}}
http {{
    access_log off;
    include "{ROOT}/deploy/nginx/cache-map.conf";
    server {{
        listen 127.0.0.1:{port};
        root "{site}";
        include "{ROOT}/deploy/nginx/cache-headers.conf";
        add_header X-Content-Type-Options nosniff always;
    }}
}}
''')
        command = [binary, "-p", str(prefix), "-c", str(configuration)]
        subprocess.run([*command, "-t"], check=True, capture_output=True)
        subprocess.run(command, check=True, capture_output=True)
        try:
            cases = [
                ("/", 200, REVALIDATE),
                ("/index.html?v=0123456789", 200, REVALIDATE),
                ("/assets/site.js", 200, REVALIDATE),
                ("/assets/site.js?v=0123456789", 200, IMMUTABLE),
                ("/assets/site.js?v=invalid", 200, REVALIDATE),
                ("/data/index.json", 200, REVALIDATE),
                ("/data/index.json?x=1&v=0123456789", 200, IMMUTABLE),
                ("/data/catalogue-details/details-0123456789abcdef.json", 200, IMMUTABLE),
                ("/assets/research/fragments/person-0123456789abcdef.html", 200, IMMUTABLE),
                ("/assets/research/fragments/person-technical.html", 200, REVALIDATE),
                ("/assets/missing.js?v=0123456789", 404, "no-store"),
            ]
            for route, expected_status, expected_cache in cases:
                try:
                    response = urlopen(f"http://127.0.0.1:{port}{route}", timeout=5)
                except HTTPError as error:
                    response = error
                with response:
                    assert response.status == expected_status, (route, response.status)
                    assert response.headers.get_all("Cache-Control") == [expected_cache], (
                        route, response.headers.get_all("Cache-Control"))
                    assert response.headers.get("X-Content-Type-Options") == "nosniff"
            url = f"http://127.0.0.1:{port}/assets/site.js?v=0123456789"
            with urlopen(url, timeout=5) as response:
                etag = response.headers["ETag"]
            try:
                urlopen(Request(url, headers={"If-None-Match": etag}), timeout=5)
                raise AssertionError("Conditional request did not return 304")
            except HTTPError as response:
                assert response.code == 304
                assert response.headers.get_all("Cache-Control") == [IMMUTABLE]
            print(f"PASS: {len(cases)} cache/status cases and conditional 304; nginx config valid")
        finally:
            subprocess.run([*command, "-s", "quit"], check=True, capture_output=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nginx", default=shutil.which("nginx"))
    args = parser.parse_args()
    if not args.nginx:
        parser.error("nginx is required to validate the host configuration")
    check(args.nginx)


if __name__ == "__main__":
    main()
