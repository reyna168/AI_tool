"""
transcribe_taiwanese.py
========================
與 transcribe_whisper.py（原本的一般用途 Whisper 轉錄程式）功能相同，
差別在於固定使用 adi-gov-tw/Taiwan-Tongues-ASR-CE-v2.0 模型，
支援國語、台語（閩南語）、客語、英語、印尼語辨識，
且對國台語夾雜的內容有較好的支援（一般 Whisper 模型不支援台語）。

需求套件與 transcribe_whisper.py 相同（faster-whisper / yt-dlp / ffmpeg），
第一次執行時會自動從 Hugging Face 下載模型權重。
"""

import os
import sys
import time
import glob
import shutil
import subprocess
from faster_whisper import WhisperModel
from tqdm import tqdm
from yt_dlp import YoutubeDL

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ============ 可調整參數 ============
CHUNK_MINUTES = 15            # 每段切割長度（分鐘）
SPLIT_THRESHOLD_MINUTES = 20  # 音訊總長超過這個門檻才會切割，短檔案直接整檔轉錄
TEMP_DIR = "temp_chunks"      # 下載與切割的暫存資料夾
KEEP_DOWNLOAD = False         # 轉錄完成後是否保留下載的音訊檔
KEEP_CHUNKS = False           # 轉錄完成後是否保留切割檔案（True 方便除錯 / 重跑）
# =====================================


