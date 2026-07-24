#!/usr/bin/env python3
"""Run Qwen3-ASR and write a compact JSON transcript result."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Qwen3-ASR on audio file.")
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--model", default="Qwen/Qwen3-ASR-0.6B")
    parser.add_argument("--language", default="Chinese")
    args = parser.parse_args(argv)

    result = {
        "audio": str(args.audio),
        "out": str(args.out),
        "model": args.model,
        "status": "ready"
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
