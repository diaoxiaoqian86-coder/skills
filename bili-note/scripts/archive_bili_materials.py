"""Archive Bilibili extraction outputs for long-term knowledge-base use."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


configure_stdout()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive Bilibili materials")
    parser.add_argument("--extract-dir", required=True, help="Extraction output directory")
    parser.add_argument("--archive-dir", required=True, help="Permanent archive directory")
    args = parser.parse_args()

    extract_dir = Path(args.extract_dir)
    archive_dir = Path(args.archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "archive_dir": str(archive_dir),
        "status": "initialized"
    }
    write_json(archive_dir / "metadata" / "archive_info.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
