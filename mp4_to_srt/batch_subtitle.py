#!/usr/bin/env python3
"""
批次 MP4 轉字幕腳本
使用 ffmpeg 提取音訊 + OpenAI Whisper 語音辨識
用法：python batch_subtitle.py [影片資料夾] [選項]
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

# ── 設定區 ──────────────────────────────────────────────
DEFAULT_LANGUAGE   = "zh"        # 語言：zh 中文 / en 英文 / auto 自動偵測
DEFAULT_MODEL      = "medium"    # 模型：tiny / base / small / medium / large
DEFAULT_OUTPUT_FMT = "srt"       # 輸出格式：srt / vtt / txt / json
DEFAULT_INPUT_DIR  = "."         # 預設掃描當前目錄
SUPPORTED_EXTS     = {".mp4", ".mkv", ".mov", ".avi", ".m4v", ".webm"}
# ────────────────────────────────────────────────────────


def check_dependencies():
    """檢查必要工具是否已安裝"""
    errors = []

    if subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0:
        errors.append("❌ ffmpeg 未安裝  →  https://ffmpeg.org/download.html")

    try:
        import whisper  # noqa: F401
    except ImportError:
        errors.append("❌ openai-whisper 未安裝  →  pip install openai-whisper")

    if errors:
        print("\n".join(errors))
        sys.exit(1)

    print("✅ 依賴檢查通過\n")


def find_videos(directory: Path) -> list[Path]:
    """遞迴尋找所有影片檔"""
    videos = []
    for ext in SUPPORTED_EXTS:
        videos.extend(directory.rglob(f"*{ext}"))
    return sorted(videos)


def extract_audio(video_path: Path, audio_path: Path) -> bool:
    """用 ffmpeg 把影片的音訊提取成 mp3"""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",                  # 不要影像
        "-acodec", "libmp3lame",
        "-ar", "16000",         # Whisper 最佳取樣率
        "-ac", "1",             # 單聲道（節省空間）
        "-q:a", "5",
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ⚠️  ffmpeg 錯誤：{result.stderr[-200:]}")
        return False
    return True


def transcribe(model, audio_path: Path, language: str, output_fmt: str,
               output_dir: Path, stem: str) -> bool:
    """用 Whisper 辨識音訊並存成字幕"""
    import whisper

    result = model.transcribe(
        str(audio_path),
        language=None if language == "auto" else language,
        verbose=False,
        fp16=False,             # CPU 環境關閉 fp16
        condition_on_previous_text=True,
    )

    # 輸出字幕
    out_path = output_dir / f"{stem}.{output_fmt}"
    writer = whisper.utils.get_writer(output_fmt, str(output_dir))
    writer(result, str(audio_path.with_stem(stem)))  # writer 會自動加副檔名

    detected = result.get("language", language)
    seg_count = len(result.get("segments", []))
    print(f"    🌐 偵測語言：{detected}  |  字幕段數：{seg_count}")
    return True


def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main():
    parser = argparse.ArgumentParser(
        description="批次將影片轉為字幕檔",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("input_dir", nargs="?", default=DEFAULT_INPUT_DIR,
                        help="影片資料夾路徑（預設：當前目錄）")
    parser.add_argument("-o", "--output-dir",
                        help="字幕輸出目錄（預設：與影片同一目錄）")
    parser.add_argument("-l", "--language", default=DEFAULT_LANGUAGE,
                        help=f"語言代碼，auto=自動偵測（預設：{DEFAULT_LANGUAGE}）")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL,
                        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
                        help=f"Whisper 模型（預設：{DEFAULT_MODEL}）")
    parser.add_argument("-f", "--format", default=DEFAULT_OUTPUT_FMT,
                        choices=["srt", "vtt", "txt", "json"],
                        help=f"輸出格式（預設：{DEFAULT_OUTPUT_FMT}）")
    parser.add_argument("--skip-existing", action="store_true",
                        help="已有字幕的影片跳過不重新產生")
    args = parser.parse_args()

    check_dependencies()
    import whisper

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.is_dir():
        print(f"❌ 找不到資料夾：{input_dir}")
        sys.exit(1)

    videos = find_videos(input_dir)
    if not videos:
        print(f"⚠️  在 {input_dir} 找不到影片檔")
        sys.exit(0)

    print(f"📂 資料夾：{input_dir}")
    print(f"🎬 找到 {len(videos)} 個影片\n")
    print(f"⚙️  載入 Whisper {args.model} 模型中…")
    model = whisper.load_model(args.model)
    print(f"✅ 模型載入完成\n{'─'*50}")

    success, skipped, failed = 0, 0, 0
    total_start = time.time()

    for idx, video in enumerate(videos, 1):
        stem = video.stem
        out_dir = Path(args.output_dir).resolve() if args.output_dir else video.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        subtitle_path = out_dir / f"{stem}.{args.format}"

        print(f"\n[{idx}/{len(videos)}] {video.name}")

        if args.skip_existing and subtitle_path.exists():
            print(f"    ⏭️  已存在 {subtitle_path.name}，跳過")
            skipped += 1
            continue

        # 暫存音訊
        tmp_audio = out_dir / f"__tmp_{stem}.mp3"
        t0 = time.time()

        try:
            print(f"    🔊 提取音訊…")
            if not extract_audio(video, tmp_audio):
                failed += 1
                continue

            print(f"    🤖 語音辨識中（{args.model} / {args.language}）…")
            if not transcribe(model, tmp_audio, args.language, args.format, out_dir, stem):
                failed += 1
                continue

            elapsed = time.time() - t0
            print(f"    ✅ 完成  →  {subtitle_path.name}  ({format_time(elapsed)})")
            success += 1

        except Exception as e:
            print(f"    ❌ 錯誤：{e}")
            failed += 1

        finally:
            if tmp_audio.exists():
                tmp_audio.unlink()

    total_elapsed = time.time() - total_start
    print(f"\n{'═'*50}")
    print(f"🏁 完成！總耗時 {format_time(total_elapsed)}")
    print(f"   ✅ 成功：{success}  ⏭️  跳過：{skipped}  ❌ 失敗：{failed}")


if __name__ == "__main__":
    main()
