#!/usr/bin/env python3
"""Fetch Bilibili AI subtitles through an already-open logged-in browser page."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

configure_stdout()

def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Bilibili AI subtitles")
    parser.add_argument("--target", required=True, help="CDP target id")
    parser.add_argument("--out", required=True, help="Output directory")
    args = parser.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    
    result = {
        "target": args.target,
        "out": str(out_root),
        "status": "ready"
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
