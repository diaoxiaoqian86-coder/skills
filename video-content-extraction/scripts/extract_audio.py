#!/usr/bin/env python3
"""从视频（或任意 ffmpeg 可读的媒体文件）提取 16kHz 单声道 WAV，供语音转录使用。

用法: python3 extract_audio.py <输入视频> <输出wav路径>

stdout 输出一行 JSON 元数据：时长、分辨率、是否有音轨等。
输入本身已是音频文件时同样适用（分辨率字段为 null）。
"""
import json
import subprocess
import sys
from pathlib import Path


def probe(path: str) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffprobe failed: {r.stderr.strip()}")
    return json.loads(r.stdout)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    if not Path(src).exists():
        sys.exit(f"input not found: {src}")

    info = probe(src)
    streams = info.get("streams", [])
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    video = [s for s in streams if s.get("codec_type") == "video"]
    duration = float(info.get("format", {}).get("duration", 0) or 0)

    meta = {
        "duration_seconds": round(duration, 1),
        "duration_hms": f"{int(duration // 3600)}:{int(duration % 3600 // 60):02d}:{int(duration % 60):02d}",
        "has_audio": bool(audio),
        "audio_codec": audio[0].get("codec_name") if audio else None,
        "video_resolution": (f"{video[0].get('width')}x{video[0].get('height')}"
                             if video and video[0].get("width") else None),
        "format": info.get("format", {}).get("format_name"),
    }

    if not audio:
        meta["error"] = "no audio stream - transcription not possible; consider frame extraction"
        print(json.dumps(meta, ensure_ascii=False))
        sys.exit(2)

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", src,
         "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", dst],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg failed: {r.stderr.strip()}")

    meta["audio_wav"] = dst
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
