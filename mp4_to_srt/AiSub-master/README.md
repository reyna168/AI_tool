# AiSub - AI 视频字幕生成器

🎬 **AiSub** 是一个基于 FFmpeg 和 OpenAI Whisper 的智能视频字幕生成工具，支持多种语言的语音识别，能够为长视频生成高质量的 SRT 字幕文件。

## ✨ 主要特性

- 🎯 **高精度语音识别**: 使用 OpenAI Whisper 模型，支持多种语言
- 🎵 **智能音频预处理**: 内置降噪、人声增强功能，显著提升噪音环境下的转录质量
- 🚀 **多引擎转录支持**: 支持本地 Whisper、Gemini、OpenAI 等多种转录引擎
- ⚡ **性能优化**: Gemini 引擎支持长音频处理，性能提升高达 8.75 倍
- 🎬 **多格式视频支持**: 支持 MP4、AVI、MOV、MKV 等常见视频格式  
- ⚡ **智能分段处理**: 自动分割长视频，提高处理效率和稳定性
- 🔧 **本地部署**: 完全本地运行，保护您的隐私
- 📝 **标准字幕格式**: 生成标准 SRT 字幕文件，兼容各种播放器
- 🎛️ **高度可配置**: 丰富的配置选项，满足不同需求
- 💻 **GPU 加速**: 支持 CUDA GPU 加速，大幅提升处理速度
- 🌍 **多语言支持**: 自动检测语言或手动指定，支持中文、英文、日文、韩文等

## 🚀 快速开始

### 环境要求

- **Python**: 3.8 或更高版本
- **FFmpeg**: 需要安装并添加到系统 PATH
- **GPU** (可选): NVIDIA GPU + CUDA 支持可大幅提升处理速度

### 安装步骤

1. **克隆或下载项目**
   ```bash
   git clone <repository_url>
   cd AiSub
   ```

2. **安装 Python 依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **安装 FFmpeg**
   
   **Windows:**
   - 下载 FFmpeg: https://ffmpeg.org/download.html
   - 解压并添加到系统 PATH
   
   **macOS:**
   ```bash
   brew install ffmpeg
   ```
   
   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```

4. **验证安装**
   ```bash
   python main.py info
   ```

### 基本使用

#### 处理单个视频文件

```bash
# 基本用法
python main.py transcribe video.mp4

# 指定输出路径
python main.py transcribe video.mp4 -o subtitle.srt

# 指定语言
python main.py transcribe video.mp4 -l zh

# 使用更高精度的模型
python main.py transcribe video.mp4 -m small

# 强制使用 CPU
python main.py transcribe video.mp4 --device cpu

# 使用 Gemini 引擎（推荐）
python main.py transcribe video.mp4 -e gemini

# 使用音频预处理增强配置
python main.py transcribe video.mp4 -c config_audio_enhance.yaml
```

#### 🎵 音频预处理功能

AiSub 内置了先进的音频预处理功能，可以显著提升噪音环境下的转录质量：

- **降噪处理**：移除低频噪音（空调、风扇等）和高频噪音
- **人声增强**：突出人声频段（85Hz-4000Hz），适度增强音量
- **智能过滤**：自动识别和抑制背景音乐和噪音

使用方法：
```yaml
# 在 config.yaml 中启用
ffmpeg:
  audio_preprocessing:
    enabled: true              # 启用音频预处理
    noise_reduction: 0.12      # 降噪强度 (0.01-1.0)
    voice_enhancement: true    # 启用人声增强
    show_progress: true        # 显示预处理进度
```

#### 🎯 转录引擎对比

| 引擎 | 时间戳精度 | 处理速度 | 文件大小限制 | 推荐场景 |
|------|------------|----------|--------------|----------|
| **本地 Whisper** | ⭐⭐⭐⭐⭐ 音频对齐 | 中等 | 无限制 | **高精度字幕制作** |
| **Gemini API** | ⭐⭐⭐ AI分析 | 很快 | 10MB, 30秒 | 快速预览、短视频 |
| **OpenAI API** | ⭐⭐⭐⭐ 较准确 | 快 | 25MB | 平衡选择 |

> ℹ️ **时间戳说明**：
> - **Gemini API**: 现在支持SRT格式输出，能提供基于AI分析的时间戳，质量中等
> - **本地 Whisper**: 提供最高精度的音频对齐时间戳，适合专业制作
> - **建议**: 短视频使用Gemini快速预览，高质量需求使用Whisper

#### 其他实用命令

```bash
# 查看系统信息
python main.py info

# 估算处理时间
python main.py estimate video.mp4

