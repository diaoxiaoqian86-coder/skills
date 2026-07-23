#!/usr/bin/env bash
# 幂等安装视频内容提取所需依赖：ffmpeg、faster-whisper、（可选）yt-dlp
# 用法: bash setup.sh [--with-ytdlp]
set -uo pipefail

need_ytdlp=false
[[ "${1:-}" == "--with-ytdlp" ]] && need_ytdlp=true

ok=true

if command -v ffmpeg >/dev/null 2>&1; then
  echo "[ok] ffmpeg: $(ffmpeg -version 2>/dev/null | head -1)"
else
  echo "[..] installing ffmpeg via apt..."
  if command -v apt-get >/dev/null 2>&1; then
    (apt-get update -qq || true)
    if apt-get install -y -qq ffmpeg >/dev/null 2>&1 || sudo apt-get install -y -qq ffmpeg >/dev/null 2>&1; then
      echo "[ok] ffmpeg installed"
    else
      echo "[!!] apt install ffmpeg failed; trying static build via pip (imageio-ffmpeg)"
      if pip3 install -q imageio-ffmpeg && python3 -c "import imageio_ffmpeg, os, shutil; src = imageio_ffmpeg.get_ffmpeg_exe(); shutil.copy(src, '/usr/local/bin/ffmpeg'); os.chmod('/usr/local/bin/ffmpeg', 0o755)"; then
        echo "[ok] ffmpeg (static) installed to /usr/local/bin/ffmpeg"
      else
        echo "[FAIL] could not install ffmpeg"; ok=false
      fi
    fi
  else
    echo "[FAIL] no apt-get available; install ffmpeg manually"; ok=false
  fi
fi

if python3 -c "import faster_whisper" >/dev/null 2>&1; then
  echo "[ok] faster-whisper already installed"
else
  echo "[..] installing faster-whisper via pip..."
  if pip3 install -q faster-whisper; then
    echo "[ok] faster-whisper installed"
  else
    echo "[FAIL] pip install faster-whisper failed"; ok=false
  fi
fi

if $need_ytdlp; then
  if command -v yt-dlp >/dev/null 2>&1; then
    echo "[ok] yt-dlp already installed"
  else
    echo "[..] installing yt-dlp via pip..."
    if pip3 install -q yt-dlp; then
      echo "[ok] yt-dlp installed"
    else
      echo "[FAIL] pip install yt-dlp failed"; ok=false
    fi
  fi
fi

$ok && echo "[done] all dependencies ready" || { echo "[done] some dependencies missing, see above"; exit 1; }