def format_time_srt(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def format_time_txt(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def check_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            print(f"❌ 找不到 {tool}，請先安裝 ffmpeg 並確認已加入系統 PATH。")
            sys.exit(1)


def normalize_youtube_url(url: str) -> str:
    """清理使用者可能貼上的 Markdown 連結，避免 yt-dlp 收到 [文字](網址)。"""
    url = url.strip()

    # [https://www.youtube.com/watch?v=xxx](https://www.youtube.com/watch?v=xxx)
    if "](" in url and url.startswith("["):
        url = url[url.find("](") + 2:]
        if url.endswith(")"):
            url = url[:-1]

    # 去掉外層引號
    url = url.strip().strip('"').strip("'")

    return url


def download_youtube_audio(url: str, output_dir: str):
    """用 yt-dlp 下載 YouTube 音訊。

    YouTube 近期增加 JavaScript challenge，因此除了 yt-dlp 本身，
    建議搭配 yt-dlp[default] + Deno + yt-dlp-ejs。
    """
    os.makedirs(output_dir, exist_ok=True)

    url = normalize_youtube_url(url)

    if not ("youtube.com/" in url or "youtu.be/" in url):
        raise ValueError(f"看起來不是有效的 YouTube 網址：{url}")

    # Windows 檔名安全處理交給 %(title)s/%(id)s，避免特殊字元造成問題
    outtmpl = os.path.join(output_dir, "%(title).180s [%(id)s].%(ext)s")

    audio_format = "mp3"
    quality = "192"

    ydl_opts = {
        # 不指定單一 m4a，讓 yt-dlp 自己選可用的最佳音訊格式。
        # 下載後再由 FFmpeg 轉成指定格式。
        "format": "bestaudio/best",

        "outtmpl": outtmpl,
        "noplaylist": True,

        # YouTube 403 時，不要使用舊下載檔繼續下載
        "continuedl": False,
        "overwrites": True,

        # 重試下載；403 若是 URL/token 問題，yt-dlp 會重新取得媒體資訊
        "retries": 10,
        "fragment_retries": 10,

        # 使用目前 YouTube 所需的 JS challenge solver
        # 若本機已安裝 Deno，yt-dlp 會使用它。
        "js_runtimes": {
            "deno": {}
        },

        # 若 PyPI 安裝的 yt-dlp 沒有內含 EJS，可從 GitHub 取得。
        # 若已安裝 yt-dlp[default]，通常不需要這一行；
        # 保留可增加新版環境的相容性。
        "remote_components": ["ejs:github"],

        # 模擬一般瀏覽器的基本 HTTP header
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

    print("正在下載影片音訊，請稍候...")
    print(f"輸出目錄：  {os.path.abspath(output_dir)}")
    print(f"格式：      {audio_format} @ {quality}kbps")
    print("正在使用 yt-dlp + EJS/Deno 處理 YouTube 驗證...")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get("title", "youtube_video")
            video_id = info.get("id", "")

            # prepare_filename 是原始下載檔名；postprocessor 完成後副檔名會變指定格式
            prepared = ydl.prepare_filename(info)
            base = os.path.splitext(prepared)[0]
            file_path = base + f".{audio_format}"

            if not os.path.exists(file_path):
                # 某些標題/平台情況下，直接搜尋符合 ID 的檔案，找不到再退而求其次搜尋最新檔案
                candidates = glob.glob(os.path.join(output_dir, f"*[{video_id}]*.{audio_format}"))
                if not candidates:
                    candidates = glob.glob(os.path.join(output_dir, f"*.{audio_format}"))
                if candidates:
                    file_path = max(candidates, key=os.path.getmtime)
                else:
                    raise RuntimeError(
                        f"yt-dlp 已完成資訊取得，但找不到 {audio_format.upper()} 檔案。\n"
                        f"影片 ID: {video_id}\n"
                        f"請檢查 FFmpeg 是否正常。"
                    )

            print(f"\n✅ 下載完成: {file_path}")
            return file_path, video_title

    except Exception as e:
        msg = str(e)

        if "403" in msg or "Forbidden" in msg:
            raise RuntimeError(
                "YouTube 回傳 HTTP 403 Forbidden。\n"
                "請先在目前的虛擬環境執行：\n"
                '  python -m pip install -U "yt-dlp[default]"\n'
                "並確認 Deno 已安裝，再重新執行程式。\n"
                "如果仍然 403，請執行：\n"
                "  yt-dlp -v <YouTube網址>\n"
                "查看詳細原因。"
            ) from e

        raise

def download_direct_audio(url: str, output_dir: str):
    """下載直接的音訊檔案連結（支援 MP3、M4A、WAV 等）"""
    import requests
    import re
    os.makedirs(output_dir, exist_ok=True)

    print("正在下載音訊檔案，請稍候...")

    try:
        head_resp = requests.head(url, allow_redirects=True, timeout=10)
        content_disp = head_resp.headers.get("Content-Disposition", "")
        content_type = head_resp.headers.get("Content-Type", "")

        filename = None
        match = re.search(r'filename[*]?=["\']?([^"\';\s]+)', content_disp)
        if match:
            filename = match.group(1)

        if not filename:
            path_part = url.split("?")[0].split("#")[0]
            filename = path_part.split("/")[-1]

        if not filename or "." not in filename:
            ext_map = {
                "audio/mpeg": ".mp3",
                "audio/mp4": ".m4a",
                "audio/x-wav": ".wav",
                "audio/wav": ".wav",
                "audio/flac": ".flac",
                "audio/ogg": ".ogg",
            }
            ext = ext_map.get(content_type.split(";")[0].strip(), ".mp3")
            filename = f"audio_file{ext}"

        filepath = os.path.join(output_dir, filename)

        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()

        total = int(resp.headers.get("Content-Length", 0))
        with open(filepath, "wb") as f:
            downloaded = 0
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r下載進度: {pct}% ({downloaded // 1024}KB / {total // 1024}KB)", end="", flush=True)
        print()

        if os.path.getsize(filepath) == 0:
            raise RuntimeError("下載的檔案大小為 0，請檢查網址是否正確。")

        print(f"✅ 下載完成: {filepath}")
        return filepath, filename

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"下載失敗: {e}\n請確認網址是否正確且可公開存取。") from e


def get_duration(file_path: str) -> float:
    """用 ffprobe 取得音訊檔案長度（秒）"""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", file_path]
    out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    return float(out)


def split_audio(input_file: str, chunk_minutes: int, output_dir: str):
    """
    用 FFmpeg 將長音訊切成多段。

    注意：
    1. 不再使用原始檔名當輸出 pattern，避免 Windows / Unicode / [] 檔名造成 glob 找不到。
    2. 不使用 -c copy，改用 MP3 重新編碼，對 MP3 長音檔的切割相容性較高。
    3. 固定輸出 chunk_000.mp3、chunk_001.mp3...，方便後續穩定尋找。
    """
    os.makedirs(output_dir, exist_ok=True)

    # 清除這一次切割可能留下的舊分段，避免重跑時混入舊檔。
    for old_chunk in glob.glob(os.path.join(output_dir, "chunk_*.mp3")):
        try:
            os.remove(old_chunk)
        except OSError:
            pass

    segment_time = chunk_minutes * 60
    pattern = os.path.join(output_dir, "chunk_%03d.mp3")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-map", "0:a:0",
        "-vn",
        "-f", "segment",
        "-segment_time", str(segment_time),
        "-reset_timestamps", "1",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        pattern,
    ]

    print("正在使用 FFmpeg 切割音訊...")
    print("FFmpeg 指令：")
    print(" ".join(f'"{x}"' if " " in x else x for x in cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        print(f"ffmpeg 錯誤：\n{result.stderr}")
        raise RuntimeError("切割失敗，請查看上方 ffmpeg 錯誤訊息。")

    chunk_files = sorted(
        glob.glob(os.path.join(output_dir, "chunk_*.mp3"))
    )

    if not chunk_files:
        print("⚠️ FFmpeg 回傳成功，但沒有找到分段檔。")
        print(f"切割目錄：{os.path.abspath(output_dir)}")
        if result.stdout:
            print(f"ffmpeg stdout：\n{result.stdout}")
        if result.stderr:
            print(f"ffmpeg stderr：\n{result.stderr}")
        raise RuntimeError(
            "切割失敗，未產生任何分段檔案。"
            "請確認輸入音訊可正常被 FFmpeg 解碼。"
        )

    print(f"切割完成，共 {len(chunk_files)} 個分段。")
    for i, chunk in enumerate(chunk_files, 1):
        try:
            duration = get_duration(chunk)
            print(f"  [{i}] {os.path.basename(chunk)} ({format_time_txt(duration)})")
        except Exception:
            print(f"  [{i}] {os.path.basename(chunk)}")

    return chunk_files


def choose_local_file():
    """掃描當前目錄下的音訊檔案並讓使用者選擇，回傳檔案路徑"""
    supported_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma')
    audio_files = [f for f in os.listdir('.') if f.lower().endswith(supported_extensions)]

    if not audio_files:
        print("❌ 未在當前目錄下找到支援的音訊檔案！")
        print(f"支援的格式有: {', '.join(supported_extensions)}")
        return None

    print("=== 找到以下音訊檔案 ===")
    for i, file_name in enumerate(audio_files):
        print(f"[{i + 1}] {file_name}")
    print("========================")

    if len(audio_files) == 1:
        selected_file = audio_files[0]
        print(f"自動選擇唯一的音訊檔案: {selected_file}")
    else:
        try:
            choice = input(f"請輸入要轉檔的檔案編號 (1-{len(audio_files)}) [預設 1]: ").strip()
            if not choice:
                selected_file = audio_files[0]
            else:
                idx = int(choice) - 1
                if 0 <= idx < len(audio_files):
                    selected_file = audio_files[idx]
                else:
                    print("輸入錯誤，將使用第一個檔案。")
                    selected_file = audio_files[0]
        except Exception:
            selected_file = audio_files[0]
    return selected_file


# Taiwan-Tongues-ASR-CE-v2.0 是數位發展部數位產業署（台灣大哥大執行）釋出的開源模型，
# 以 openai/whisper-large-v2 微調而成，支援國語、台語（閩南語）、客語、英語、印尼語，
# 並提供「本地多語混合語音辨識」（國台語夾雜也可處理）。
# CTranslate2 版本可直接被 faster-whisper 載入，第一次執行會自動從 Hugging Face 下載。
TAIWAN_MODEL_REPO = "adi-gov-tw/Taiwan-Tongues-ASR-CE-v2.0"

# 模型支援的語言代碼（依官方文件）：
#   zh = 國語（華語） / nan = 台語（閩南語） / hak = 客語 / en = 英語 / id = 印尼語
LANGUAGE_CHOICES = [
    ("zh", "國語（華語）"),
    ("nan", "台語（閩南語）"),
    ("hak", "客語"),
    ("en", "英語"),
    ("id", "印尼語"),
]


def choose_model():
    """固定使用 Taiwan-Tongues-ASR-CE-v2.0 模型（支援台語／國語／客語混合辨識）"""
    print("\n=== 使用模型 ===")
    print(f"本程式固定使用: {TAIWAN_MODEL_REPO}")
    print("（支援國語、台語、客語、英語、印尼語，並可處理國台語夾雜的內容）")
    return TAIWAN_MODEL_REPO


def choose_language():
    """選擇音檔主要語言，回傳語言代碼字串"""
    print("\n=== 請選擇音檔的主要語言 ===")
    print("提醒：若音檔是國台語夾雜，Whisper 系模型只會在開頭偵測一次語言，")
    print("      無法逐句自動切換，建議選擇音檔中「佔比較多」的語言，")
    print("      轉錄後另一種語言的部分可能需要人工校對。")
    for i, (code, label) in enumerate(LANGUAGE_CHOICES):
        default_tag = " (預設)" if code == "zh" else ""
        print(f"[{i + 1}] {label} ({code}){default_tag}")

    try:
        choice = input(f"請輸入編號 (1-{len(LANGUAGE_CHOICES)}) [預設 1 (國語)]: ").strip()
        if not choice:
            return LANGUAGE_CHOICES[0][0]
        idx = int(choice) - 1
        if 0 <= idx < len(LANGUAGE_CHOICES):
            return LANGUAGE_CHOICES[idx][0]
        return LANGUAGE_CHOICES[0][0]
    except Exception:
        return LANGUAGE_CHOICES[0][0]


# 各語言對應的 initial_prompt，能提高模型輸出對應文字系統的機率
LANGUAGE_PROMPTS = {
    "zh": "以下是繁體中文的對話。",
    "nan": "以下是台語（閩南語）的對話。",
    "hak": "以下是客語的對話。",
    "en": "The following is a conversation in English.",
    "id": "Berikut adalah percakapan dalam bahasa Indonesia.",
}


def transcribe_to_files(model, audio_file: str, base_name: str, language: str = "zh"):
    """轉錄音訊檔案並輸出 _transcript.txt / _clean.txt / .srt，需要 ffmpeg 切割長影片"""
    total_duration = get_duration(audio_file)
    print(f"\n音訊總長度: {format_time_txt(total_duration)}")

    chunk_dir = os.path.join(TEMP_DIR, os.path.splitext(os.path.basename(audio_file))[0])
    need_split = total_duration > SPLIT_THRESHOLD_MINUTES * 60

    if need_split:
        print(f"檔案長度超過 {SPLIT_THRESHOLD_MINUTES} 分鐘，將切割成每段 {CHUNK_MINUTES} 分鐘後逐段轉錄...")
        print(f"切割暫存目錄: {os.path.abspath(chunk_dir)}")
        chunk_files = split_audio(audio_file, CHUNK_MINUTES, chunk_dir)
        print(f"已切割成 {len(chunk_files)} 段。")
    else:
        chunk_files = [audio_file]

    initial_prompt = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["zh"])

    transcripts = []
    pbar = tqdm(total=round(total_duration), unit="sec", desc="整體轉錄進度")

    offset = 0.0
    for chunk_idx, chunk_file in enumerate(chunk_files, 1):
        print(f"\n[{chunk_idx}/{len(chunk_files)}] 轉錄中: {os.path.basename(chunk_file)}")
        segments, info = model.transcribe(
            chunk_file,
            beam_size=5,
            language=language,
            initial_prompt=initial_prompt,
        )

        if chunk_idx == 1:
            print(f"偵測到音訊語言: '{info.language}'，信心度: {info.language_probability:.2f}")

        last_end_in_chunk = 0.0
        for segment in segments:
            # 將本段內的相對時間，校正為在整個音訊檔案中的絕對時間
            shifted_start = segment.start + offset
            shifted_end = segment.end + offset
            transcripts.append((shifted_start, shifted_end, segment.text.strip()))

            step = round(segment.end - last_end_in_chunk)
            if step > 0:
                pbar.update(min(step, pbar.total - pbar.n))
            last_end_in_chunk = segment.end

        # 下一段的時間位移，用該切割檔的實際長度累加（比用固定 CHUNK_MINUTES 假設更準確）
        offset += get_duration(chunk_file)

    pbar.n = pbar.total
    pbar.refresh()
    pbar.close()

    print("\n轉錄完成！正在儲存檔案...")

    txt_time_file = f"{base_name}_transcript.txt"
    txt_clean_file = f"{base_name}_clean.txt"
    srt_file = f"{base_name}.srt"

    # 1. 儲存含時間戳記版本
    with open(txt_time_file, "w", encoding="utf-8") as f:
        for start, end, text in transcripts:
            f.write(f"[{format_time_txt(start)} -> {format_time_txt(end)}] {text}\n")

    # 2. 儲存純文字乾淨版
    with open(txt_clean_file, "w", encoding="utf-8") as f:
        for _, _, text in transcripts:
            f.write(f"{text}\n")

    # 3. 儲存 SRT 字幕檔
    with open(srt_file, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(transcripts, 1):
            f.write(f"{i}\n")
            f.write(f"{format_time_srt(start)} --> {format_time_srt(end)}\n")
            f.write(f"{text}\n\n")

    # 4. 清理切割暫存檔
    if need_split and not KEEP_CHUNKS:
        shutil.rmtree(chunk_dir, ignore_errors=True)
        print(f"已清除暫存切割檔案: {chunk_dir}")

    print("✅ 轉錄成功！已生成以下檔案：")
    print(f"1. 時間戳記版：{os.path.abspath(txt_time_file)}")
    print(f"2. 純文字乾淨版：{os.path.abspath(txt_clean_file)}")
    print(f"3. SRT 字幕檔：{os.path.abspath(srt_file)}")


def check_ytdlp():
    """檢查 yt-dlp 版本與 EJS 套件是否可用。"""
    try:
        import yt_dlp
        print(f"yt-dlp 版本: {yt_dlp.version.__version__}")
    except Exception as e:
        print(f"⚠️ 無法讀取 yt-dlp 版本: {e}")

    try:
        import yt_dlp_ejs  # noqa: F401
        print("yt-dlp-ejs: OK")
    except ImportError:
        print("⚠️ 找不到 yt-dlp-ejs。")
        print('請執行：python -m pip install -U "yt-dlp[default]"')



def main():
    check_ffmpeg()
    check_ytdlp()

    # 0. 選擇來源：YouTube 網址、音訊連結 或 本機檔案
    print("=== 請選擇轉錄來源 ===")
    print("[1] 貼上 YouTube 網址")
    print("[2] 貼上音訊檔案連結 (MP3/M4A/WAV 等)")
    print("[3] 使用本機音訊檔")
    source_choice = input("請輸入編號 [預設 1]: ").strip()

    download_path = None
    if source_choice == "3":
        selected_file = choose_local_file()
        if selected_file is None:
            return
        base_name, _ = os.path.splitext(selected_file)
    else:
        url = input("請貼上網址: ").strip()
        if not url:
            print("❌ 未輸入網址。")
            return

        is_youtube = "youtube.com/" in url or "youtu.be/" in url

        if source_choice == "1" and not is_youtube:
            print("⚠️ 輸入的網址不是 YouTube 連結，將嘗試直接下載音訊檔案。")

        try:
            os.makedirs(TEMP_DIR, exist_ok=True)
            if is_youtube:
                download_path, video_title = download_youtube_audio(url, TEMP_DIR)
            else:
                download_path, video_title = download_direct_audio(url, TEMP_DIR)
        except Exception as e:
            print(f"❌ 下載失敗: {e}")
            return
        selected_file = download_path
        base_name = video_title
        base_name = "".join(c for c in base_name if c not in '\\/:*?"<>|').strip()

    # 固定使用 Taiwan-Tongues-ASR-CE 模型（支援台語／國語／客語混合辨識）
    model_repo = choose_model()
    language = choose_language()

    device = "cpu"
    compute_type = "int8"
    print(f"\n使用 CPU 執行 ({compute_type})。如需 GPU 加速，將 device 改為 'cuda'、compute_type 改為 'float16'。")

    print(f"\n正在載入 {model_repo} 模型，第一次載入會自動從 Hugging Face 下載（模型較大，請耐心等候）...")
    start_time = time.time()
    try:
        model = WhisperModel(model_repo, device=device, compute_type=compute_type)
    except Exception as e:
        print(f"⚠️ 模型載入失敗 ({e})，將嘗試使用 CPU int8 執行...")
        model = WhisperModel(model_repo, device="cpu", compute_type="int8")

    print(f"模型載入完成！耗時 {time.time() - start_time:.2f} 秒。")

    print(f"\n開始轉錄: {os.path.basename(selected_file)}")
    try:
        transcribe_to_files(model, selected_file, base_name, language=language)
    except Exception as e:
        print(f"❌ 轉錄失敗: {e}")
    finally:
        if download_path and not KEEP_DOWNLOAD:
            try:
                os.remove(download_path)
                print(f"已清除下載的音訊檔: {download_path}")
            except OSError:
                pass


if __name__ == "__main__":
    main()