# 验证字幕文件
python main.py validate subtitle.srt
```

## 🔧 配置说明

项目使用 `config.yaml` 文件进行配置。主要配置项包括：

### Whisper 模型选择

| 模型 | 参数量 | 显存需求 | 相对速度 | 适用场景 |
|------|--------|----------|----------|----------|
| tiny | 39M | ~1GB | ~32x | 快速预览 |
| base | 74M | ~1GB | ~16x | **推荐平衡选择** |
| small | 244M | ~2GB | ~6x | 高质量需求 |
| medium | 769M | ~5GB | ~2x | 专业级质量 |
| large | 1550M | ~10GB | ~1x | 最高质量 |

### 关键配置项

```yaml
# Whisper 设置
whisper:
  model_size: "base"          # 模型大小
  device: "auto"              # 设备选择
  transcription:
    language: "auto"          # 语言设置
    temperature: 0.0          # 随机性控制

# 字幕生成设置  
subtitle:
  max_line_length: 80         # 每行最大字符数
  max_lines_per_subtitle: 2   # 每个字幕最大行数
  min_subtitle_duration: 1.0  # 最小持续时间
  max_subtitle_duration: 10.0 # 最大持续时间

# 处理设置
processing:
  split_long_audio: true      # 是否分割长音频
  segment_length: 300         # 分割长度(秒)
  cleanup_temp_files: true    # 自动清理临时文件
```

## 📁 项目结构

```
AiSub/
├── src/                    # 源代码目录
│   ├── utils/             # 工具模块
│   │   ├── ffmpeg_wrapper.py      # FFmpeg 包装器
│   │   ├── whisper_transcriber.py # Whisper 转录器
│   │   ├── srt_generator.py       # SRT 生成器
│   │   └── config_loader.py       # 配置加载器
│   └── aisub_app.py       # 主应用程序
├── examples/              # 示例脚本
├── tests/                 # 测试文件
├── output/                # 默认输出目录
├── main.py               # 命令行入口
├── config.yaml           # 配置文件
├── requirements.txt      # 依赖列表
└── README.md            # 项目文档
```

## 🎯 使用示例

### 示例 1: 处理中文视频

```bash
python main.py transcribe chinese_video.mp4 -l zh -m base
```

### 示例 2: 处理英文视频 (高质量)

```bash
python main.py transcribe english_video.mp4 -l en -m small -o subtitles/english.srt
```

### 示例 3: 自动语言检测

```bash
python main.py transcribe multilingual_video.mp4 -m medium
```

### 示例 4: 批量处理 (通过脚本)

创建批处理脚本：

```python
from src.aisub_app import AiSubApplication
import os

app = AiSubApplication()
video_dir = "videos/"
output_dir = "subtitles/"

for video_file in os.listdir(video_dir):
    if video_file.endswith(('.mp4', '.avi', '.mov')):
        video_path = os.path.join(video_dir, video_file)
        output_path = os.path.join(output_dir, f"{os.path.splitext(video_file)[0]}.srt")
        
        try:
            app.process_video(video_path, output_path)
            print(f"✅ 处理完成: {video_file}")
        except Exception as e:
            print(f"❌ 处理失败: {video_file} - {str(e)}")
```

## ⚡ 性能优化建议

### GPU 加速

1. **安装 CUDA**: 
   - 下载并安装 NVIDIA CUDA Toolkit
   - 确保 PyTorch 支持 CUDA

2. **验证 GPU**:
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```

3. **配置 GPU**:
   ```yaml
   whisper:
     device: "cuda"  # 或 "auto"
   ```

### 处理长视频

- 启用音频分段: `split_long_audio: true`
- 调整分段长度: `segment_length: 300` (5分钟)
- 使用适当的模型大小平衡质量和速度

### 内存管理

- 长视频使用分段处理
- 及时清理临时文件
- 监控系统内存使用

## 🐛 常见问题

### Q: FFmpeg 未找到
**A**: 确保 FFmpeg 已安装并添加到系统 PATH。可以通过 `ffmpeg -version` 验证。

### Q: CUDA 内存不足
**A**: 
- 使用更小的模型 (如 `base` 代替 `large`)
- 启用音频分段处理
- 减少分段长度

### Q: 转录质量不佳
**A**: 
- 使用更大的模型 (如 `small` 或 `medium`)
- 检查音频质量
- 尝试指定正确的语言代码

### Q: 处理速度太慢
**A**: 
- 使用 GPU 加速
- 选择更小的模型
- 启用音频分段处理

### Q: 字幕时间轴不准确
**A**: 
- 调整 `min_subtitle_duration` 和 `max_subtitle_duration`
- 检查 `merge_threshold` 设置
- 确保视频音频同步

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 🙏 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 语音识别模型
- [FFmpeg](https://ffmpeg.org/) - 多媒体处理工具
- [PyTorch](https://pytorch.org/) - 深度学习框架

## 📞 支持

如果您遇到问题或有建议，请：

1. 查看本 README 的常见问题部分
2. 搜索已有的 GitHub Issues
3. 创建新的 Issue 并提供详细信息

---

**Happy Subtitling! 🎬✨**