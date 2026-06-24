# 🎯 AiSub Whisper优化配置指南

## 📋 优化总览

本项目已集成了针对中文语音识别的Whisper优化配置，相比默认设置可显著提升转录准确性和连贯性。

## 🚀 主要优化点

### 1. 中文语音识别优化
- **语言明确指定**: `language: "zh"` 避免自动检测的不稳定性
- **上下文关联**: `condition_on_previous_text: true` 提高中文语句连贯性
- **中文提示词**: 专门的中文初始提示提高识别准确性
- **中文标点符号**: 优化的中文标点符号处理

### 2. 搜索质量提升
- **束搜索**: `beam_size: 5` 增加搜索候选数量
- **最佳选择**: `best_of: 5` 从更多候选中选择最优结果  
- **耐心参数**: `patience: 1.0` 平衡质量和速度

### 3. 噪音抑制优化
- **精准token抑制**: `[50256, 50257, 50358, 50359, 50360]`
- **语音检测阈值**: `no_speech_threshold: 0.5` 优化的静音检测

## ⚙️ 配置使用方式

### 方式1：使用预设方法（推荐）

```python
from src.utils.whisper_transcriber import WhisperTranscriber

# 创建转录器
transcriber = WhisperTranscriber(model_size="base")

# 使用中文优化配置
result = transcriber.transcribe_with_chinese_optimization("audio.wav")

# 使用速度优化配置
result = transcriber.transcribe_with_speed_optimization("audio.wav")
```

### 方式2：使用配置字典

```python
# 获取中文优化配置
config = WhisperTranscriber.get_chinese_optimized_config()

# 自定义调整
config['beam_size'] = 3  # 降低搜索质量换取速度
config['model_size'] = 'small'  # 使用更大模型

# 应用配置
result = transcriber.transcribe_audio("audio.wav", **config)
```

### 方式3：配置文件方式

在 `config.yaml` 中已更新为优化配置：

```yaml
whisper:
  transcription:
    language: "zh"
    condition_on_previous_text: true
    initial_prompt: "以下是一段中文音频的转录。请准确识别每个字词，保持语言的连贯性和自然性。"
    suppress_tokens: [50256, 50257, 50358, 50359, 50360]
    no_speech_threshold: 0.5
    beam_size: 5
    best_of: 5
    patience: 1.0
```

## 📊 性能对比

| 配置类型 | 准确性 | 连贯性 | 处理速度 | 适用场景 |
|----------|--------|--------|----------|----------|
| **中文优化** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 高质量中文转录 |
| **速度优化** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 快速批量处理 |
| **默认配置** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | 通用场景 |

## 🔧 参数详解

### 核心优化参数

```python
{
    # === 语言设置 ===
    'language': 'zh',                    # 明确指定中文，避免检测错误
    
    # === 质量提升 ===
    'condition_on_previous_text': True,  # 启用上下文关联
    'beam_size': 5,                      # 束搜索宽度（1-10）
    'best_of': 5,                        # 候选数量（1-10）
    'patience': 1.0,                     # 搜索耐心（0.0-2.0）
    
    # === 噪音控制 ===
    'suppress_tokens': [50256, 50257, 50358, 50359, 50360],  # 抑制特定噪音token
    'no_speech_threshold': 0.5,          # 语音检测阈值（0.0-1.0）
    
    # === 中文优化 ===
    'initial_prompt': "以下是一段中文音频的转录...",  # 中文提示词
    'append_punctuations': "\"'.。,，!！?？:：)]}、",   # 中文标点符号
}
```

### 参数调优建议

**高质量场景**（准确性优先）:
```python
config = {
    'beam_size': 5,
    'best_of': 5,
    'patience': 1.0,
    'condition_on_previous_text': True
}
```

**快速处理场景**（速度优先）:
```python
config = {
    'beam_size': 1,        # 或不设置
    'best_of': 1,          # 或不设置
    'condition_on_previous_text': False,
    'initial_prompt': ""
}
```

**平衡场景**:
```python
config = {
    'beam_size': 3,
    'best_of': 3,
    'condition_on_previous_text': True,
    'patience': 0.5
}
```

## 🧪 测试验证

### 运行对比测试
```bash
# 完整对比测试
python test_whisper_optimization.py audio.wav --model base

# 快速演示
python examples/simple_whisper_demo.py
```

### 测试结果解读
- **文本长度**: 优化配置通常产生更详细的转录
- **处理时间**: 质量优化会增加处理时间
- **语言检测**: 明确指定语言避免检测错误
- **连贯性**: 上下文关联提升语句自然度

## 💡 最佳实践

1. **模型选择**:
   - 日常使用: `base` 模型 + 中文优化
   - 高质量需求: `small` 或 `large` 模型
   - 快速预览: `tiny` 模型 + 速度优化

2. **参数调优**:
   - 清晰音频: 使用完整优化配置
   - 噪音环境: 结合音频预处理 + 优化配置
   - 长音频: 适当降低 `beam_size` 和 `best_of`

3. **性能平衡**:
   - CPU环境: 优先速度优化
   - GPU环境: 可使用完整质量优化
   - 批量处理: 考虑速度与质量的平衡

## 🔗 相关文件

- `config.yaml`: 全局配置文件
- `src/utils/whisper_transcriber.py`: 核心转录器
- `test_whisper_optimization.py`: 效果对比测试
- `examples/simple_whisper_demo.py`: 使用演示

## 📞 问题排查

**常见问题**:
1. **处理速度慢**: 降低 `beam_size` 和 `best_of` 参数
2. **准确性不佳**: 检查音频质量，考虑使用更大模型
3. **标点错误**: 确认 `append_punctuations` 参数设置
4. **语言检测错误**: 明确设置 `language: "zh"`

**优化建议**:
- 结合音频预处理使用
- 根据具体场景调整参数
- 定期测试不同配置的效果