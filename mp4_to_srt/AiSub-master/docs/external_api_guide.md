# AiSub 外部 API 使用指南

## 🚀 功能介绍

AiSub 现在支持多种外部语音识别 API，包括：
- **Google Gemini API** - 高质量的多模态模型
- **OpenAI Whisper API** - 云端 Whisper 服务  
- **Ollama** - 本地部署的开源模型
- **本地 Whisper** - 默认的本地语音识别

## 📋 配置方法

### 1. 设置 API 密钥

**方法一：环境变量（推荐）**
```bash
# Windows
set GEMINI_API_KEY=your_gemini_api_key_here
set OPENAI_API_KEY=your_openai_api_key_here

# Linux/macOS
export GEMINI_API_KEY=your_gemini_api_key_here
export OPENAI_API_KEY=your_openai_api_key_here
```

**方法二：配置文件**
编辑 `config_with_gemini.yaml` 文件，在相应位置填入您的 API 密钥：
```yaml
external_apis:
  gemini:
    api_key: "your_gemini_api_key_here"
  openai:
    api_key: "your_openai_api_key_here"
```

### 2. 获取 API 密钥

**Google Gemini API**
1. 访问 [Google AI Studio](https://makersuite.google.com/)
2. 创建新项目或选择现有项目
3. 生成 API 密钥
4. 设置环境变量或配置文件

**OpenAI API**
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 登录账户并进入 API 设置
3. 创建新的 API 密钥
4. 设置环境变量或配置文件

## 🎯 使用方法

### 命令行使用

**使用 Gemini API**
```bash
python main.py transcribe video.mp4 --engine gemini -c config_with_gemini.yaml
```

**使用 OpenAI API**
```bash
python main.py transcribe video.mp4 --engine openai -c config_with_gemini.yaml
```

**使用 Ollama**
```bash
python main.py transcribe video.mp4 --engine ollama -c config_with_gemini.yaml
```

**默认本地 Whisper**
```bash
python main.py transcribe video.mp4
```

### Python 代码使用

```python
from src.aisub_app import AiSubApplication

# 使用 Gemini API
app = AiSubApplication('config_with_gemini.yaml', external_engine='gemini')
result = app.process_video('video.mp4', 'subtitle_gemini.srt')

# 使用 OpenAI API
app = AiSubApplication('config_with_gemini.yaml', external_engine='openai')
result = app.process_video('video.mp4', 'subtitle_openai.srt')

# 使用本地 Whisper（默认）
app = AiSubApplication()
result = app.process_video('video.mp4', 'subtitle_whisper.srt')
```

## ⚡ 性能对比

| 引擎 | 速度 | 质量 | 成本 | 隐私 | 适用场景 |
|------|------|------|------|------|----------|
| 本地 Whisper | 慢 | 高 | 免费 | 完全保护 | 隐私要求高、批量处理 |
| Gemini API | 快 | 很高 | 低 | 上传到谷歌 | 高质量要求、快速处理 |
| OpenAI API | 中等 | 高 | 中等 | 上传到OpenAI | 平衡的选择 |
| Ollama | 中等 | 中等 | 免费 | 完全保护 | 本地部署、定制化 |

## 🔧 高级配置

### 引擎回退机制

在配置文件中设置回退顺序：
```yaml
transcription_engine:
  default_engine: "gemini"
  enable_fallback: true
  fallback_order: ["gemini", "openai", "whisper"]
```

这样当 Gemini API 失败时，会自动尝试 OpenAI API，最后回退到本地 Whisper。

### 自定义提示模板

针对特定领域或语言优化识别效果：
```yaml
external_apis:
  gemini:
    prompt_template: "请转录以下技术讲座音频为中文字幕，注意专业术语的准确性：\n\n音频内容：{audio_text}"
```

### API 限制设置

控制 API 调用频率：
```yaml
external_apis:
  gemini:
    rate_limit: 15  # 每分钟最大请求数
    timeout: 300    # 请求超时时间（秒）
```

## 🛠️ 故障排除

### 常见错误

**1. API 密钥错误**
```
ValueError: Gemini API key is required
```
解决：检查环境变量或配置文件中的 API 密钥设置

**2. 网络连接问题**
```
requests.exceptions.ConnectionError
```
解决：检查网络连接，考虑使用代理或 VPN

**3. API 配额超限**
```
HTTP 429: Too Many Requests
```
解决：等待配额重置或升级 API 计划

### 调试模式

使用详细输出查看详细信息：
```bash
python main.py transcribe video.mp4 --engine gemini --verbose
```

## 💡 最佳实践

### 1. 选择合适的引擎
- **快速预览**：使用 Gemini API
- **高质量需求**：使用 OpenAI API 或本地 large 模型
- **隐私保护**：使用本地 Whisper
- **批量处理**：使用本地 Whisper

### 2. 成本优化
- 对短视频使用外部 API
- 对长视频使用本地 Whisper
- 设置合理的 rate_limit 避免超限

### 3. 质量优化
- 为特定领域定制提示模板
- 预处理音频以提高质量
- 使用回退机制确保可靠性

## 🔐 安全建议

1. **不要在代码中硬编码 API 密钥**
2. **使用环境变量存储敏感信息**
3. **定期轮换 API 密钥**
4. **监控 API 使用情况和费用**
5. **对敏感内容使用本地 Whisper**

## 📞 技术支持

如果您在使用过程中遇到问题：

1. 查看本文档的故障排除部分
2. 使用 `--verbose` 参数获取详细错误信息
3. 检查 API 服务状态和配额
4. 提交 Issue 并附上错误日志

---

**享受多引擎语音识别的强大功能！** 🎉