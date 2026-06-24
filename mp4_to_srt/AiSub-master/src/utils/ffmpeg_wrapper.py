"""
FFmpeg 包装器模块
用于处理视频文件和提取音频
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import ffmpeg
from tqdm import tqdm


class FFmpegWrapper:
    """FFmpeg 包装器类，用于视频处理和音频提取"""
    
    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        初始化 FFmpeg 包装器
        
        Args:
            ffmpeg_path: FFmpeg 可执行文件路径，如果为 None 则使用系统 PATH
        """
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"
        self.logger = logging.getLogger(__name__)
        
        # 检查 FFmpeg 是否可用
        self._check_ffmpeg_availability()
    
    def _check_ffmpeg_availability(self) -> None:
        """检查 FFmpeg 是否可用"""
        # 尝试多个可能的FFmpeg路径
        possible_paths = [
            self.ffmpeg_path,
            "ffmpeg",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
            # WinGet安装路径
            os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\BtbN.FFmpeg.GPL_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg.exe"),
            os.path.expanduser(r"~\scoop\apps\ffmpeg\current\bin\ffmpeg.exe"),
        ]
        
        for path in possible_paths:
            if path:
                try:
                    result = subprocess.run(
                        [path, "-version"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        encoding='utf-8',
                        errors='ignore'
                    )
                    if result.returncode == 0:
                        self.ffmpeg_path = path
                        self.logger.info(f"FFmpeg 找到: {path}")
                        return
                except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                    continue
        
        # 如果都找不到，显示详细错误信息
        error_msg = (
            "FFmpeg 不可用。请安装 FFmpeg：\n"
            "1. 重启命令行窗口（如果刚安装）\n"
            "2. 或访问 https://ffmpeg.org/download.html 手动安装\n"
            "3. 或运行: winget install --id BtbN.FFmpeg.GPL"
        )
        self.logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def get_audio_info(self, audio_path: str) -> dict:
        """
        获取音频文件信息
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            包含音频信息的字典
        """
        try:
            probe = ffmpeg.probe(audio_path)
            
            # 获取音频流信息
            audio_info = next(
                stream for stream in probe['streams'] 
                if stream['codec_type'] == 'audio'
            )
            
            info = {
                'duration': float(probe['format']['duration']),
                'size': int(probe['format']['size']),
                'audio': {
                    'codec': audio_info['codec_name'],
                    'sample_rate': int(audio_info['sample_rate']),
                    'channels': int(audio_info['channels']),
                    'bit_rate': int(audio_info.get('bit_rate', 0))
                }
            }
            
            return info
            
        except Exception as e:
            error_msg = f"获取音频信息失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def get_video_info(self, video_path: str) -> dict:
        """
        获取视频文件信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            包含视频信息的字典
        """
        try:
            probe = ffmpeg.probe(video_path)
            video_info = next(
                stream for stream in probe['streams'] 
                if stream['codec_type'] == 'video'
            )
            audio_info = next(
                (stream for stream in probe['streams'] 
                 if stream['codec_type'] == 'audio'), 
                None
            )
            
            info = {
                'duration': float(probe['format']['duration']),
                'size': int(probe['format']['size']),
                'video': {
                    'codec': video_info['codec_name'],
                    'width': int(video_info['width']),
                    'height': int(video_info['height']),
                    'fps': eval(video_info['r_frame_rate'])
                }
            }
            
            if audio_info:
                info['audio'] = {
                    'codec': audio_info['codec_name'],
                    'sample_rate': int(audio_info['sample_rate']),
                    'channels': int(audio_info['channels'])
                }
            
            return info
            
        except Exception as e:
            error_msg = f"获取视频信息失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def extract_audio(
        self, 
        video_path: str, 
        output_path: str, 
        audio_format: str = "wav",
        sample_rate: int = 16000,
        channels: int = 1,
        show_progress: bool = True,
        preprocess_audio: bool = False
    ) -> str:
        """
        从视频中提取音频
        
        Args:
            video_path: 输入视频文件路径
            output_path: 输出音频文件路径
            audio_format: 音频格式 (wav, mp3, flac 等)
            sample_rate: 采样率 (默认 16000 Hz，适合语音识别)
            channels: 声道数 (默认 1 为单声道)
            show_progress: 是否显示进度条
            preprocess_audio: 是否启用音频预处理（降噪、人声增强）
            
        Returns:
            输出音频文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 直接使用视频文件获取时长用于进度显示
            # 这里的video_path实际是原始视频文件，不是音频文件
            probe = ffmpeg.probe(video_path)
            duration = float(probe['format']['duration'])
            
            self.logger.info(f"开始提取音频: {video_path} -> {output_path}")
            self.logger.info(f"音频格式: {audio_format}, 采样率: {sample_rate}Hz, 声道: {channels}")
            if preprocess_audio:
                self.logger.info("启用音频预处理: 降噪、人声增强")
            
            # 构建 FFmpeg 命令
            stream = ffmpeg.input(video_path)
            
            # 如果启用音频预处理
            if preprocess_audio:
                # 应用音频预处理滤镜
                stream = self._apply_audio_preprocessing(stream)
            
            stream = ffmpeg.output(
                stream,
                output_path,
                acodec='pcm_s16le' if audio_format.lower() == 'wav' else 'libmp3lame',
                ar=sample_rate,
                ac=channels,
                y=None  # 覆盖已存在的文件
            )
            
            # 执行命令
            if show_progress:
                self._run_ffmpeg_with_progress(stream, duration)
            else:
                ffmpeg.run(stream, quiet=True, overwrite_output=True)
            
            # 验证输出文件
            if not os.path.exists(output_path):
                raise RuntimeError("音频提取失败，输出文件不存在")
            
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                raise RuntimeError("音频提取失败，输出文件为空")
            
            self.logger.info(f"音频提取成功，文件大小: {file_size / 1024 / 1024:.2f} MB")
            return output_path
            
        except Exception as e:
            error_msg = f"音频提取失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _run_ffmpeg_with_progress(self, stream, total_duration: float) -> None:
        """
        运行 FFmpeg 并显示进度条
        
        Args:
            stream: FFmpeg 流对象
            total_duration: 总时长（秒）
        """
        cmd = ffmpeg.compile(stream, overwrite_output=True)
        
        # 调试：输出FFmpeg命令
        self.logger.info(f"执行FFmpeg命令: {' '.join(cmd)}")        
        
        with tqdm(
            total=total_duration,
            unit='s',
            unit_scale=True,
            desc="提取音频"
        ) as pbar:
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    # 解析 FFmpeg 输出中的时间信息
                    if 'time=' in output:
                        try:
                            time_str = output.split('time=')[1].split()[0]
                            time_parts = time_str.split(':')
                            if len(time_parts) == 3:
                                current_time = (
                                    float(time_parts[0]) * 3600 +
                                    float(time_parts[1]) * 60 +
                                    float(time_parts[2])
                                )
                                pbar.update(current_time - pbar.n)
                        except (IndexError, ValueError):
                            pass
            
            return_code = process.poll()
            if return_code != 0:
                # 获取所有错误输出
                stderr_output = []
                while True:
                    line = process.stderr.readline()
                    if not line:
                        break
                    stderr_output.append(line.strip())
                
                error_output = '\n'.join(stderr_output)
                if not error_output:
                    error_output = "未知错误，请检查FFmpeg命令和音频文件"
                
                raise RuntimeError(f"FFmpeg 执行失败 (exit code: {return_code}): {error_output}")
    
    def _apply_audio_preprocessing(self, stream):
        """
        应用音频预处理滤镜
        
        Args:
            stream: FFmpeg 输入流
            
        Returns:
            处理后的音频流
        """
        # 应用多种音频处理滤镜来优化人声
        filters = []
        
        # 1. 降噪滤镜 (afftdn) - 使用FFT降噪
        # nr: 降噪强度 0.01-1.0, nf: 噪声底限 -80到-20dB
        filters.append('afftdn=nr=0.12:nf=-40')
        
        # 2. 高通滤波器 - 移除低频噪音（如空调声、机械噪音）
        # 人声主要频率在 85Hz-255Hz 以上
        filters.append('highpass=f=85')
        
        # 3. 低通滤波器 - 移除高频噪音
        # 人声主要频率在 4000Hz 以下
        filters.append('lowpass=f=4000')
        
        # 4. 动态范围压缩 - 平衡音量，突出人声
        # threshold: 压缩阈值, ratio: 压缩比, attack: 攻击时间, release: 释放时间
        filters.append('acompressor=threshold=-18dB:ratio=3:attack=5:release=50')
        
        # 5. 音量标准化 - 自动调整音量到合适水平
        # I: 目标音量 (LUFS), LRA: 响度范围, tp: 真峰值限制
        filters.append('loudnorm=I=-16:LRA=11:tp=-1.5')
        
        # 6. 门限降噪 - 静音时完全静音，有声音时保持
        # level_in: 输入电平, mode: 模式, ratio: 压缩比, threshold: 阈值
        filters.append('agate=level_in=1:mode=downward:ratio=2:threshold=0.06:attack=20:release=250')
        
        # 将所有滤镜组合成一个滤镜链
        filter_chain = ','.join(filters)
        
        # 应用音频滤镜 - 使用正确的 API
        stream = stream.audio.filter('aresample', 16000).filter('af', filter_chain)
        
        return stream
    
    def preprocess_audio_file(
        self,
        input_path: str,
        output_path: str,
        noise_reduction: float = 0.12,
        voice_enhancement: bool = True,
        show_progress: bool = True
    ) -> str:
        """
        对音频文件进行预处理以优化人声
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出音频文件路径
            noise_reduction: 降噪强度 (0.01-1.0，越高降噪越强)
            voice_enhancement: 是否启用人声增强
            show_progress: 是否显示进度条
            
        Returns:
            处理后的音频文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 获取音频信息
            audio_info = self.get_audio_info(input_path)
            duration = audio_info['duration']
            
            self.logger.info(f"开始音频预处理: {input_path} -> {output_path}")
            self.logger.info(f"降噪强度: {noise_reduction}, 人声增强: {'开启' if voice_enhancement else '关闭'}")
            
            # 直接使用subprocess调用FFmpeg，避免ffmpeg-python库的问题
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-af', 'highpass=f=85,lowpass=f=4000' + (',volume=1.2' if voice_enhancement else ''),
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y', output_path
            ]
            
            self.logger.info(f"执行FFmpeg命令: {' '.join(cmd)}")
            
            # 执行命令
            if show_progress:
                self._run_subprocess_with_progress(cmd, duration)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg执行失败: {result.stderr}")
            
            # 验证输出文件
            if not os.path.exists(output_path):
                raise RuntimeError("音频预处理失败，输出文件不存在")
            
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                raise RuntimeError("音频预处理失败，输出文件为空")
            
            self.logger.info(f"音频预处理完成，文件大小: {file_size / 1024 / 1024:.2f} MB")
            return output_path
            
        except Exception as e:
            error_msg = f"音频预处理失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _run_subprocess_with_progress(self, cmd, total_duration: float) -> None:
        """
        运行 subprocess 并显示进度条
        
        Args:
            cmd: 命令列表
            total_duration: 总时长（秒）
        """
        with tqdm(
            total=total_duration,
            unit='s',
            unit_scale=True,
            desc="音频预处理"
        ) as pbar:
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='ignore'  # 忽略无法解码的字符
            )
            
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    # 解析 FFmpeg 输出中的时间信息
                    if 'time=' in output:
                        try:
                            time_str = output.split('time=')[1].split()[0]
                            time_parts = time_str.split(':')
                            if len(time_parts) == 3:
                                current_time = (
                                    float(time_parts[0]) * 3600 +
                                    float(time_parts[1]) * 60 +
                                    float(time_parts[2])
                                )
                                pbar.update(current_time - pbar.n)
                        except (IndexError, ValueError):
                            pass
            
            return_code = process.poll()
            if return_code != 0:
                # 获取所有错误输出
                stderr_output = []
                while True:
                    line = process.stderr.readline()
                    if not line:
                        break
                    stderr_output.append(line.strip())
                
                error_output = '\n'.join(stderr_output)
                if not error_output:
                    error_output = "未知错误，请检查FFmpeg命令和音频文件"
                
                raise RuntimeError(f"FFmpeg 执行失败 (exit code: {return_code}): {error_output}")
    
    def _apply_custom_audio_preprocessing(self, stream, noise_reduction: float, voice_enhancement: bool):
        """
        应用自定义音频预处理滤镜
        
        Args:
            stream: FFmpeg 输入流
            noise_reduction: 降噪强度
            voice_enhancement: 是否启用人声增强
            
        Returns:
            处理后的音频流
        """
        # 使用链式单独滤镜调用，避免 filter_complex 的问题
        try:
            # 逐个应用滤镜
            stream = stream.filter('highpass', f=85)   # 移除低频噪音
            stream = stream.filter('lowpass', f=4000)  # 移除高频噪音
            
            # 如果启用人声增强，适度增强音量
            if voice_enhancement:
                stream = stream.filter('volume', '1.2')  # 适度增强音量
            
            # 最后应用格式转换
            stream = stream.filter('aformat', 's16:16000:mono')
            
            return stream
            
        except Exception as e:
            self.logger.error(f"应用音频滤镜失败: {str(e)}")
            # 如果滤镜失败，返回原始流但仍要设置格式
            try:
                return stream.filter('aformat', 's16:16000:mono')
            except:
                return stream
    
    def split_audio(
        self, 
        audio_path: str, 
        output_dir: str, 
        segment_length: int = 300
    ) -> list:
        """
        将长音频文件分割成较小的片段
        
        Args:
            audio_path: 输入音频文件路径
            output_dir: 输出目录
            segment_length: 片段长度（秒），默认 5 分钟
            
        Returns:
            分割后的音频文件路径列表
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取音频信息
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['format']['duration'])
            
            self.logger.info(f"开始分割音频，总时长: {duration:.2f}s，片段长度: {segment_length}s")
            
            segments = []
            segment_count = int(duration // segment_length) + (1 if duration % segment_length > 0 else 0)
            
            for i in range(segment_count):
                start_time = i * segment_length
                segment_path = os.path.join(output_dir, f"segment_{i:03d}.wav")
                
                stream = ffmpeg.input(audio_path, ss=start_time, t=segment_length)
                stream = ffmpeg.output(stream, segment_path, acodec='copy')
                ffmpeg.run(stream, quiet=True, overwrite_output=True)
                
                if os.path.exists(segment_path):
                    segments.append(segment_path)
            
            self.logger.info(f"音频分割完成，共 {len(segments)} 个片段")
            return segments
            
        except Exception as e:
            error_msg = f"音频分割失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def cleanup_temp_files(self, file_paths: list) -> None:
        """
        清理临时文件
        
        Args:
            file_paths: 要清理的文件路径列表
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.debug(f"已删除临时文件: {file_path}")
            except Exception as e:
                self.logger.warning(f"删除临时文件失败: {file_path}, 错误: {str(e)}")