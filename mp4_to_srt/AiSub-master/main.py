#!/usr/bin/env python3
"""
AiSub 命令行界面
视频字幕生成器命令行工具
"""

import os
import sys
import click
import logging
from pathlib import Path
from typing import Optional

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.aisub_app import AiSubApplication


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    AiSub - AI 视频字幕生成器
    
    使用 FFmpeg 和 Whisper 为视频生成高质量字幕
    """
    pass


@cli.command()
@click.argument('video_path', type=click.Path(exists=True))
@click.option(
    '--output', '-o', 
    type=click.Path(),
    help='输出字幕文件路径'
)
@click.option(
    '--language', '-l',
    type=str,
    help='强制指定语言代码 (如: zh, en, ja, ko)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='配置文件路径'
)
@click.option(
    '--model', '-m',
    type=click.Choice(['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']),
    help='Whisper 模型大小'
)
@click.option(
    '--device',
    type=click.Choice(['auto', 'cuda', 'cpu']),
    default='auto',
    help='计算设备 (auto=自动检测, cuda=NVIDIA GPU, cpu=CPU)'
)
@click.option(
    '--engine', '-e',
    type=click.Choice(['whisper', 'gemini', 'openai']),
    help='指定转录引擎（默认使用本地 Whisper）'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='显示详细输出'
)
def transcribe(
    video_path: str,
    output: Optional[str],
    language: Optional[str],
    config: Optional[str],
    model: Optional[str],
    device: str,
    engine: Optional[str],
    verbose: bool
):
    """
    转录视频文件并生成 SRT 字幕
    
    VIDEO_PATH: 要处理的视频文件路径
    """
    try:
        # 设置日志级别
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        click.echo(f"🎬 AiSub - 开始处理视频: {video_path}")
        
        # 验证视频文件
        if not os.path.exists(video_path):
            click.echo(f"❌ 错误: 视频文件不存在: {video_path}", err=True)
            sys.exit(1)
        
        # 创建应用实例
        app = AiSubApplication(config, external_engine=engine)
        
        # 显示可用的转录引擎
        if verbose and hasattr(app, 'external_transcriber_manager') and app.external_transcriber_manager:
            available_engines = app.external_transcriber_manager.get_available_engines()
            click.echo(f"🚀 可用的转录引擎: {', '.join(available_engines)}")
            if engine:
                click.echo(f"🎯 指定使用引擎: {engine}")
        
        # 验证视频格式
        if not app.validate_video_file(video_path):
            click.echo(f"❌ 错误: 不支持的视频格式", err=True)
            supported_formats = ', '.join(app.get_supported_video_formats())
            click.echo(f"支持的格式: {supported_formats}", err=True)
            sys.exit(1)
        
        # 显示状态信息
        if verbose:
            status = app.get_status_info()
            click.echo(f"📋 状态信息:")
            click.echo(f"   配置已加载: {status['config_loaded']}")
            click.echo(f"   设备: {device}")
            if model:
                click.echo(f"   模型: {model}")
        
        # 临时修改配置
        if model:
            app.config.config.setdefault('whisper', {})['model_size'] = model
        if device != 'auto':
            # 支持新的设备配置格式
            whisper_config = app.config.config.setdefault('whisper', {})
            # 兼容旧格式
            whisper_config['device'] = device
            # 同时更新新格式
            device_config = whisper_config.setdefault('device_config', {})
            device_config['preferred_device'] = device
            
            click.echo(f"💻 设置计算设备: {device}")
        
        # 处理视频
        with click.progressbar(length=100, label='处理进度') as bar:
            try:
                subtitle_path = app.process_video(
                    video_path=video_path,
                    output_path=output,
                    language=language
                )
                bar.update(100)
                
                click.echo(f"\n✅ 字幕生成完成!")
                click.echo(f"📄 字幕文件: {subtitle_path}")
                
                # 显示文件信息
                if os.path.exists(subtitle_path):
                    file_size = os.path.getsize(subtitle_path)
                    click.echo(f"📊 文件大小: {file_size:,} 字节")
                
            except Exception as e:
                bar.update(100)
                raise e
        
    except KeyboardInterrupt:
        click.echo("\n⚠️  用户中断操作", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ 处理失败: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='配置文件路径'
)
def info(config: Optional[str]):
    """显示系统信息和可用模型"""
    try:
        click.echo("🔍 AiSub 系统信息")
        click.echo("=" * 50)
        
        # 创建应用实例
        app = AiSubApplication(config)
        
        # 显示配置信息
        click.echo(f"📁 配置文件: {app.config.config_path}")
        
        # 显示支持的视频格式
        formats = app.get_supported_video_formats()
        click.echo(f"🎬 支持的视频格式: {', '.join(formats)}")
        
        # 显示 Whisper 模型信息
        click.echo("\n🤖 可用的 Whisper 模型:")
        models = app.whisper.list_available_models() if app.whisper else {}
        if not models:
            from src.utils.whisper_transcriber import WhisperTranscriber
            models = WhisperTranscriber.list_available_models()
        
        for model_name, info in models.items():
            click.echo(f"   {model_name:12} - 参数: {info['params']:>8}, 显存: {info['vram']:>6}, 速度: {info['speed']}")
        
        # 检查 GPU 可用性
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            click.echo(f"\n🖥️  设备信息:")
            click.echo(f"   CUDA 可用: {'是' if cuda_available else '否'}")
            
            if cuda_available:
                gpu_count = torch.cuda.device_count()
                click.echo(f"   GPU 数量: {gpu_count}")
                for i in range(gpu_count):
                    gpu_name = torch.cuda.get_device_name(i)
                    memory = torch.cuda.get_device_properties(i).total_memory / 1024**3
                    click.echo(f"   GPU {i}: {gpu_name} ({memory:.1f} GB)")
                    
                # 显示当前设备配置
                device_config = app.config.get_device_config()
                preferred_device = device_config.get('preferred_device', 'auto')
                click.echo(f"   首选设备: {preferred_device}")
                
                cuda_config = device_config.get('cuda', {})
                if cuda_config.get('enabled', True):
                    click.echo(f"   CUDA 配置: 已启用")
                    device_id = cuda_config.get('device_id', -1)
                    if device_id >= 0:
                        click.echo(f"     指定设备: GPU {device_id}")
                    click.echo(f"     内存增长: {'已启用' if cuda_config.get('allow_growth', True) else '已禁用'}")
            else:
                # 检查AMD GPU
                try:
                    import subprocess
                    result = subprocess.run(['rocm-smi'], capture_output=True, text=True, timeout=3)
                    if result.returncode == 0:
                        click.echo("   AMD GPU: 检测到（但Whisper不支持ROCm）")
                except:
                    pass
                    
                click.echo("   建议: 使用CPU模式或安装CUDA")
                
        except ImportError:
            click.echo("\n🖥️  PyTorch 未安装，无法检查 GPU")
        
        # 检查 FFmpeg
        try:
            app.initialize_components()
            click.echo("\n🎞️  FFmpeg: 可用")
        except Exception as e:
            click.echo(f"\n🎞️  FFmpeg: 不可用 ({str(e)})")
        
        click.echo("\n✅ 系统信息检查完成")
        
    except Exception as e:
        click.echo(f"❌ 获取系统信息失败: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('video_path', type=click.Path(exists=True))
@click.option(
    '--model', '-m',
    type=click.Choice(['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']),
    default='base',
    help='使用的模型大小'
)
def estimate(video_path: str, model: str):
    """估算视频处理时间"""
    try:
        click.echo(f"⏱️  估算处理时间: {video_path}")
        
        # 创建应用实例
        app = AiSubApplication()
        app.initialize_components()
        
        # 获取视频信息
        video_info = app.ffmpeg.get_video_info(video_path)
        duration = video_info['duration']
        
        click.echo(f"📊 视频信息:")
        click.echo(f"   时长: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")
        click.echo(f"   大小: {video_info['size'] / 1024 / 1024:.1f} MB")
        
        # 估算处理时间
        from src.utils.whisper_transcriber import WhisperTranscriber
        estimated_time = WhisperTranscriber.estimate_processing_time(duration, model)
        
        click.echo(f"\n⏱️  预计处理时间 (模型: {model}):")
        click.echo(f"   估算时间: {estimated_time:.1f} 秒 ({estimated_time/60:.1f} 分钟)")
        
        if estimated_time > 3600:
            click.echo(f"   约 {estimated_time/3600:.1f} 小时")
        
        # 给出建议
        if duration > 1800:  # 30 分钟
            click.echo(f"\n💡 建议:")
            click.echo(f"   - 长视频建议使用 'small' 或更大的模型以获得更好效果")
            click.echo(f"   - 如果有 GPU，处理速度会显著提升")
        
    except Exception as e:
        click.echo(f"❌ 估算失败: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('srt_path', type=click.Path(exists=True))
def validate(srt_path: str):
    """验证 SRT 字幕文件"""
    try:
        click.echo(f"🔍 验证字幕文件: {srt_path}")
        
        from src.utils.srt_generator import SRTGenerator
        srt_gen = SRTGenerator()
        
        result = srt_gen.validate_srt_file(srt_path)
        
        if result['valid']:
            click.echo("✅ 字幕文件有效")
            click.echo(f"📊 统计信息:")
            click.echo(f"   字幕数量: {result['subtitle_count']}")
            click.echo(f"   总时长: {result['total_duration']:.1f} 秒")
        else:
            click.echo("❌ 字幕文件无效")
            for error in result['errors']:
                click.echo(f"   错误: {error}")
        
    except Exception as e:
        click.echo(f"❌ 验证失败: {str(e)}", err=True)
        sys.exit(1)


def main():
    """主函数"""
    try:
        cli()
    except Exception as e:
        click.echo(f"❌ 程序异常: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()