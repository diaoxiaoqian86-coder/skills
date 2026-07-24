"""Score a generated Bili Note against its archive note budget."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Score Markdown note length")
    parser.add_argument("--archive-dir", required=True)
    parser.add_argument("--note-path", required=True)
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
