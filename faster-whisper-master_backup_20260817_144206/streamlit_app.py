import os
import tempfile
import time
import glob
import shutil
import subprocess

import streamlit as st
from faster_whisper import WhisperModel

# ============ 可調整參數 ============
CHUNK_MINUTES = 15
SPLIT_THRESHOLD_MINUTES = 20
TEMP_DIR = "temp_chunks"
# =====================================

SUPPORTED_EXTENSIONS = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus')
MODELS = ["tiny", "base", "small", "medium", "large-v3"]


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
            return False
    return True


def get_duration(file_path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", file_path]
    out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    return float(out)


def split_audio(input_file: str, chunk_minutes: int, output_dir: str):
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
        raise RuntimeError("切割失敗，未產生任何分段檔案。")
    return chunk_files


def transcribe_audio(uploaded_file, model_size, device, compute_type, progress_callback=None):
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    try:
        if progress_callback:
            progress_callback("正在載入模型...")

        start_time = time.time()
        try:
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            if progress_callback:
                progress_callback(f"模型載入完成（使用 CPU int8）。耗時 {time.time() - start_time:.2f} 秒。")
        else:
            if progress_callback:
                progress_callback(f"模型載入完成！耗時 {time.time() - start_time:.2f} 秒。")

        total_duration = get_duration(tmp_path)

        chunk_dir = os.path.join(TEMP_DIR, os.path.splitext(os.path.basename(tmp_path))[0])
        need_split = total_duration > SPLIT_THRESHOLD_MINUTES * 60

        if need_split:
            if progress_callback:
                progress_callback(f"音訊長度 {format_time_txt(total_duration)}，超過 {SPLIT_THRESHOLD_MINUTES} 分鐘，正在切割...")
            chunk_files = split_audio(tmp_path, CHUNK_MINUTES, chunk_dir)
            if progress_callback:
                progress_callback(f"已切割成 {len(chunk_files)} 段。")
        else:
            chunk_files = [tmp_path]

        initial_prompt = "以下是繁體中文的對話。"
        transcripts = []

        offset = 0.0
        for chunk_idx, chunk_file in enumerate(chunk_files, 1):
            if progress_callback:
                progress_callback(f"正在轉錄第 {chunk_idx}/{len(chunk_files)} 段...")

            segments, info = model.transcribe(
                chunk_file,
                beam_size=5,
                language="zh",
                initial_prompt=initial_prompt,
            )

            for segment in segments:
                shifted_start = segment.start + offset
                shifted_end = segment.end + offset
                transcripts.append((shifted_start, shifted_end, segment.text.strip()))

            offset += get_duration(chunk_file)

        # 產生輸出檔案內容
        base_name = os.path.splitext(uploaded_file.name)[0]

        txt_time_content = ""
        for start, end, text in transcripts:
            txt_time_content += f"[{format_time_txt(start)} -> {format_time_txt(end)}] {text}\n"

        txt_clean_content = ""
        for _, _, text in transcripts:
            txt_clean_content += f"{text}\n"

        srt_content = ""
        for i, (start, end, text) in enumerate(transcripts, 1):
            srt_content += f"{i}\n"
            srt_content += f"{format_time_srt(start)} --> {format_time_srt(end)}\n"
            srt_content += f"{text}\n\n"

        if need_split:
            shutil.rmtree(chunk_dir, ignore_errors=True)

        return {
            "txt_time": txt_time_content,
            "txt_clean": txt_clean_content,
            "srt": srt_content,
            "duration": format_time_txt(total_duration),
            "segments_count": len(transcripts),
        }
    finally:
        os.unlink(tmp_path)


def main():
    st.set_page_config(
        page_title="Whisper 語音轉錄工具",
        page_icon="🎙️",
        layout="wide",
    )

    st.title("🎙️ Whisper 語音轉錄工具")
    st.markdown("上傳音訊檔案，使用 Faster-Whisper 進行語音轉文字（繁體中文）")

    if not check_ffmpeg():
        st.error("❌ 找不到 ffmpeg 或 ffprobe，請先安裝 ffmpeg 並確認已加入系統 PATH。")
        st.stop()

    # 側邊欄設定
    with st.sidebar:
        st.header("⚙️ 設定")

        model_size = st.selectbox(
            "Whisper 模型",
            MODELS,
            index=3,
            help="模型越大越精準，但需要更多記憶體與計算時間。medium 為推薦平衡選項。",
        )

        device_options = ["cpu"]
        compute_options = ["int8", "float32", "float16"]
        default_device = "cpu"
        default_compute = "int8"

        device = st.selectbox("運算裝置", device_options, index=0)
        compute_type = st.selectbox("運算精度", compute_options, index=0)

        st.divider()
        st.caption("💡 **提示**：首次使用較大模型時會自動下載模型檔案，請耐心等待。")

    # 上傳檔案
    uploaded_file = st.file_uploader(
        "上傳音訊檔案",
        type=[ext.lstrip('.') for ext in SUPPORTED_EXTENSIONS],
        help=f"支援格式：{', '.join(SUPPORTED_EXTENSIONS)}",
    )

    if uploaded_file is not None:
        st.info(f"已上傳：**{uploaded_file.name}**（{uploaded_file.size / (1024*1024):.2f} MB）")

        # 嘗試取得音訊長度
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name
        try:
            duration = get_duration(tmp_path)
            st.metric("音訊長度", format_time_txt(duration))
        except Exception:
            st.warning("無法讀取音訊長度資訊")
        finally:
            os.unlink(tmp_path)

        if st.button("🚀 開始轉錄", type="primary", use_container_width=True):
            status_placeholder = st.empty()
            progress_bar = st.progress(0, text="準備中...")

            def update_progress(msg):
                status_placeholder.info(f"⏳ {msg}")

            with st.spinner("轉錄中，請勿關閉頁面..."):
                try:
                    result = transcribe_audio(
                        uploaded_file, model_size, device, compute_type,
                        progress_callback=update_progress,
                    )
                    progress_bar.progress(100, text="轉錄完成！")

                    st.success(f"✅ 轉錄完成！共 {result['segments_count']} 個段落，音訊長度 {result['duration']}")

                    # 顯示結果
                    tab1, tab2, tab3 = st.tabs(["📝 純文字版", "⏱️ 時間戳記版", "📄 SRT 字幕檔"])

                    with tab1:
                        st.text_area("純文字", result["txt_clean"], height=300)

                    with tab2:
                        st.text_area("時間戳記版", result["txt_time"], height=300)

                    with tab3:
                        st.text_area("SRT 字幕", result["srt"], height=300)

                    # 下載按鈕
                    base_name = os.path.splitext(uploaded_file.name)[0]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.download_button(
                            "📥 下載純文字版 (.txt)",
                            result["txt_clean"],
                            file_name=f"{base_name}_clean.txt",
                            mime="text/plain",
                            use_container_width=True,
                        )
                    with col2:
                        st.download_button(
                            "📥 下載時間戳記版 (.txt)",
                            result["txt_time"],
                            file_name=f"{base_name}_transcript.txt",
                            mime="text/plain",
                            use_container_width=True,
                        )
                    with col3:
                        st.download_button(
                            "📥 下載 SRT 字幕檔 (.srt)",
                            result["srt"],
                            file_name=f"{base_name}.srt",
                            mime="text/plain",
                            use_container_width=True,
                        )

                except Exception as e:
                    progress_bar.empty()
                    status_placeholder.empty()
                    st.error(f"❌ 轉錄失敗：{e}")


if __name__ == "__main__":
    main()
