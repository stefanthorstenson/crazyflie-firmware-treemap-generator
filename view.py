#!/usr/bin/env python3
"""Serve the treemap page locally and print the URL to open.

    view.py [data.json] [--port 8000]

Serves this folder over HTTP on localhost, which avoids the browser blocking
`treemap.html`'s local `fetch()` under `file://`. With no argument the page
loads `data.json`; pass another tree JSON (e.g. one from `example/`) to view
that instead. The file must be inside this folder. Stop with Ctrl-C.
"""
import argparse
import functools
import http.server
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("data", nargs="?", type=Path, help="tree JSON to view (default: data.json)")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    url = f"http://localhost:{args.port}/treemap.html"
    if args.data is not None:
        data = args.data.resolve()
        if not data.is_file():
            sys.exit(f"error: {args.data} not found")
        if not data.is_relative_to(ROOT):
            sys.exit(f"error: {args.data} is outside the served folder {ROOT}")
        url += f"?data={quote(data.relative_to(ROOT).as_posix())}"

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError as e:
        sys.exit(f"error: cannot listen on port {args.port}: {e.strerror} (try --port)")

    print(f"Serving {ROOT}")
    print(f"Open {url}")
    print("Stop with Ctrl-C")
    with server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print()


if __name__ == "__main__":
    main()
