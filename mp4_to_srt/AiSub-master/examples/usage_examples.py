#!/usr/bin/env python3
"""
AiSub 简单使用示例
演示如何通过 Python 代码使用 AiSub
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.aisub_app import AiSubApplication


def basic_example():
    """基本使用示例"""
    print("🎬 AiSub 基本使用示例")
    print("=" * 50)
    
    # 创建应用实例
    app = AiSubApplication()
    
    # 假设的视频文件路径 (请替换为实际文件)
    video_path = "example_video.mp4"
    
    # 检查文件是否存在
    if not os.path.exists(video_path):
        print(f"⚠️  示例视频文件不存在: {video_path}")
        print("请将您的视频文件重命名为 'example_video.mp4' 或修改此脚本中的路径")
        return
    
    try:
        # 处理视频
        print(f"📝 开始处理视频: {video_path}")
        subtitle_path = app.process_video(video_path)
        
        print(f"✅ 字幕生成成功!")
        print(f"📄 字幕文件: {subtitle_path}")
        
        # 验证字幕文件
        validation_result = app.srt_generator.validate_srt_file(subtitle_path)
        if validation_result['valid']:
            print(f"📊 字幕信息: {validation_result['subtitle_count']} 个字幕项")
        
    except Exception as e:
        print(f"❌ 处理失败: {str(e)}")
    finally:
        # 清理资源
        app.cleanup()


def batch_processing_example():
    """批量处理示例"""
    print("\n🎬 AiSub 批量处理示例")
    print("=" * 50)
    
    # 视频文件目录
    video_dir = "videos"
    output_dir = "output"
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 检查视频目录
    if not os.path.exists(video_dir):
        print(f"⚠️  视频目录不存在: {video_dir}")
        print("请创建 'videos' 目录并放入要处理的视频文件")
        return
    
    # 获取视频文件列表
    video_files = []
    supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    
    for file in os.listdir(video_dir):
        if any(file.lower().endswith(fmt) for fmt in supported_formats):
            video_files.append(file)
    
    if not video_files:
        print(f"⚠️  在 {video_dir} 目录中未找到支持的视频文件")
        print(f"支持的格式: {', '.join(supported_formats)}")
        return
    
    print(f"📁 找到 {len(video_files)} 个视频文件")
    
    # 创建应用实例
    app = AiSubApplication()
    
    # 处理每个视频文件
    success_count = 0
    for i, video_file in enumerate(video_files, 1):
        video_path = os.path.join(video_dir, video_file)
        video_name = Path(video_file).stem
        output_path = os.path.join(output_dir, f"{video_name}.srt")
        
        print(f"\n[{i}/{len(video_files)}] 处理: {video_file}")
        
        try:
            app.process_video(video_path, output_path)
            print(f"✅ 成功: {output_path}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ 失败: {str(e)}")
    
    print(f"\n📊 批量处理完成: {success_count}/{len(video_files)} 成功")
    
    # 清理资源
    app.cleanup()


def custom_config_example():
    """自定义配置示例"""
    print("\n🎬 AiSub 自定义配置示例")
    print("=" * 50)
    
    # 使用自定义配置文件
    config_path = "custom_config.yaml"
    
    # 创建自定义配置文件（如果不存在）
    if not os.path.exists(config_path):
        custom_config = """
# 自定义配置示例
whisper:
  model_size: "small"  # 使用更高质量的模型
  device: "auto"
  transcription:
    language: "zh"  # 强制中文识别
    temperature: 0.0

subtitle:
  max_line_length: 60  # 更短的行长度
  max_lines_per_subtitle: 2
  encoding: "utf-8"

processing:
  split_long_audio: true
  segment_length: 180  # 3分钟分段
  cleanup_temp_files: true

output:
  default_output_dir: "./custom_output"
