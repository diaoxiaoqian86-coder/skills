#!/usr/bin/env python3
"""用 faster-whisper 转录音频，输出带时间戳的分段结果。

用法: python3 transcribe.py <音频文件> <输出目录> [--model small] [--language zh]

产出:
  <输出目录>/segments.json     原始分段（start/end/text/置信度相关字段）
  <输出目录>/transcript_raw.md 带时间戳的转录初稿（供后续人工整理）

进度打印到 stderr，长音频可后台运行后 tail 查看。
"""
import argparse
import json
import sys
from pathlib import Path


def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    if s >= 3600:
        return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"
    return f"{s // 60:02d}:{s % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("outdir")
    ap.add_argument("--model", default="small",
                    help="tiny/base/small/medium/large-v3 (default: small)")
    ap.add_argument("--language", default=None,
                    help="e.g. zh, en; default auto-detect")
    args = ap.parse_args()

    if not Path(args.audio).exists():
        sys.exit(f"audio not found: {args.audio}")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    from faster_whisper import WhisperModel

    print(f"loading model '{args.model}' (first run downloads it)...", file=sys.stderr)
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    segments_iter, info = model.transcribe(
        args.audio,
        language=args.language,
        vad_filter=True,
        beam_size=5,
    )
    print(f"detected language: {info.language} (p={info.language_probability:.2f}), "
          f"duration: {info.duration:.0f}s", file=sys.stderr)

    segments = []
    for seg in segments_iter:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
            "avg_logprob": round(seg.avg_logprob, 3),
            "no_speech_prob": round(seg.no_speech_prob, 3),
        })
        print(f"  [{fmt_ts(seg.start)}] {seg.text.strip()}", file=sys.stderr)

    (outdir / "segments.json").write_text(
        json.dumps({
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration_seconds": round(info.duration, 1),
            "model": args.model,
            "segments": segments,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 转录初稿（未整理）",
        "",
        f"- 语言: {info.language}（置信度 {info.language_probability:.2f}）",
        f"- 时长: {fmt_ts(info.duration)}",
        f"- 模型: faster-whisper {args.model}",
        "",
    ]
    # 低置信段落标注 (?)，提示整理时留意
    for s in segments:
        flag = " (?)" if s["avg_logprob"] < -1.0 or s["no_speech_prob"] > 0.5 else ""
        lines.append(f"[{fmt_ts(s['start'])}] {s['text']}{flag}")
    (outdir / "transcript_raw.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "segments": len(segments),
        "language": info.language,
        "outputs": [str(outdir / "segments.json"), str(outdir / "transcript_raw.md")],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
