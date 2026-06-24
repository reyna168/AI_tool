# AiSub 设备配置功能

本次更新为AiSub添加了**详细的设备配置选项**，让用户可以灵活选择使用CPU或GPU（CUDA）进行本地Whisper处理。

## 🎯 主要功能

### 1. 设备选择选项

- **auto** - 自动检测最佳设备（优先级：CUDA > CPU）
- **cuda** - 强制使用NVIDIA CUDA GPU
- **cpu** - 强制使用CPU

### 2. 详细配置选项

#### CUDA配置
- 启用/禁用CUDA
- 指定GPU设备ID
- 内存管理策略
- 显存分配控制

#### CPU配置  
- CPU线程数设置
- CPU优化选项

## 🔧 配置文件格式

### 新格式（推荐）

```yaml
whisper:
  model_size: "base"
  
  # 详细设备配置
  device_config:
    # 首选设备类型
    preferred_device: "auto"  # auto/cuda/cpu
    
    # CUDA配置
    cuda:
      enabled: true
      device_id: -1           # -1为自动选择，0+为指定GPU
      memory_fraction: 0      # 0为动态分配
      allow_growth: true      # 允许内存增长
    
    # CPU配置
    cpu:
      num_threads: 0          # 0为自动检测
      optimize: true          # 启用CPU优化
```

### 兼容旧格式

```yaml
whisper:
  device: "auto"  # 继续支持，会自动转换为新格式
```

## 💻 使用方法

### 命令行使用

```bash
# 自动检测设备
python main.py transcribe video.mp4

# 强制使用CUDA
python main.py transcribe video.mp4 --device cuda

# 强制使用CPU
python main.py transcribe video.mp4 --device cpu

# 查看设备信息
python main.py info
```

### 代码使用

```python
from src.utils.whisper_transcriber import WhisperTranscriber

# 自动检测设备
transcriber = WhisperTranscriber(model_size="base")

# 强制使用CPU
transcriber = WhisperTranscriber(model_size="base", device="cpu")

# 使用详细设备配置
device_config = {
    'preferred_device': 'cuda',
    'cuda': {
        'enabled': True,
        'device_id': 0,         # 使用第一个GPU
        'allow_growth': True
    },
    'cpu': {
        'num_threads': 4,       # 使用4个CPU线程
        'optimize': True
    }
}

transcriber = WhisperTranscriber(
    model_size="base",
    device_config=device_config
)
```

## 🚀 智能设备检测

### 检测逻辑

1. **auto模式**：
   - 检查CUDA是否可用
   - 检查GPU驱动和设备
   - 自动选择最佳设备

2. **cuda模式**：
   - 验证CUDA可用性
   - 如果不可用，提示或回退到CPU

3. **cpu模式**：
   - 直接使用CPU
   - 应用CPU优化配置

### 设备信息显示

运行 `python main.py info` 查看：

```
🖥️  设备信息:
   CUDA 可用: 是
   GPU 数量: 1
   GPU 0: NVIDIA GeForce RTX 4080 (16.0 GB)
   首选设备: auto
   CUDA 配置: 已启用
     指定设备: GPU 0
     内存增长: 已启用
```

## ⚙️ 高级配置示例

### 多GPU环境

```yaml
whisper:
  device_config:
    preferred_device: "cuda"
    cuda:
      enabled: true
      device_id: 1          # 使用第二个GPU
      allow_growth: true
```

### CPU优化

```yaml
whisper:
  device_config:
    preferred_device: "cpu"
    cpu:
      num_threads: 8        # 使用8个线程
      optimize: true
```

### 混合策略

```yaml
whisper:
  device_config:
    preferred_device: "auto"
    cuda:
      enabled: true
      memory_fraction: 0.8  # 只使用80%显存
    cpu:
      num_threads: 4        # CPU回退时使用4线程
```

## 🔍 故障排除

### CUDA问题

如果CUDA不可用：

1. **检查GPU驱动**：
   ```bash
   nvidia-smi
   ```

2. **检查CUDA安装**：
   ```bash
   nvcc --version
   ```

3. **安装CUDA版本的PyTorch**：
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

### 性能优化

1. **GPU内存不足**：
   - 使用更小的模型（tiny, base）
   - 启用 `allow_growth: true`
   - 设置 `memory_fraction` 限制显存使用

2. **CPU性能优化**：
   - 设置合适的 `num_threads`
   - 启用 `optimize: true`
   - 考虑使用更小的模型

## 📊 性能对比

| 设备类型 | 处理速度 | 内存使用 | 兼容性 | 推荐场景 |
|---------|----------|----------|--------|----------|
| **CUDA** | ⭐⭐⭐⭐⭐ | 高 | ⭐⭐⭐⭐ | **有N卡时首选** |
| **CPU** | ⭐⭐⭐ | 低 | ⭐⭐⭐⭐⭐ | **稳定可靠** |

## 🎯 最佳实践

### 推荐配置

**有NVIDIA GPU时：**
```yaml
whisper:
  device_config:
    preferred_device: "cuda"
    cuda:
      enabled: true
      allow_growth: true
```

**仅CPU时：**
```yaml
whisper:
  device_config:
    preferred_device: "cpu"
    cpu:
      num_threads: 0  # 自动检测
      optimize: true
```

**不确定环境时：**
```yaml
whisper:
  device_config:
    preferred_device: "auto"  # 让系统自动选择
```

## 🧪 测试验证

运行测试脚本验证配置：

```bash
python test_device_config.py
```

该脚本会：
- ✅ 检查设备配置加载
- ✅ 检测可用的计算设备
- ✅ 测试不同设备的Whisper初始化
- ✅ 验证配置覆盖功能

---

通过这些设备配置选项，AiSub现在可以灵活适应不同的硬件环境，为用户提供最佳的性能和兼容性。无论是使用高性能的NVIDIA GPU还是依赖CPU处理，都能获得良好的使用体验.