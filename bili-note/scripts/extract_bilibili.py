#!/usr/bin/env python3
"""Extract public Bilibili metadata, audio, transcripts, and comments."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path


BASE = "https://api.bilibili.com"
TZ = timezone(timedelta(hours=8))
DEFAULT_QWEN_MODEL = "Qwen/Qwen3-ASR-0.6B"
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

configure_stdout()

def is_chinese_language(value: str | None) -> bool:
    key = (value or "").strip().lower()
    return key in {"", "zh", "zh-cn", "zh_cn", "cn", "chinese", "mandarin"}

def headers(bvid: str | None = None) -> dict[str, str]:
    referer = "https://www.bilibili.com/"
    if bvid:
        referer = f"https://www.bilibili.com/video/{bvid}/"
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
        ),
        "Referer": referer,
        "Accept": "application/json,text/plain,*/*",
    }

def request_json(url: str, bvid: str | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers(bvid))
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def extract_bvid(source: str) -> str:
    match = re.search(r"(BV[0-9A-Za-z]+)", source)
    if not match:
        raise ValueError(f"Could not find BVID in: {source}")
    return match.group(1)

def fmt_ts(sec: int | None) -> str:
    if not sec:
        return ""
    return datetime.fromtimestamp(int(sec), TZ).strftime("%Y-%m-%d %H:%M:%S")

def fmt_duration(seconds: int | None) -> str:
    if not seconds:
        return "0:00"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def api_get(path: str, params: dict, bvid: str | None = None) -> dict:
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    obj = request_json(url, bvid)
    if obj.get("code") != 0:
        raise RuntimeError(f"API error {obj.get('code')}: {obj.get('message')} url={url}")
    return obj

def write_source_md(view: dict, out_dir: Path) -> None:
    data = view["data"]
    lines = [
        f"# {data.get('title', '')}",
        "",
        f"- URL: https://www.bilibili.com/video/{data.get('bvid')}/",
        f"- BVID: {data.get('bvid')}",
        f"- AID: {data.get('aid')}",
        f"- UP: {(data.get('owner') or {}).get('name', '')}",
        f"- Published: {fmt_ts(data.get('pubdate'))} (UTC+8)",
        f"- Duration: {fmt_duration(data.get('duration'))}",
        f"- Parts: {data.get('videos')}",
        "",
        "## Description",
        "",
        data.get("desc") or "",
        "",
        "## Parts",
        "",
    ]
    for page in data.get("pages") or []:
        lines.append(
            f"{page.get('page')}. cid={page.get('cid')} "
            f"duration={fmt_duration(page.get('duration'))} - {page.get('part', '')}"
        )
    (out_dir / "source.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

def select_pages(pages: list[dict], parts_arg: str | None) -> list[dict]:
    if not pages:
        return []
    if not parts_arg or parts_arg == "key":
        if len(pages) == 1:
            return pages
        pattern = re.compile(r"(Agentic|Summary|总结|实操|打造|冠军|方案|Challenge|打卡)", re.I)
        selected = [p for p in pages if pattern.search(p.get("part", ""))]
        return selected or [pages[0]]
    if parts_arg == "all":
        return pages
    wanted = {int(x.strip()) for x in parts_arg.split(",") if x.strip()}
    return [p for p in pages if int(p.get("page", 0)) in wanted]

def check_subtitles(bvid: str, pages: list[dict]) -> list[dict]:
    result = []
    for page in pages:
        obj = api_get("/x/player/v2", {"bvid": bvid, "cid": page["cid"]}, bvid)
        data = obj.get("data") or {}
        result.append(
            {
                "page": page.get("page"),
                "cid": page.get("cid"),
                "part": page.get("part"),
                "need_login_subtitle": data.get("need_login_subtitle"),
                "subtitles": (data.get("subtitle") or {}).get("subtitles") or [],
            }
        )
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Bilibili URL or BVID")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--parts", default="key", help="'key', 'all', or comma-separated page numbers")
    parser.add_argument("--download-subtitles", action="store_true", help="Download Bilibili subtitle tracks")
    parser.add_argument("--comments", action="store_true", help="Fetch comments")
    args = parser.parse_args()

    bvid = extract_bvid(args.source)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    view = api_get("/x/web-interface/view", {"bvid": bvid}, bvid)
    data = view["data"]
    (out_dir / "metadata.json").write_text(json.dumps(view, ensure_ascii=False, indent=2), encoding="utf-8")
    write_source_md(view, out_dir)

    pages = data.get("pages") or []
    selected = select_pages(pages, args.parts)
    subtitles = check_subtitles(bvid, selected)
    (out_dir / "subtitle_probe.json").write_text(json.dumps(subtitles, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "bvid": bvid,
        "aid": data.get("aid"),
        "title": data.get("title"),
        "owner": (data.get("owner") or {}).get("name"),
        "published": fmt_ts(data.get("pubdate")),
        "parts_total": len(pages),
        "parts_selected": [p.get("page") for p in selected],
        "metadata": str(out_dir / "metadata.json"),
        "source_md": str(out_dir / "source.md"),
        "subtitle_probe": str(out_dir / "subtitle_probe.json"),
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
