#!/usr/bin/env python3
"""
设备配置功能测试
验证本地Whisper处理时的CPU/GPU设备选择功能
"""

import os
import sys
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.utils.config_loader import ConfigLoader
from src.utils.whisper_transcriber import WhisperTranscriber

def test_device_config():
    """测试设备配置功能"""
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    print("🔧 AiSub 设备配置测试")
    print("=" * 50)
    
    # 1. 测试配置加载器的设备配置功能
    config_loader = ConfigLoader()
    
    print("\n📋 1. 测试设备配置加载")
    print("-" * 30)
    
    device_config = config_loader.get_device_config()
    
    print("设备配置:")
    print(f"  首选设备: {device_config.get('preferred_device', 'auto')}")
    
    # CUDA配置
    cuda_config = device_config.get('cuda', {})
    print(f"  CUDA配置:")
    print(f"    启用: {cuda_config.get('enabled', True)}")
    print(f"    设备ID: {cuda_config.get('device_id', -1)}")
    print(f"    内存增长: {cuda_config.get('allow_growth', True)}")
    
    # CPU配置
    cpu_config = device_config.get('cpu', {})
    print(f"  CPU配置:")
    print(f"    线程数: {cpu_config.get('num_threads', 0)}")
    print(f"    优化: {cpu_config.get('optimize', True)}")
    
    return True

def test_device_detection():
    """测试设备检测功能"""
    
    print("\n🔍 2. 测试设备检测")
    print("-" * 30)
    
    # 检查PyTorch和CUDA
    try:
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        print(f"CUDA可用: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA版本: {torch.version.cuda}")
            print(f"GPU数量: {torch.cuda.device_count()}")
            
            for i in range(torch.cuda.device_count()):
                gpu_name = torch.cuda.get_device_name(i)
                props = torch.cuda.get_device_properties(i)
                memory_gb = props.total_memory / 1024**3
                print(f"  GPU {i}: {gpu_name}")
                print(f"    显存: {memory_gb:.1f} GB")
                print(f"    计算能力: {props.major}.{props.minor}")
        else:
            print("❌ CUDA不可用")
            
            # 检查可能的原因
            print("\n🔍 CUDA检查:")
            print("  - 确保已安装NVIDIA GPU驱动")
            print("  - 确保已安装CUDA toolkit")
            print("  - 确保PyTorch支持CUDA")
            print("  - 可以使用: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
            
    except ImportError:
        print("❌ PyTorch未安装")
        return False
    
    return True

def test_whisper_with_different_devices():
    """测试Whisper在不同设备上的初始化"""
    
    print("\n🤖 3. 测试Whisper设备初始化")
    print("-" * 30)
    
    devices_to_test = ["auto", "cpu"]
    
    # 如果CUDA可用，添加cuda测试
    try:
        import torch
        if torch.cuda.is_available():
            devices_to_test.append("cuda")
    except ImportError:
        pass
    
    for device in devices_to_test:
        print(f"\n测试设备: {device}")
        try:
            # 创建设备配置
            device_config = {
                'preferred_device': device,
                'cuda': {
                    'enabled': True,
                    'device_id': -1,
                    'memory_fraction': 0,
                    'allow_growth': True
                },
                'cpu': {
                    'num_threads': 0,
                    'optimize': True
                }
            }
            
            # 初始化Whisper（不加载模型，只测试设备选择）
            transcriber = WhisperTranscriber(
                model_size="tiny",  # 使用最小模型测试
                device=device,
                device_config=device_config
            )
            
            print(f"  ✅ {device} 初始化成功")
            print(f"  实际使用设备: {transcriber.device}")
            
            # 清理
            transcriber.cleanup()
            
        except Exception as e:
            print(f"  ❌ {device} 初始化失败: {str(e)}")

def test_config_override():
    """测试配置覆盖功能"""
    
    print("\n⚙️ 4. 测试配置覆盖")
    print("-" * 30)
    
    # 测试通过代码覆盖配置
    custom_device_config = {
        'preferred_device': 'cpu',
        'cpu': {
            'num_threads': 4,
            'optimize': True
        },
        'cuda': {
            'enabled': False
        }
    }
    
    try:
        transcriber = WhisperTranscriber(
            model_size="tiny",
            device="cpu",  # 强制使用CPU
            device_config=custom_device_config
        )
        
        print("✅ 自定义配置应用成功")
        print(f"使用设备: {transcriber.device}")
        
        transcriber.cleanup()
        
    except Exception as e:
        print(f"❌ 自定义配置测试失败: {str(e)}")

def show_usage_examples():
    """显示使用示例"""
    
    print("\n💡 5. 使用示例")
    print("-" * 30)
    
    print("""
# 命令行使用:
python main.py transcribe video.mp4 --device cuda    # 强制使用CUDA
python main.py transcribe video.mp4 --device cpu     # 强制使用CPU
python main.py transcribe video.mp4 --device auto    # 自动检测

# 代码使用:
from src.utils.whisper_transcriber import WhisperTranscriber

# 自动检测设备
transcriber = WhisperTranscriber(model_size="base")

# 强制使用CPU
transcriber = WhisperTranscriber(model_size="base", device="cpu")

# 使用自定义设备配置
device_config = {
    'preferred_device': 'cuda',
    'cuda': {
        'enabled': True,
        'device_id': 0,  # 使用第一个GPU
        'allow_growth': True
    }
}
transcriber = WhisperTranscriber(
    model_size="base", 
    device_config=device_config
)
    """)

if __name__ == "__main__":
    try:
        # 运行测试
        config_test = test_device_config()
        detection_test = test_device_detection()
        
        if config_test and detection_test:
            test_whisper_with_different_devices()
            test_config_override()
            show_usage_examples()
            
            print("\n🎉 设备配置测试完成！")
            print("\n📝 配置文件说明:")
            print("  在 config.yaml 中可以配置:")
            print("  - whisper.device_config.preferred_device: auto/cuda/cpu")
            print("  - whisper.device_config.cuda.enabled: true/false") 
            print("  - whisper.device_config.cuda.device_id: GPU设备ID")
            print("  - whisper.device_config.cpu.num_threads: CPU线程数")
        else:
            print("\n❌ 基础检查失败，请检查环境配置")
            
    except Exception as e:
        print(f"\n❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()