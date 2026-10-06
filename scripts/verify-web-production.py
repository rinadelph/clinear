#!/usr/bin/env python3
"""Static and live checks for the production-served dashboard artifact."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_static(dist: Path) -> None:
    index = dist / "index.html"
    if not index.is_file():
        fail(f"missing {index}")
    html = index.read_text(encoding="utf-8")
    if not re.match(r"^<!doctype html>\s*<html\b", html, re.I):
        fail("index.html must begin with a standards-mode doctype and html element")
    for ref in re.findall(r"(?:src|href)=\"([^\"]+)\"", html):
        if ref.startswith("/assets/") and not (dist / ref.removeprefix("/")).is_file():
            fail(f"index references missing asset: {ref}")
    if not list((dist / "assets").glob("*.css")):
        fail("no CSS asset emitted")


def check_live(base_url: str) -> None:
    base = base_url.rstrip("/")
    def get(path: str):
        try:
            return urlopen(Request(base + path, headers={"Accept": "*/*"}), timeout=10)
        except HTTPError as exc:
            fail(f"{path} returned HTTP {exc.code}")
        except URLError as exc:
            fail(f"{path} could not connect to {base}: {exc.reason}")
    html = get("/").read().decode("utf-8")
    if not html.lower().startswith("<!doctype html>"):
        fail("live root is not standards mode")
    for ref in re.findall(r"(?:src|href)=\"(/assets/[^\"]+)\"", html):
        content_type = get(ref).headers.get_content_type()
        if ref.endswith(".js") and content_type not in {"text/javascript", "application/javascript"}:
            fail(f"{ref} served as {content_type}, expected JavaScript MIME")
        if ref.endswith(".css") and content_type != "text/css":
            fail(f"{ref} served as {content_type}, expected text/css MIME")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path)
    parser.add_argument("--url")
    args = parser.parse_args()
    dist = args.dist or Path(__file__).resolve().parents[1] / "frontend" / "dist"
    check_static(dist)
    if args.url:
        check_live(args.url)
    print("web-production-check: ok")


if __name__ == "__main__":
    main()
