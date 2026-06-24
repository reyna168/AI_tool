#!/usr/bin/env python3
"""
AiSub API 使用示例
演示如何在您的 Python 项目中集成 AiSub
"""

import os
import sys
from typing import List, Dict, Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.aisub_app import AiSubApplication
from src.utils import WhisperTranscriber, FFmpegWrapper, SRTGenerator


class AiSubAPI:
    """AiSub API 封装类，方便在其他项目中使用"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 AiSub API
        
        Args:
            config_path: 配置文件路径
        """
        self.app = AiSubApplication(config_path)
    
    def transcribe_video(
        self, 
        video_path: str, 
        output_path: Optional[str] = None,
        language: Optional[str] = None,
        model_size: Optional[str] = None
    ) -> Dict[str, str]:
        """
        转录视频并生成字幕
        
        Args:
            video_path: 视频文件路径
            output_path: 输出字幕文件路径
            language: 强制指定语言
            model_size: Whisper 模型大小
            
        Returns:
            包含结果信息的字典
        """
        try:
            # 临时修改模型大小
            if model_size:
                self.app.config.config.setdefault('whisper', {})['model_size'] = model_size
            
            subtitle_path = self.app.process_video(video_path, output_path, language)
            
            return {
                'status': 'success',
                'subtitle_path': subtitle_path,
                'video_path': video_path,
                'message': '字幕生成成功'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'video_path': video_path,
                'message': '字幕生成失败'
            }
    
    def batch_transcribe(
        self, 
        video_paths: List[str],
        output_dir: Optional[str] = None,
        language: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        批量转录视频
        
        Args:
            video_paths: 视频文件路径列表
            output_dir: 输出目录
            language: 强制指定语言
            
        Returns:
            结果列表
        """
        results = []
        
        for video_path in video_paths:
            # 生成输出路径
            if output_dir:
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                output_path = os.path.join(output_dir, f"{video_name}.srt")
            else:
                output_path = None
            
            result = self.transcribe_video(video_path, output_path, language)
            results.append(result)
        
        return results
    
    def get_video_info(self, video_path: str) -> Dict:
        """
        获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            视频信息字典
        """
        try:
            if not self.app.ffmpeg:
                self.app.initialize_components()
            
            return self.app.ffmpeg.get_video_info(video_path)
            
        except Exception as e:
            return {'error': str(e)}
    
    def estimate_processing_time(self, video_path: str, model_size: str = "base") -> Dict:
        """
        估算处理时间
        
        Args:
            video_path: 视频文件路径
            model_size: 模型大小
            
        Returns:
            估算信息字典
        """
        try:
            video_info = self.get_video_info(video_path)
            if 'error' in video_info:
                return video_info
            
            duration = video_info['duration']
            estimated_time = WhisperTranscriber.estimate_processing_time(duration, model_size)
            
            return {
                'video_duration': duration,
                'estimated_time': estimated_time,
                'model_size': model_size
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def validate_subtitle(self, srt_path: str) -> Dict:
        """
        验证字幕文件
        
        Args:
            srt_path: SRT 文件路径
            
        Returns:
            验证结果字典
        """
        return self.app.srt_generator.validate_srt_file(srt_path)
    
    def cleanup(self):
        """清理资源"""
        self.app.cleanup()


def api_basic_example():
    """API 基本使用示例"""
    print("🎯 AiSub API 基本使用示例")
    print("=" * 50)
    
    # 创建 API 实例
    api = AiSubAPI()
    
    video_path = "example.mp4"
    
    if not os.path.exists(video_path):
        print(f"⚠️  示例视频文件不存在: {video_path}")
        print("请准备一个测试视频文件")
        return
    
    try:
        # 获取视频信息
        print("📊 获取视频信息...")
        video_info = api.get_video_info(video_path)
        print(f"   时长: {video_info.get('duration', 0):.1f} 秒")
        print(f"   大小: {video_info.get('size', 0) / 1024 / 1024:.1f} MB")
        
        # 估算处理时间
        print("\n⏱️  估算处理时间...")
        estimate = api.estimate_processing_time(video_path, "base")
        print(f"   预计时间: {estimate.get('estimated_time', 0):.1f} 秒")
        
        # 转录视频
        print("\n🎬 开始转录...")
        result = api.transcribe_video(video_path, language="auto")
        
        if result['status'] == 'success':
            print(f"✅ {result['message']}")
            print(f"📄 字幕文件: {result['subtitle_path']}")
            
            # 验证字幕
            validation = api.validate_subtitle(result['subtitle_path'])
            if validation['valid']:
                print(f"📊 字幕验证: {validation['subtitle_count']} 个字幕项")
        else:
            print(f"❌ {result['message']}: {result['error']}")
    
    finally:
        api.cleanup()


def api_batch_example():
    """API 批量处理示例"""
    print("\n🎯 AiSub API 批量处理示例")
    print("=" * 50)
    
    # 创建 API 实例
    api = AiSubAPI()
    
    # 假设的视频文件列表
    video_files = [
        "video1.mp4",
        "video2.mp4", 
        "video3.mp4"
    ]
    
    # 过滤存在的文件
    existing_files = [f for f in video_files if os.path.exists(f)]
    
    if not existing_files:
        print("⚠️  没有找到测试视频文件")
        print("请准备一些视频文件进行测试")
        return
    
    print(f"📁 找到 {len(existing_files)} 个视频文件")
    
    try:
        # 批量处理
        output_dir = "batch_output"
        os.makedirs(output_dir, exist_ok=True)
        
        results = api.batch_transcribe(existing_files, output_dir, language="auto")
        
        # 统计结果
        success_count = sum(1 for r in results if r['status'] == 'success')
        
        print(f"\n📊 批量处理结果:")
        print(f"   总数: {len(results)}")
        print(f"   成功: {success_count}")
        print(f"   失败: {len(results) - success_count}")
        
        # 显示详细结果
        for result in results:
            status_icon = "✅" if result['status'] == 'success' else "❌"
            video_name = os.path.basename(result['video_path'])
            print(f"   {status_icon} {video_name}: {result['message']}")
    
    finally:
        api.cleanup()


def api_advanced_example():
    """API 高级使用示例"""
    print("\n🎯 AiSub API 高级使用示例")
    print("=" * 50)
    
    # 创建带自定义配置的 API 实例
    api = AiSubAPI("config.yaml")
    
    video_path = "advanced_example.mp4"
    
    if not os.path.exists(video_path):
        print(f"⚠️  示例视频文件不存在: {video_path}")
        return
    
    try:
        # 使用不同模型进行对比
        models = ["tiny", "base", "small"]
        results = {}
        
        for model in models:
            print(f"\n🤖 使用模型: {model}")
            
            import time
            start_time = time.time()
            
            result = api.transcribe_video(
                video_path, 
                output_path=f"subtitle_{model}.srt",
                model_size=model
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            if result['status'] == 'success':
                validation = api.validate_subtitle(result['subtitle_path'])
                results[model] = {
                    'time': processing_time,
                    'subtitles': validation.get('subtitle_count', 0),
                    'valid': validation.get('valid', False)
                }
                print(f"   ✅ 成功: {processing_time:.1f}s, {validation.get('subtitle_count', 0)} 字幕")
            else:
                print(f"   ❌ 失败: {result['error']}")
        
        # 显示对比结果
        if results:
            print(f"\n📊 模型对比结果:")
            print(f"{'模型':<10} {'时间(s)':<10} {'字幕数':<10} {'状态'}")
            print("-" * 40)
            for model, data in results.items():
                status = "✅" if data['valid'] else "❌"
                print(f"{model:<10} {data['time']:<10.1f} {data['subtitles']:<10} {status}")
    
    finally:
        api.cleanup()


def integration_example():
    """集成示例 - 展示如何在现有项目中使用"""
    print("\n🎯 项目集成示例")
    print("=" * 50)
    
    class VideoProcessor:
        """示例：视频处理类，集成了 AiSub"""
        
        def __init__(self):
            self.aisub = AiSubAPI()
        
        def process_uploaded_video(self, video_path: str, user_id: str) -> Dict:
            """处理用户上传的视频"""
            try:
                # 1. 验证视频文件
                if not os.path.exists(video_path):
                    return {'success': False, 'error': '视频文件不存在'}
                
                # 2. 获取视频信息
                video_info = self.aisub.get_video_info(video_path)
                if 'error' in video_info:
                    return {'success': False, 'error': '无法读取视频信息'}
                
                # 3. 检查视频时长限制
                max_duration = 3600  # 1小时
                if video_info['duration'] > max_duration:
                    return {'success': False, 'error': '视频时长超过限制'}
                
                # 4. 生成字幕
                output_path = f"user_{user_id}_subtitle.srt"
                result = self.aisub.transcribe_video(video_path, output_path)
                
                if result['status'] == 'success':
                    # 5. 验证字幕质量
                    validation = self.aisub.validate_subtitle(result['subtitle_path'])
                    
                    return {
                        'success': True,
                        'subtitle_path': result['subtitle_path'],
                        'video_info': video_info,
                        'subtitle_count': validation.get('subtitle_count', 0)
                    }
                else:
                    return {'success': False, 'error': result['error']}
                    
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        def cleanup(self):
            self.aisub.cleanup()
    
    # 示例使用
    processor = VideoProcessor()
    
    try:
        result = processor.process_uploaded_video("test_video.mp4", "user123")
        
        if result['success']:
            print("✅ 视频处理成功")
            print(f"📄 字幕文件: {result['subtitle_path']}")
            print(f"📊 字幕数量: {result['subtitle_count']}")
        else:
            print(f"❌ 视频处理失败: {result['error']}")
    
    finally:
        processor.cleanup()


def main():
    """主函数"""
    print("🎯 AiSub API 使用示例")
    print("=" * 60)
    
    examples = [
        ("1. 基本 API 使用", api_basic_example),
        ("2. 批量处理 API", api_batch_example),
        ("3. 高级 API 功能", api_advanced_example),
        ("4. 项目集成示例", integration_example),
    ]
    
    print("可用的示例:")
    for name, _ in examples:
        print(f"   {name}")
    print("   0. 运行所有示例")
    
    try:
        choice = input("\n请选择要运行的示例 (0-4): ").strip()
        
        if choice == "0":
            for name, example_func in examples:
                try:
                    example_func()
                except Exception as e:
                    print(f"❌ 示例 {name} 运行失败: {str(e)}")
        elif choice in ["1", "2", "3", "4"]:
            index = int(choice) - 1
            name, example_func = examples[index]
            example_func()
        else:
            print("无效选择")
    
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"❌ 运行失败: {str(e)}")


if __name__ == "__main__":
    main()