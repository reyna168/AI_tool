"""
AiSub 主应用程序
视频字幕生成器
"""

import os
import sys
import tempfile
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from tqdm import tqdm

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils import (
    ConfigLoader, 
    setup_logging,
    FFmpegWrapper, 
    WhisperTranscriber, 
    SRTGenerator,
    ExternalTranscriberManager
)


class AiSubApplication:
    """AiSub 主应用程序"""
    
    def __init__(self, config_path: Optional[str] = None, external_engine: Optional[str] = None):
        """
        初始化应用程序
        
        Args:
            config_path: 配置文件路径
            external_engine: 指定使用的外部转录引擎 (gemini, openai)
        """
        # 加载配置
        self.config = ConfigLoader(config_path)
        
        # 设置日志
        setup_logging(self.config)
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.ffmpeg = None
        self.whisper = None
        self.srt_generator = SRTGenerator()
        
        # 外部转录引擎设置
        self.external_engine = external_engine
        self.external_transcriber_manager = None
        
        # 初始化外部转录器管理器
        try:
            self.external_transcriber_manager = ExternalTranscriberManager(self.config.config)
            available_engines = self.external_transcriber_manager.get_available_engines()
            self.logger.info(f"可用的转录引擎: {', '.join(available_engines)}")
        except Exception as e:
            self.logger.warning(f"外部转录器初始化失败: {str(e)}")
        
        # 临时文件目录
        self.temp_dir = None
        
        self.logger.info("AiSub 应用程序初始化完成")
    
    def initialize_components(self) -> None:
        """初始化 FFmpeg 和 Whisper 组件"""
        try:
            # 初始化 FFmpeg
            ffmpeg_config = self.config.get_ffmpeg_config()
            ffmpeg_path = ffmpeg_config.get('executable_path') or None
            self.ffmpeg = FFmpegWrapper(ffmpeg_path)
            
            # 初始化 Whisper
            whisper_config = self.config.get_whisper_config()
            device_config = self.config.get_device_config()
            
            # 兼容旧格式设备配置
            legacy_device = whisper_config.get('device', 'auto')
            
            self.whisper = WhisperTranscriber(
                model_size=whisper_config.get('model_size', 'base'),
                device=legacy_device,  # 兼容旧格式
                device_config=device_config,  # 新格式配置
                download_root=whisper_config.get('download_root') or None
            )
            
            self.logger.info("所有组件初始化完成")
            
        except Exception as e:
            error_msg = f"组件初始化失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def process_video(
        self, 
        video_path: str, 
        output_path: Optional[str] = None,
        language: Optional[str] = None
    ) -> str:
        """
        处理视频文件，生成字幕
        
        Args:
            video_path: 视频文件路径
            output_path: 输出字幕文件路径
            language: 强制指定语言
            
        Returns:
            生成的字幕文件路径
        """
        try:
            # 验证输入文件
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
            self.logger.info(f"开始处理视频: {video_path}")
            
            # 初始化组件
            if self.ffmpeg is None or self.whisper is None:
                self.initialize_components()
            
            # 设置临时目录
            self._setup_temp_directory()
            
            # 获取视频信息
            video_info = self.ffmpeg.get_video_info(video_path)
            self.logger.info(f"视频信息: 时长 {video_info['duration']:.2f}s, 大小 {video_info['size'] / 1024 / 1024:.2f}MB")
            
            # 提取音频
            audio_path = self._extract_audio(video_path, video_info)
            
            # 处理音频 (转录)
            transcription_results = self._transcribe_audio(audio_path, language, video_info)
            
            # 生成字幕
            subtitle_path = self._generate_subtitle(transcription_results, video_path, output_path)
            
            # 清理临时文件
            self._cleanup_temp_files()
            
            self.logger.info(f"视频处理完成，字幕文件: {subtitle_path}")
            return subtitle_path
            
        except Exception as e:
            # 确保清理临时文件
            self._cleanup_temp_files()
            error_msg = f"视频处理失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _setup_temp_directory(self) -> None:
        """设置临时目录"""
        processing_config = self.config.get_processing_config()
        temp_dir_config = processing_config.get('temp_dir')
        
        if temp_dir_config:
            self.temp_dir = temp_dir_config
            os.makedirs(self.temp_dir, exist_ok=True)
        else:
            self.temp_dir = tempfile.mkdtemp(prefix='aisub_')
        
        self.logger.debug(f"临时目录: {self.temp_dir}")
    
    def _extract_audio(self, video_path: str, video_info: Dict) -> str:
        """
        提取音频
        
        Args:
            video_path: 视频文件路径
            video_info: 视频信息
            
        Returns:
            音频文件路径
        """
        ffmpeg_config = self.config.get_ffmpeg_config()
        audio_config = ffmpeg_config.get('audio_extraction', {})
        preprocessing_config = ffmpeg_config.get('audio_preprocessing', {})
        
        audio_filename = f"audio.{audio_config.get('format', 'wav')}"
        if not self.temp_dir:
            raise RuntimeError("临时目录未设置")
        audio_path = os.path.join(self.temp_dir, audio_filename)
        
        self.logger.info("开始提取音频...")
        
        # 检查是否启用音频预处理
        preprocess_enabled = preprocessing_config.get('enabled', False)
        
        if preprocess_enabled:
            # 先提取原始音频到临时文件
            raw_audio_path = os.path.join(self.temp_dir, f"raw_audio.{audio_config.get('format', 'wav')}")
            
            self.ffmpeg.extract_audio(
                video_path=video_path,
                output_path=raw_audio_path,
                audio_format=audio_config.get('format', 'wav'),
                sample_rate=audio_config.get('sample_rate', 16000),
                channels=audio_config.get('channels', 1),
                show_progress=audio_config.get('show_progress', True),
                preprocess_audio=False  # 第一步不预处理
            )
            
            # 然后对音频进行预处理
            self.logger.info("开始音频预处理（降噪、人声增强）...")
            self.ffmpeg.preprocess_audio_file(
                input_path=raw_audio_path,
                output_path=audio_path,
                noise_reduction=preprocessing_config.get('noise_reduction', 0.12),
                voice_enhancement=preprocessing_config.get('voice_enhancement', True),
                show_progress=preprocessing_config.get('show_progress', True)
            )
            
            # 清理临时原始音频文件
            try:
                os.remove(raw_audio_path)
            except Exception as e:
                self.logger.warning(f"清理临时文件失败: {str(e)}")
        else:
            # 直接提取音频，不进行预处理
            self.ffmpeg.extract_audio(
                video_path=video_path,
                output_path=audio_path,
                audio_format=audio_config.get('format', 'wav'),
                sample_rate=audio_config.get('sample_rate', 16000),
                channels=audio_config.get('channels', 1),
                show_progress=audio_config.get('show_progress', True),
                preprocess_audio=False
            )
        
        return audio_path
    
    def _get_engine_limits(self, engine: str) -> Dict[str, Any]:
        """
        获取不同引擎的处理限制
        
        Args:
            engine: 引擎名称
            
        Returns:
            包含引擎限制的字典
        """
        # 定义不同引擎的限制参数
        engine_limits = {
            'gemini': {
                'max_file_size_mb': 20.0,  # 20MB请求大小限制
                'max_duration_sec': 7200,  # 约2小时（保守估计，实际支持8.4小时）
                'segment_length': 600,     # 10分钟分段（充分利用Gemini能力）
                'description': 'Gemini 2.5-flash限制（实际支持长音频）'
            },
            'openai': {
                'max_file_size_mb': 25.0,  # 25MB
                'max_duration_sec': 600,   # 10分钟 
                'segment_length': 300,     # 5分钟分段
                'description': 'OpenAI Whisper API限制'
            },
            'custom': {
                'max_file_size_mb': 50.0,  # 50MB（默认限制）
                'max_duration_sec': 900,   # 15分钟
                'segment_length': 300,     # 5分钟分段
                'description': '自定义API限制'
            }
        }
        
        # 返回指定引擎的限制，如果未找到则使用默认限制
        return engine_limits.get(engine, {
            'max_file_size_mb': 20.0,
            'max_duration_sec': 300, 
            'segment_length': 180,
            'description': '默认引擎限制'
        })
    
    def _transcribe_audio(self, audio_path: str, language: Optional[str] = None, video_info: Optional[Dict] = None) -> Dict:
        """
        转录音频
        
        Args:
            audio_path: 音频文件路径
            language: 指定语言
            video_info: 视频信息
            
        Returns:
            转录结果
        """
        # 确保组件已初始化
        if self.ffmpeg is None or self.whisper is None:
            self.initialize_components()
        
        # 先尝试使用外部转录引擎（如果指定）
        if self.external_engine and self.external_transcriber_manager:
            try:
                self.logger.info(f"使用外部转录引擎: {self.external_engine}")
                
                # 获取音频信息以决定是否需要分段处理
                processing_config = self.config.get_processing_config()
                try:
                    audio_info = self.ffmpeg.get_audio_info(audio_path)
                    duration = audio_info['duration']
                except Exception as e:
                    # 如果无法获取音频信息，使用视频时长
                    if video_info and 'duration' in video_info:
                        duration = video_info['duration']
                        self.logger.warning(f"无法获取音频详细信息，使用视频时长 {duration:.1f}s: {str(e)}")
                    else:
                        self.logger.error(f"无法获取时长信息: {str(e)}")
                        raise RuntimeError(f"无法获取时长信息: {str(e)}")
                
                # 根据不同的外部引擎采用不同的处理策略
                processing_config = self.config.get_processing_config()
                
                # 为不同引擎确定最佳分段长度
                engine_limits = self._get_engine_limits(self.external_engine)
                
                if self.external_engine == 'gemini':
                    # Gemini 2.5-flash 实际限制：文件大小 < 20MB，时长 < 8.4小时
                    audio_file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
                    
                    # 检查是否需要分段处理
                    needs_segmentation = False
                    segmentation_reason = []
                    
                    # Gemini实际上可以处理很长的音频，但为了稳定性和效率，仍然建议分段
                    if audio_file_size > engine_limits['max_file_size_mb'] - 1.0:  # 保留1MB缓冲
                        needs_segmentation = True
                        segmentation_reason.append(f"文件大小超限 ({audio_file_size:.1f}MB > {engine_limits['max_file_size_mb'] - 1.0}MB)")
                    
                    # 对于超过一定时长的音频，为了提高处理效率和稳定性，仍然使用分段
                    if duration > 1800:  # 30分钟以上建议分段处理
                        needs_segmentation = True
                        segmentation_reason.append(f"音频较长 ({duration:.1f}s > 1800s)，建议分段处理提高效率")
                    
                    if needs_segmentation:
                        reason_str = ", ".join(segmentation_reason)
                        self.logger.info(f"音频需要分段处理: {reason_str}")
                        # 使用Gemini优化的分段长度（10分钟，充分利用Gemini能力）
                        result = self._transcribe_long_audio_with_external_api(
                            audio_path, duration, engine_limits['segment_length'], language
                        )
                    else:
                        self.logger.info(f"音频符合Gemini处理条件 (大小: {audio_file_size:.1f}MB, 时长: {duration:.1f}s)，使用单文件处理")
                        # 单文件处理
                        result = self.external_transcriber_manager.transcribe_with_engine(
                            audio_path, self.external_engine, language
                        )
                else:
                    # 其他外部API使用对应的限制检查
                    split_audio = processing_config.get('split_long_audio', True)
                    
                    # 检查是否超过该引擎的限制
                    needs_segmentation = False
                    if split_audio:
                        if 'max_file_size_mb' in engine_limits:
                            audio_file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
                            if audio_file_size > engine_limits['max_file_size_mb']:
                                needs_segmentation = True
                                
                        if duration > engine_limits['max_duration_sec']:
                            needs_segmentation = True
                    
                    if needs_segmentation:
                        self.logger.info(f"音频超过{self.external_engine}引擎限制，使用分段处理 (时长: {duration:.1f}s, 分段长度: {engine_limits['segment_length']}s)")
                        # 使用分段处理
                        result = self._transcribe_long_audio_with_external_api(
                            audio_path, duration, engine_limits['segment_length'], language
                        )
                    else:
                        # 单文件处理
                        result = self.external_transcriber_manager.transcribe_with_engine(
                            audio_path, self.external_engine, language
                        )
                
                if result:
                    self.logger.info(f"外部转录成功，使用引擎: {self.external_engine}")
                    return result
            except Exception as e:
                self.logger.warning(f"外部转录引擎 {self.external_engine} 失败: {str(e)}，回退到本地 Whisper")
        
        # 如果没有指定外部引擎或外部引擎失败，使用本地 Whisper
        return self._transcribe_with_whisper(audio_path, language, video_info)
    
    def _transcribe_with_whisper(self, audio_path: str, language: Optional[str] = None, video_info: Optional[Dict] = None) -> Dict:
        """
        使用本地 Whisper 转录音频
        
        Args:
            audio_path: 音频文件路径
            language: 指定语言
            video_info: 视频信息
            
        Returns:
            转录结果
        """
        processing_config = self.config.get_processing_config()
        # 使用基础配置而不是优化配置
        whisper_config = self.config.get_whisper_basic_config()
        transcription_config = whisper_config.get('transcription', {})
        
        self.logger.info("使用基础Whisper配置（不包含降噪等优化功能）")
        
        # 获取音频信息以估算处理时间
        try:
            audio_info = self.ffmpeg.get_audio_info(audio_path)
            duration = audio_info['duration']
        except Exception as e:
            # 如果无法获取音频信息，使用视频时长
            if video_info and 'duration' in video_info:
                duration = video_info['duration']
                self.logger.warning(f"无法获取音频详细信息，使用视频时长 {duration:.1f}s: {str(e)}")
            else:
                self.logger.error(f"无法获取时长信息: {str(e)}")
                raise RuntimeError(f"无法获取时长信息: {str(e)}")
        
        # 估算处理时间
        estimated_time = WhisperTranscriber.estimate_processing_time(
            duration, 
            whisper_config.get('model_size', 'base')
        )
        self.logger.info(f"预计转录时间: {estimated_time:.1f} 秒")
        
        # 检查是否需要分割音频 - 本地Whisper使用更长的分段
        # 本地处理可以使用更长的片段，降低处理复杂度
        local_segment_length = processing_config.get('local_segment_length', 300)  # 本地默认5分钟
        split_audio = processing_config.get('split_long_audio', True)
        
        if split_audio and duration > local_segment_length:
            self.logger.info(f"本地Whisper使用长分段处理 (时长: {duration:.1f}s, 分段长度: {local_segment_length}s)")
            return self._transcribe_long_audio(audio_path, duration, local_segment_length, language, transcription_config)
        else:
            return self._transcribe_single_audio(audio_path, language, transcription_config)
    
    def _transcribe_single_audio(self, audio_path: str, language: Optional[str], config: Dict) -> Dict:
        """转录单个音频文件"""
        self.logger.info("开始语音识别（单文件，基础模式）...")
        
        # 使用指定语言或配置中的语言
        target_language = language or config.get('language', 'auto')
        if target_language == 'auto':
            target_language = None
        
        # 基础模式：只传递基本参数，不传递优化参数
        basic_params = {
            'audio_path': audio_path,
            'language': target_language,
            'task': config.get('task', 'transcribe'),
            'temperature': config.get('temperature', 0.0),
            'word_timestamps': config.get('word_timestamps', True),
            'initial_prompt': config.get('initial_prompt') or None,
            'verbose': config.get('verbose', False)
        }
        
        # 根据配置决定是否添加可选参数
        if config.get('condition_on_previous_text') is not None:
            basic_params['condition_on_previous_text'] = config.get('condition_on_previous_text')
        if config.get('suppress_tokens') is not None:
            basic_params['suppress_tokens'] = config.get('suppress_tokens')
        if config.get('no_speech_threshold') is not None:
            basic_params['no_speech_threshold'] = config.get('no_speech_threshold')
        if config.get('logprob_threshold') is not None:
            basic_params['logprob_threshold'] = config.get('logprob_threshold')
        if config.get('compression_ratio_threshold') is not None:
            basic_params['compression_ratio_threshold'] = config.get('compression_ratio_threshold')
        if config.get('prepend_punctuations') is not None:
            basic_params['prepend_punctuations'] = config.get('prepend_punctuations')
        if config.get('append_punctuations') is not None:
            basic_params['append_punctuations'] = config.get('append_punctuations')
        
        # 基础模式下不传递优化参数（beam_size, best_of, patience）
        
        result = self.whisper.transcribe_audio(**basic_params)
        
        return result
    
    def _transcribe_long_audio(
        self, 
        audio_path: str, 
        duration: float, 
        segment_length: float,
        language: Optional[str], 
        config: Dict
    ) -> Dict:
        """转录长音频文件（分段处理）"""
        self.logger.info(f"开始语音识别（分段处理，基础模式），音频时长: {duration:.1f}s")
        
        # 分割音频
        if not self.temp_dir:
            raise RuntimeError("临时目录未设置")
        segments_dir = os.path.join(self.temp_dir, 'segments')
        audio_segments = self.ffmpeg.split_audio(audio_path, segments_dir, int(segment_length))
        
        self.logger.info(f"音频已分割为 {len(audio_segments)} 个片段")
        
        # 使用指定语言或配置中的语言
        target_language = language or config.get('language', 'auto')
        if target_language == 'auto':
            target_language = None
        
        # 基础模式：只传递基本参数
        basic_params = {
            'language': target_language,
            'task': config.get('task', 'transcribe'),
            'temperature': config.get('temperature', 0.0),
            'word_timestamps': config.get('word_timestamps', True),
            'initial_prompt': config.get('initial_prompt') or None,
            'verbose': config.get('verbose', False)
        }
        
        # 根据配置决定是否添加可选参数
        if config.get('condition_on_previous_text') is not None:
            basic_params['condition_on_previous_text'] = config.get('condition_on_previous_text')
        if config.get('suppress_tokens') is not None:
            basic_params['suppress_tokens'] = config.get('suppress_tokens')
        if config.get('no_speech_threshold') is not None:
            basic_params['no_speech_threshold'] = config.get('no_speech_threshold')
        if config.get('logprob_threshold') is not None:
            basic_params['logprob_threshold'] = config.get('logprob_threshold')
        if config.get('compression_ratio_threshold') is not None:
            basic_params['compression_ratio_threshold'] = config.get('compression_ratio_threshold')
        if config.get('prepend_punctuations') is not None:
            basic_params['prepend_punctuations'] = config.get('prepend_punctuations')
        if config.get('append_punctuations') is not None:
            basic_params['append_punctuations'] = config.get('append_punctuations')
        
        # 转录每个片段（基础模式，不使用优化参数）
        segment_results = self.whisper.transcribe_segments(
            audio_segments=audio_segments,
            **basic_params
        )
        
        # 合并结果
        return self._merge_segment_results(segment_results, segment_length)
    
    def _merge_segment_results(self, segment_results: List[Dict], segment_length: float) -> Dict:
        """合并分段转录结果"""
        all_segments = []
        all_text_parts = []
        current_offset = 0.0
        detected_language = None
        
        for i, result in enumerate(segment_results):
            if 'error' in result:
                self.logger.warning(f"片段 {i} 转录失败: {result['error']}")
                current_offset += segment_length
                continue
            
            if not detected_language and result.get('language'):
                detected_language = result['language']
            
            # 添加文本
            if result.get('text'):
                all_text_parts.append(result['text'])
            
            # 调整分段时间戳
            if 'segments' in result:
                for segment in result['segments']:
                    adjusted_segment = segment.copy()
                    adjusted_segment['start'] += current_offset
                    adjusted_segment['end'] += current_offset
                    
                    # 调整单词时间戳
                    if 'words' in adjusted_segment:
                        for word in adjusted_segment['words']:
                            word['start'] += current_offset
                            word['end'] += current_offset
                    
                    all_segments.append(adjusted_segment)
            
            current_offset += segment_length
        
        # 创建合并结果
        merged_result = {
            'text': ' '.join(all_text_parts),
            'segments': all_segments,
            'language': detected_language or 'unknown'
        }
        
        self.logger.info(f"转录完成，检测到语言: {detected_language}, 文本长度: {len(merged_result['text'])}")
        
        return merged_result
    
    def _transcribe_long_audio_with_external_api(
        self, 
        audio_path: str, 
        duration: float, 
        segment_length: float,
        language: Optional[str]
    ) -> Dict:
        """
        使用外部API转录长音频文件（分段处理）
        
        Args:
            audio_path: 音频文件路径
            duration: 音频时长
            segment_length: 分段长度
            language: 指定语言
            
        Returns:
            转录结果
        """
        self.logger.info(f"开始使用外部API语音识别（分段处理），音频时长: {duration:.1f}s，分段长度: {segment_length}s")
        
        # 分割音频
        if not self.temp_dir:
            raise RuntimeError("临时目录未设置")
        segments_dir = os.path.join(self.temp_dir, 'segments')
        audio_segments = self.ffmpeg.split_audio(audio_path, segments_dir, int(segment_length))
        
        self.logger.info(f"音频已分割为 {len(audio_segments)} 个片段")
        
        # 使用外部API转录所有片段
        if not self.external_engine:
            raise RuntimeError("外部转录引擎未指定")
            
        result = self.external_transcriber_manager.transcribe_segments_with_engine(
            audio_segments=audio_segments,
            engine=self.external_engine,
            language=language,
            segment_length=segment_length
        )
        
        return result
    
    def _generate_subtitle(
        self, 
        transcription_result: Dict, 
        video_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        生成字幕文件
        
        Args:
            transcription_result: 转录结果
            video_path: 原视频文件路径
            output_path: 指定的输出路径
            
        Returns:
            字幕文件路径
        """
        if not output_path:
            output_path = self._generate_output_path(video_path)
        
        subtitle_config = self.config.get_subtitle_config()
        
        self.logger.info("开始生成 SRT 字幕...")
        
        subtitle_path = self.srt_generator.generate_srt_from_whisper(
            whisper_result=transcription_result,
            output_path=output_path,
            max_line_length=subtitle_config.get('max_line_length', 80),
            max_lines_per_subtitle=subtitle_config.get('max_lines_per_subtitle', 2),
            min_subtitle_duration=subtitle_config.get('min_subtitle_duration', 1.0),
            max_subtitle_duration=subtitle_config.get('max_subtitle_duration', 10.0),
            merge_threshold=subtitle_config.get('merge_threshold', 0.5),
            encoding=subtitle_config.get('encoding', 'utf-8')
        )
        
        # 验证字幕文件
        validation_result = self.srt_generator.validate_srt_file(subtitle_path)
        if validation_result['valid']:
            self.logger.info(f"字幕验证成功: {validation_result['subtitle_count']} 个字幕项, 总时长 {validation_result['total_duration']:.1f}s")
        else:
            self.logger.warning(f"字幕验证发现问题: {validation_result['errors']}")
        
        return subtitle_path
    
    def _generate_output_path(self, video_path: str) -> str:
        """生成输出文件路径"""
        output_config = self.config.get_output_config()
        
        video_name = Path(video_path).stem
        filename_pattern = output_config.get('filename_pattern', '{video_name}.srt')
        filename = filename_pattern.format(video_name=video_name)
        
        if output_config.get('output_to_video_dir', False):
            output_dir = os.path.dirname(video_path)
        else:
            output_dir = output_config.get('default_output_dir', './output')
        
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        
        # 检查文件是否存在
        if os.path.exists(output_path) and not output_config.get('overwrite_existing', False):
            base, ext = os.path.splitext(output_path)
            counter = 1
            while os.path.exists(f"{base}_{counter}{ext}"):
                counter += 1
            output_path = f"{base}_{counter}{ext}"
        
        return output_path
    
    def _cleanup_temp_files(self) -> None:
        """清理临时文件"""
        processing_config = self.config.get_processing_config()
        
        if (processing_config.get('cleanup_temp_files', True) and 
            self.temp_dir and 
            os.path.exists(self.temp_dir)):
            
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.debug("临时文件已清理")
            except Exception as e:
                self.logger.warning(f"清理临时文件失败: {str(e)}")
            
            self.temp_dir = None
    
    def get_supported_video_formats(self) -> List[str]:
        """获取支持的视频格式"""
        return [
            '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', 
            '.webm', '.m4v', '.3gp', '.ts', '.mts', '.m2ts'
        ]
    
    def validate_video_file(self, video_path: str) -> bool:
        """
        验证视频文件
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            是否为有效的视频文件
        """
        if not os.path.exists(video_path):
            return False
        
        ext = os.path.splitext(video_path)[1].lower()
        return ext in self.get_supported_video_formats()
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取应用状态信息"""
        info = {
            'config_loaded': self.config is not None,
            'ffmpeg_initialized': self.ffmpeg is not None,
            'whisper_initialized': self.whisper is not None,
            'temp_dir': self.temp_dir
        }
        
        if self.whisper:
            info['whisper_model'] = self.whisper.get_model_info()
        
        return info
    
    def cleanup(self) -> None:
        """清理应用资源"""
        try:
            if self.whisper:
                self.whisper.cleanup()
            
            self._cleanup_temp_files()
            
            self.logger.info("应用资源清理完成")
            
        except Exception as e:
            self.logger.warning(f"清理应用资源时出现警告: {str(e)}")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()