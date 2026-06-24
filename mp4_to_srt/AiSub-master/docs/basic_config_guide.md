# AiSub 基础配置模式

本次更新为AiSub添加了**基础配置模式**，让本地Whisper处理使用最基础的配置，不开启降噪等额外功能，只保留提示词。

## 🎯 主要变更

### 1. 配置文件修改 (`config.yaml`)

#### 音频预处理
```yaml
ffmpeg:
  audio_preprocessing:
    enabled: false  # 默认关闭音频预处理（降噪、人声增强）
```

#### Whisper转录设置
```yaml
whisper:
  transcription:
    basic_mode: true  # 启用基础模式
    
    # 基础参数（保留）
    language: "zh"
    task: "transcribe"
    temperature: 0.0
    word_timestamps: true
    initial_prompt: "以下是一段中文音频的转录。"  # 简化的提示词
    verbose: false
    
    # 优化参数（基础模式下被忽略）
    condition_on_previous_text: false
    beam_size: null
    best_of: null
    patience: null
    # ... 其他优化参数
```

### 2. 代码修改

#### 配置加载器 (`src/utils/config_loader.py`)
- 新增 `get_whisper_basic_config()` 方法
- 根据 `basic_mode` 配置自动过滤优化参数

#### Whisper转录器 (`src/utils/whisper_transcriber.py`) 
- 新增 `get_basic_config()` 静态方法
- 新增 `transcribe_with_basic_config()` 方法

#### 主应用程序 (`src/aisub_app.py`)
- 修改转录逻辑使用基础配置
- 在日志中明确显示使用基础模式

## 📊 基础模式 vs 优化模式对比

| 特性 | 基础模式 | 优化模式 |
|------|----------|----------|
| **音频预处理** | ❌ 关闭 | ✅ 启用（降噪、人声增强） |
| **初始提示词** | 简单提示 | 详细中文优化提示 |
| **上下文关联** | ❌ 关闭 | ✅ 启用 |
| **束搜索** | ❌ 不使用 | ✅ beam_size=5 |
| **最佳候选** | ❌ 不使用 | ✅ best_of=5 |
| **耐心参数** | ❌ 不使用 | ✅ patience=1.0 |
| **噪音抑制** | 默认 | 精准抑制特定token |
| **语音检测阈值** | 0.6（默认） | 0.5（优化） |

## ⚡ 性能优势

基础模式的优势：
- **更快的处理速度** - 减少复杂计算
- **更低的内存使用** - 不进行音频预处理
- **更稳定的处理** - 使用Whisper默认配置
- **接近原生体验** - 最接近原版Whisper的行为

## 🚀 使用方法

### 自动使用基础配置
配置文件中 `basic_mode: true` 时，本地处理会自动使用基础配置：

```bash
python main.py transcribe video.mp4
```

### 手动使用基础配置
```python
from src.utils.whisper_transcriber import WhisperTranscriber

transcriber = WhisperTranscriber(model_size="base")

# 使用基础配置
result = transcriber.transcribe_with_basic_config("audio.wav")

# 或覆盖特定参数
result = transcriber.transcribe_with_basic_config(
    "audio.wav", 
    language="en"  # 覆盖语言设置
)
```

## 🎯 适用场景

### 推荐使用基础模式：
- ✅ 音频质量较好，无明显噪音
- ✅ 需要快速批量处理
- ✅ 系统资源有限
- ✅ 希望接近原生Whisper体验
- ✅ 对转录速度要求较高

### 推荐使用优化模式：
- ⚡ 音频有背景噪音
- ⚡ 需要最高转录质量
- ⚡ 处理复杂的中文内容
- ⚡ 系统资源充足

## 📝 配置切换

### 启用基础模式
```yaml
whisper:
  transcription:
    basic_mode: true
ffmpeg:
  audio_preprocessing:
    enabled: false
```

### 启用优化模式  
```yaml
whisper:
  transcription:
    basic_mode: false
ffmpeg:
  audio_preprocessing:
    enabled: true
```

## 🧪 测试验证

运行测试脚本验证配置：

```bash
python test_basic_config.py
```

该脚本会：
- ✅ 验证配置文件结构
- ✅ 测试基础配置参数
- ✅ 对比不同配置模式
- ✅ 显示配置差异

## 🔧 故障排除

### 如果想要完全关闭所有优化
确保配置文件中：
```yaml
whisper:
  transcription:
    basic_mode: true
    beam_size: null
    best_of: null
    patience: null
    condition_on_previous_text: false

ffmpeg:
  audio_preprocessing:
    enabled: false
```

### 验证当前使用的配置
查看日志输出，会显示：
```
使用基础Whisper配置（不包含降噪等优化功能）
开始语音识别（单文件，基础模式）...
```

---

通过这些修改，AiSub现在提供了更灵活的配置选项，用户可以根据自己的需求选择基础模式（快速、简单）或优化模式（高质量、功能丰富）。