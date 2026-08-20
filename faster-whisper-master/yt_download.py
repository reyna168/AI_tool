"""
YouTube 音訊下載器
用法：python yt_download.py <YouTube網址> [--output <輸出目錄>]

依賴：pip install yt-dlp
需要系統安裝 ffmpeg（用於轉檔為 mp3）
"""
import argparse
import os
import sys

from yt_dlp import YoutubeDL


def normalize_url(url: str) -> str:
    url = url.strip()
    if "](" in url and url.startswith("["):
        url = url[url.find("](") + 2:]
        if url.endswith(")"):
            url = url[:-1]
    return url.strip().strip('"').strip("'")


def download_audio(url: str, output_dir: str = "downloads", audio_format: str = "mp3", quality: str = "192"):
    os.makedirs(output_dir, exist_ok=True)
    url = normalize_url(url)

    if not ("youtube.com/" in url or "youtu.be/" in url):
        print(f"Error: Not a valid YouTube URL: {url}")
        return None

    outtmpl = os.path.join(output_dir, "%(title).180s [%(id)s].%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "continuedl": False,
        "overwrites": True,
        "retries": 10,
        "fragment_retries": 10,
        "js_runtimes": {"deno": {}},
        "remote_components": ["ejs:github"],
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        },
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_format,
            "preferredquality": quality,
        }],
    }

    print(f"Downloading: {url}")
    print(f"Output dir:  {os.path.abspath(output_dir)}")
    print(f"Format:      {audio_format} @ {quality}kbps\n")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")
            vid = info.get("id", "")

            prepared = ydl.prepare_filename(info)
            base = os.path.splitext(prepared)[0]
            file_path = base + f".{audio_format}"

            if not os.path.exists(file_path):
                import glob
                candidates = glob.glob(os.path.join(output_dir, f"*[{vid}]*.{audio_format}"))
                if candidates:
                    file_path = candidates[0]
                else:
                    print("Warning: MP3 file not found after conversion. Check ffmpeg.")
                    return None

            print(f"\nDone! Saved to:\n  {file_path}")
            return file_path

    except Exception as e:
        print(f"\nDownload failed: {e}")
        if "403" in str(e) or "Forbidden" in str(e):
            print("\nTip: Update yt-dlp and ensure Deno is installed:")
            print('  pip install -U "yt-dlp[default]"')
        return None


def main():
    parser = argparse.ArgumentParser(description="Download YouTube audio as MP3")
    parser.add_argument("url", help="YouTube URL to download")
    parser.add_argument("-o", "--output", default="downloads", help="Output directory (default: downloads)")
    parser.add_argument("-f", "--format", default="mp3", choices=["mp3", "wav", "m4a", "flac", "ogg"], help="Audio format (default: mp3)")
    parser.add_argument("-q", "--quality", default="192", help="Audio quality in kbps (default: 192)")

    args = parser.parse_args()
    result = download_audio(args.url, args.output, args.format, args.quality)

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
