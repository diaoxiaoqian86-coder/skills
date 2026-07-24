#!/usr/bin/env python3
"""Insert or refresh the note budget section in a Markdown Bili Note."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

configure_stdout()

def main() -> int:
    parser = argparse.ArgumentParser(description="Update note budget section")
    parser.add_argument("--note-path", required=True)
    parser.add_argument("--archive-dir", required=True)
    args = parser.parse_args()

    result = {
        "note_path": args.note_path,
        "archive_dir": args.archive_dir,
        "status": "ready"
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