"""
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(custom_config)
        print(f"📝 创建了自定义配置文件: {config_path}")
    
    # 使用自定义配置创建应用实例
    app = AiSubApplication(config_path)
    
    print("⚙️  使用自定义配置:")
    print(f"   模型: {app.config.get('whisper.model_size')}")
    print(f"   语言: {app.config.get('whisper.transcription.language')}")
    print(f"   输出目录: {app.config.get('output.default_output_dir')}")
    
    # 这里可以继续处理视频...
    print("💡 配置已加载，可以继续处理视频")


def language_specific_example():
    """特定语言处理示例"""
    print("\n🎬 AiSub 多语言处理示例")
    print("=" * 50)
    
    app = AiSubApplication()
    
    # 不同语言的示例设置
    language_examples = [
        {"code": "zh", "name": "中文", "video": "chinese_video.mp4"},
        {"code": "en", "name": "英文", "video": "english_video.mp4"},
        {"code": "ja", "name": "日文", "video": "japanese_video.mp4"},
        {"code": "ko", "name": "韩文", "video": "korean_video.mp4"},
    ]
    
    for lang_info in language_examples:
        lang_code = lang_info["code"]
        lang_name = lang_info["name"]
        video_file = lang_info["video"]
        
        print(f"\n🌍 {lang_name} 处理示例:")
        print(f"   语言代码: {lang_code}")
        print(f"   示例文件: {video_file}")
        
        if os.path.exists(video_file):
            try:
                output_path = f"subtitle_{lang_code}.srt"
                app.process_video(video_file, output_path, language=lang_code)
                print(f"   ✅ 生成字幕: {output_path}")
            except Exception as e:
                print(f"   ❌ 处理失败: {str(e)}")
        else:
            print(f"   ⚠️  文件不存在，跳过处理")
    
    app.cleanup()


def model_comparison_example():
    """模型对比示例"""
    print("\n🎬 AiSub 模型对比示例")
    print("=" * 50)
    
    test_video = "test_video.mp4"
    
    if not os.path.exists(test_video):
        print(f"⚠️  测试视频不存在: {test_video}")
        print("请准备一个测试视频文件")
        return
    
    # 不同模型的对比
    models = ["tiny", "base", "small"]
    
    for model in models:
        print(f"\n🤖 测试模型: {model}")
        
        try:
            # 为每个模型创建单独的应用实例
            app = AiSubApplication()
            
            # 临时修改配置
            app.config.config.setdefault('whisper', {})['model_size'] = model
            
            # 处理视频
            import time
            start_time = time.time()
            
            output_path = f"subtitle_{model}.srt"
            app.process_video(test_video, output_path)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 验证结果
            validation = app.srt_generator.validate_srt_file(output_path)
            
            print(f"   ✅ 处理完成")
            print(f"   ⏱️  处理时间: {processing_time:.1f} 秒")
            print(f"   📊 字幕数量: {validation['subtitle_count']}")
            
            app.cleanup()
            
        except Exception as e:
            print(f"   ❌ 处理失败: {str(e)}")


def main():
    """主函数 - 运行所有示例"""
    print("🎬 AiSub 使用示例集合")
    print("=" * 60)
    
    examples = [
        ("1. 基本使用", basic_example),
        ("2. 批量处理", batch_processing_example),
        ("3. 自定义配置", custom_config_example),
        ("4. 多语言处理", language_specific_example),
        ("5. 模型对比", model_comparison_example),
    ]
    
    print("请选择要运行的示例:")
    for i, (name, _) in enumerate(examples):
        print(f"   {name}")
    print("   0. 运行所有示例")
    
    try:
        choice = input("\n请输入选择 (0-5): ").strip()
        
        if choice == "0":
            # 运行所有示例
            for name, example_func in examples:
                print(f"\n{'='*20} {name} {'='*20}")
                try:
                    example_func()
                except KeyboardInterrupt:
                    print("\n⚠️  用户中断")
                    break
                except Exception as e:
                    print(f"❌ 示例运行失败: {str(e)}")
        
        elif choice in ["1", "2", "3", "4", "5"]:
            # 运行选定的示例
            index = int(choice) - 1
            name, example_func = examples[index]
            print(f"\n{'='*20} {name} {'='*20}")
            example_func()
        
        else:
            print("无效选择")
    
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"❌ 运行失败: {str(e)}")


if __name__ == "__main__":
    main()