import os
import sys
import time
from faster_whisper import WhisperModel
from tqdm import tqdm

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

def main():
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
        
    # 自動偵測 GPU/CUDA
    # device = "cuda"
    # compute_type = "float16"
    device = "cpu"
    compute_type = "int8"
    print(f"\n預設使用 GPU (CUDA) 加速執行 ({compute_type})。")
    
    print(f"\n正在載入 {model_size} 模型，第一次載入會自動下載模型，請稍候...")
    start_time = time.time()
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception as e:
        print(f"⚠️ GPU 載入失敗 ({e})，將嘗試使用 CPU 執行...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
    print(f"模型載入完成！耗時 {time.time() - start_time:.2f} 秒。")
    
    # 開始轉錄
    print(f"\n開始轉錄: {selected_file}")
    
    # 強制繁體中文提示詞，這能大幅提高 Whisper 輸出繁體中文的機率
    initial_prompt = "以下是繁體中文的對話。"
    
    segments, info = model.transcribe(
        selected_file,
        beam_size=5,
        language="zh",
        initial_prompt=initial_prompt
    )
    
    print(f"偵測到音訊語言: '{info.language}'，信心度: {info.language_probability:.2f}")
    print(f"音訊總長度: {format_time_txt(info.duration)}")
    
    # 進度條設定 (依據音訊總秒數)
    pbar = tqdm(total=round(info.duration), unit="sec", desc="轉錄進度")
    last_end = 0
    
    transcripts = []
    
    for segment in segments:
        transcripts.append(segment)
        # 更新進度條
        step = round(segment.end - last_end)
        if step > 0:
            pbar.update(min(step, pbar.total - pbar.n))
        last_end = segment.end
        
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
        for seg in transcripts:
            start_str = format_time_txt(seg.start)
            end_str = format_time_txt(seg.end)
            f.write(f"[{start_str} -> {end_str}] {seg.text.strip()}\n")
            
    # 2. 儲存純文字乾淨版
    with open(txt_clean_file, "w", encoding="utf-8") as f:
        for seg in transcripts:
            f.write(f"{seg.text.strip()}\n")
            
    # 3. 儲存 SRT 字幕檔
    with open(srt_file, "w", encoding="utf-8") as f:
        for i, seg in enumerate(transcripts, 1):
            f.write(f"{i}\n")
            f.write(f"{format_time_srt(seg.start)} --> {format_time_srt(seg.end)}\n")
            f.write(f"{seg.text.strip()}\n\n")
            
    print(f"✅ 轉錄成功！已生成以下檔案：")
    print(f"1. 時間戳記版：{os.path.abspath(txt_time_file)}")
    print(f"2. 純文字乾淨版：{os.path.abspath(txt_clean_file)}")
    print(f"3. SRT 字幕檔：{os.path.abspath(srt_file)}")

if __name__ == "__main__":
    main()
