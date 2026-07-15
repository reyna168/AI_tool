import os
import sys
import time
import glob
import shutil
import subprocess
from faster_whisper import WhisperModel
from tqdm import tqdm

# ============ 可調整參數 ============
CHUNK_MINUTES = 15          # 每段切割長度（分鐘）
SPLIT_THRESHOLD_MINUTES = 20  # 音訊總長超過這個門檻才會切割，短檔案直接整檔轉錄
TEMP_DIR = "temp_chunks"    # 切割後暫存資料夾
KEEP_CHUNKS = False         # 轉錄完成後是否保留切割檔案（True 方便除錯 / 重跑）
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


def get_duration(file_path: str) -> float:
    """用 ffprobe 取得音訊檔案長度（秒）"""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", file_path]
    out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    return float(out)


def split_audio(input_file: str, chunk_minutes: int, output_dir: str):
    """用 ffmpeg segment muxer 切割音訊（-c copy，不重新編碼，速度快、不吃記憶體）"""
    os.makedirs(output_dir, exist_ok=True)
    base, ext = os.path.splitext(os.path.basename(input_file))
    pattern = os.path.join(output_dir, f"{base}_%03d{ext}")
    segment_time = chunk_minutes * 60

    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-f", "segment", "-segment_time", str(segment_time),
        "-c", "copy", "-reset_timestamps", "1",
        pattern,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    chunk_files = sorted(glob.glob(os.path.join(output_dir, f"{base}_*{ext}")))
    if not chunk_files:
        raise RuntimeError("切割失敗，未產生任何分段檔案，請確認 ffmpeg 是否正常運作。")
    return chunk_files


def main():
    check_ffmpeg()

    # 1. 掃描當前目錄下的音訊檔案
    supported_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma')
    audio_files = [f for f in os.listdir('.') if f.lower().endswith(supported_extensions)]

    if not audio_files:
        print("❌ 未在當前目錄下找到支援的音訊檔案！")
        print(f"支援的格式有: {', '.join(supported_extensions)}")
        return

    print("=== 找到以下音訊檔案 ===")
    for i, file_name in enumerate(audio_files):
        print(f"[{i + 1}] {file_name}")
    print("========================")

    # 選擇音訊檔案
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

    # 選擇 Whisper 模型大小
    models = ["tiny", "base", "small", "medium", "large-v3"]
    print("\n=== 請選擇 Whisper 模型大小 ===")
    print("模型越大越精準，但需要更多顯存與計算時間。")
    for i, m in enumerate(models):
        default_tag = " (預設，最準確但最慢)" if m == "large-v3" else ""
        if m == "medium":
            default_tag = " (推薦，速度與精準度平衡)"
        print(f"[{i + 1}] {m}{default_tag}")

    try:
        model_choice = input(f"請輸入模型編號 (1-{len(models)}) [預設 5 (large-v3)]: ").strip()
        if not model_choice:
            model_size = "large-v3"
        else:
            m_idx = int(model_choice) - 1
            if 0 <= m_idx < len(models):
                model_size = models[m_idx]
            else:
                model_size = "large-v3"
    except Exception:
        model_size = "large-v3"

    device = "cpu"
    compute_type = "int8"
    print(f"\n使用 CPU 執行 ({compute_type})。如需 GPU 加速，將 device 改為 'cuda'、compute_type 改為 'float16'。")

    print(f"\n正在載入 {model_size} 模型，第一次載入會自動下載模型，請稍候...")
    start_time = time.time()
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception as e:
        print(f"⚠️ 模型載入失敗 ({e})，將嘗試使用 CPU int8 執行...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"模型載入完成！耗時 {time.time() - start_time:.2f} 秒。")

    # 2. 判斷是否需要切割
    total_duration = get_duration(selected_file)
    print(f"\n音訊總長度: {format_time_txt(total_duration)}")

    chunk_dir = os.path.join(TEMP_DIR, os.path.splitext(os.path.basename(selected_file))[0])
    need_split = total_duration > SPLIT_THRESHOLD_MINUTES * 60

    if need_split:
        print(f"檔案長度超過 {SPLIT_THRESHOLD_MINUTES} 分鐘，將切割成每段 {CHUNK_MINUTES} 分鐘後逐段轉錄...")
        chunk_files = split_audio(selected_file, CHUNK_MINUTES, chunk_dir)
        print(f"已切割成 {len(chunk_files)} 段。")
    else:
        chunk_files = [selected_file]

    # 強制繁體中文提示詞，這能大幅提高 Whisper 輸出繁體中文的機率
    initial_prompt = "以下是繁體中文的對話。"

    transcripts = []
    pbar = tqdm(total=round(total_duration), unit="sec", desc="整體轉錄進度")

    offset = 0.0
    for chunk_idx, chunk_file in enumerate(chunk_files, 1):
        print(f"\n[{chunk_idx}/{len(chunk_files)}] 轉錄中: {os.path.basename(chunk_file)}")
        segments, info = model.transcribe(
            chunk_file,
            beam_size=5,
            language="zh",
            initial_prompt=initial_prompt,
        )

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

    # 輸出檔案名稱命名
    base_name, _ = os.path.splitext(selected_file)
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


if __name__ == "__main__":
    main()
