#!/usr/bin/env python3
"""
简化的Whisper优化使用示例
展示如何在您的项目中使用优化后的Whisper配置
"""

import os
import sys
import time
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.whisper_transcriber import WhisperTranscriber

def demo_chinese_optimization():
    """演示中文优化效果"""
    print("🎯 AiSub Whisper中文优化演示")
    print("=" * 50)
    
    # 创建转录器实例
    print("📥 加载Whisper模型...")
    transcriber = WhisperTranscriber(model_size="base", device="auto")
    
    print("✅ 模型加载完成！")
    print("\n🔍 可用的预设配置:")
    
    # 显示中文优化配置
    chinese_config = WhisperTranscriber.get_chinese_optimized_config()
    print("\n🇨🇳 中文优化配置:")
    print(f"   语言: {chinese_config['language']}")
    print(f"   上下文关联: {chinese_config['condition_on_previous_text']}")
    print(f"   搜索质量: beam_size={chinese_config['beam_size']}, best_of={chinese_config['best_of']}")
    print(f"   语音检测阈值: {chinese_config['no_speech_threshold']}")
    print(f"   初始提示: {chinese_config['initial_prompt'][:30]}...")
    
    # 显示速度优化配置
    speed_config = WhisperTranscriber.get_speed_optimized_config()
    print("\n⚡ 速度优化配置:")
    print(f"   语言: {speed_config['language']}")
    print(f"   上下文关联: {speed_config['condition_on_previous_text']}")
    print(f"   初始提示: {'无' if not speed_config['initial_prompt'] else speed_config['initial_prompt']}")
    print(f"   语音检测阈值: {speed_config['no_speech_threshold']}")
    
    print("\n💡 使用方法:")
    print("""
# 方法1: 使用便利方法
result = transcriber.transcribe_with_chinese_optimization("audio.wav")

# 方法2: 使用配置字典
config = WhisperTranscriber.get_chinese_optimized_config()
result = transcriber.transcribe_audio("audio.wav", **config)

# 方法3: 覆盖特定参数
result = transcriber.transcribe_with_chinese_optimization(
    "audio.wav", 
    beam_size=3,  # 降低搜索质量换取速度
    patience=0.5  # 减少耐心参数
)
    """)
    
    # 清理资源
    transcriber.cleanup()
    print("🎉 演示完成！")

def create_test_audio_guide():
    """创建测试音频指南"""
    print("\n📋 测试音频准备指南")
    print("=" * 40)
    print("""
🎵 音频要求:
- 格式: WAV, MP3, FLAC, M4A
- 时长: 10-60秒（测试推荐）
- 内容: 清晰的中文对话或朗读
- 质量: 尽量减少背景噪音

📁 获取测试音频的方式:
1. 录制一段中文语音
2. 从视频中提取音频片段
3. 使用文本转语音工具生成
4. 下载公开的中文音频素材

🔧 使用FFmpeg提取音频:
ffmpeg -i video.mp4 -ss 00:01:30 -t 00:00:30 -vn -acodec pcm_s16le -ar 16000 test_audio.wav

⚡ 快速测试命令:
python examples/simple_whisper_demo.py
python test_whisper_optimization.py <音频文件> --model base
    """)

if __name__ == "__main__":
    print("🎬 AiSub Whisper优化集成完成！")
    print("=" * 60)
    
    try:
        demo_chinese_optimization()
        create_test_audio_guide()
        
        print(f"\n✅ 优化已成功集成到您的项目中！")
        print("\n🎯 主要改进:")
        print("   ✅ 中文语音识别优化")
        print("   ✅ 上下文连贯性提升") 
        print("   ✅ 精准标点符号处理")
        print("   ✅ 智能噪音抑制")
        print("   ✅ 便利的预设配置方法")
        
        print("\n📝 下一步:")
        print("   1. 准备测试音频文件")
        print("   2. 运行: python test_whisper_optimization.py <音频文件>")
        print("   3. 查看优化效果对比")
        print("   4. 根据需要调整配置参数")
        
    except Exception as e:
        print(f"❌ 演示过程出错: {str(e)}")
        print("💡 请确保已正确安装所有依赖并配置好Whisper模型")