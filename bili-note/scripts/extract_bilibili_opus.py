#!/usr/bin/env python3
"""Extract Bilibili opus/article pages into Markdown, JSONL evidence, and images."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


TZ = timezone(timedelta(hours=8))
SCRIPT_DIR = Path(__file__).resolve().parent


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


configure_stdout()


def headers(opus_id: str | None = None) -> dict[str, str]:
    referer = "https://www.bilibili.com/"
    if opus_id:
        referer = f"https://www.bilibili.com/opus/{opus_id}"
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
        ),
        "Referer": referer,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def normalize_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http://i") and ".hdslb.com/" in url:
        return "https://" + url[len("http://") :]
    return url


def extract_opus_id(source: str) -> str:
    match = re.search(r"(?:opus|dynamic)/(\d+)", source)
    if not match:
        match = re.search(r"\b(\d{12,})\b", source)
    if not match:
        raise ValueError(f"Could not find Bilibili opus id in: {source}")
    return match.group(1)


def clean_filename(value: str, limit: int = 90) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value).strip(" ._")
    return (value[:limit] or "untitled").strip(" ._")


def request_text(url: str, opus_id: str) -> str:
    req = urllib.request.Request(url, headers=headers(opus_id))
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_json_after_marker(text: str, marker: str) -> dict[str, Any]:
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"Could not find {marker!r} in Bilibili opus page")
    start += len(marker)
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] != "{":
        raise RuntimeError("Initial state marker was found but JSON object did not follow")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])
    raise RuntimeError("Could not locate the end of Bilibili opus initial state JSON")


def fetch_initial_state(source: str) -> dict[str, Any]:
    opus_id = extract_opus_id(source)
    url = f"https://www.bilibili.com/opus/{opus_id}"
    html = request_text(url, opus_id)
    return extract_json_after_marker(html, "window.__INITIAL_STATE__=")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Bilibili opus URL or opus id")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--download-images", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--comments", action="store_true", help="Fetch opus comments")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()

    state = fetch_initial_state(args.source)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    (out_dir / "opus_raw.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"source": args.source, "status": "extracted"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
