"""
外部API转录器模块
支持 Gemini、OpenAI 等多种外部语音识别API
"""

import os
import sys
import base64
import json
import time
import logging
import requests
from pathlib import Path
from typing import Dict, Optional, List, Any
from abc import ABC, abstractmethod

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class BaseExternalTranscriber(ABC):
    """外部转录器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化转录器
        
        Args:
            config: API配置字典
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
            
        Returns:
            转录结果字典
        """
        pass
    
    def _load_audio_file(self, audio_path: str) -> bytes:
        """加载音频文件为字节数据"""
        try:
            with open(audio_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"无法读取音频文件: {str(e)}")
    
    def _audio_to_base64(self, audio_path: str) -> str:
        """将音频文件转换为base64编码"""
        audio_data = self._load_audio_file(audio_path)
        return base64.b64encode(audio_data).decode('utf-8')
    
    def _convert_audio_to_mp3(self, audio_path: str) -> str:
        """将音频文件转换为 MP3 格式（如果需要）"""
        if audio_path.lower().endswith('.mp3'):
            return audio_path
        
        try:
            import tempfile
            import subprocess
            
            # 创建临时 MP3 文件
            temp_mp3 = tempfile.mktemp(suffix='.mp3')
            
            # 使用 ffmpeg 转换
            cmd = [
                'ffmpeg', '-i', audio_path, 
                '-codec:a', 'libmp3lame', 
                '-b:a', '128k', 
                '-y', temp_mp3
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, encoding='utf-8', errors='ignore')
            self.logger.info(f"音频转换成功: {audio_path} -> {temp_mp3}")
            return temp_mp3
            
        except Exception as e:
            self.logger.warning(f"音频转换失败: {str(e)}，尝试使用原文件")
            return audio_path
    
    def transcribe_segments(self, audio_segments: List[str], language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        转录多个音频片段，支持正确的时间轴拼接
        
        Args:
            audio_segments: 音频片段文件路径列表
            language: 语言代码
            
        Returns:
            每个片段的转录结果列表
        """
        results = []
        total_duration_offset = 0.0  # 前面所有片段的总时长
        
        for i, segment_path in enumerate(audio_segments):
            try:
                self.logger.info(f"正在转录片段 {i+1}/{len(audio_segments)}: {segment_path}")
                
                # 获取当前片段的时长
                try:
                    import ffmpeg
                    probe = ffmpeg.probe(segment_path)
                    current_duration = float(probe['format']['duration'])
                except Exception as e:
                    self.logger.warning(f"无法获取片段时长: {str(e)}，使用默认值")
                    current_duration = 30.0  # 默认片段时长
                
                # 为当前片段设置上下文信息（用于提示词）
                if hasattr(self, '_set_segment_context'):
                    self._set_segment_context(i + 1, total_duration_offset)
                
                # 转录当前片段
                result = self.transcribe_audio(segment_path, language)
                
                # 在结果中添加片段信息
                if isinstance(result, dict):
                    result['segment_index'] = i
                    result['segment_start_offset'] = total_duration_offset
                    result['segment_duration'] = current_duration
                    
                    # 如果有segments，调整其时间戳以反映在整个音频中的位置
                    if 'segments' in result:
                        for segment in result['segments']:
                            # 检查Gemini是否已经包含了偏移量
                            if segment.get('gemini_offset_applied', False):
                                # Gemini已经包含偏移，不需要额外添加
                                if 'start' in segment:
                                    segment['absolute_start'] = segment['start']  # 直接使用
                                if 'end' in segment:
                                    segment['absolute_end'] = segment['end']  # 直接使用
                                self.logger.info(f"Gemini已偏移，直接使用: {segment.get('text', '')[:20]} -> {segment.get('start', 0):.1f}s")
                            else:
                                # 需要添加偏移量
                                if 'start' in segment:
                                    segment['absolute_start'] = segment['start'] + total_duration_offset
                                if 'end' in segment:
                                    segment['absolute_end'] = segment['end'] + total_duration_offset
                                self.logger.info(f"添加偏移: {segment.get('text', '')[:20]} -> {segment.get('start', 0):.1f}s + {total_duration_offset:.1f}s = {segment.get('absolute_start', 0):.1f}s")
                
                results.append(result)
                
                # 更新时间偏移
                total_duration_offset += current_duration
                
            except Exception as e:
                error_msg = f"片段 {i+1} 转录失败: {str(e)}"
                self.logger.error(error_msg)
                results.append({
                    'error': error_msg,
                    'segment_index': i,
                    'segment_start_offset': total_duration_offset,
                    'segment_duration': 30.0  # 默认时长
                })
                # 即使失败也要更新时间偏移以保持时间轴连续性
                total_duration_offset += 30.0
        
        return results


class GeminiTranscriber(BaseExternalTranscriber):
    """Google Gemini API 转录器"""
    
    # 语言配置映射
    LANGUAGE_CONFIGS = {
        'zh': {
            'name': '简体中文',
            'instructions': '使用简体中文进行转录',
            'example_text_1': '第一句话',
            'example_text_2': '第二句话',
            'char_limit': 30
        },
        'zh-tw': {
            'name': '繁体中文',
            'instructions': '使用繁体中文进行转录',
            'example_text_1': '第一句話',
            'example_text_2': '第二句話',
            'char_limit': 30
        },
        'en': {
            'name': 'English',
            'instructions': 'Transcribe in English',
            'example_text_1': 'First sentence',
            'example_text_2': 'Second sentence',
            'char_limit': 50
        },
        'ja': {
            'name': '日本語',
            'instructions': '日本語で転写してください',
            'example_text_1': '最初の文',
            'example_text_2': '二番目の文',
            'char_limit': 25
        },
        'ko': {
            'name': '한국어',
            'instructions': '한국어로 전사해주세요',
            'example_text_1': '첫 번째 문장',
            'example_text_2': '두 번째 문장',
            'char_limit': 30
        },
        'es': {
            'name': 'Español',
            'instructions': 'Transcribir en español',
            'example_text_1': 'Primera oración',
            'example_text_2': 'Segunda oración',
            'char_limit': 45
        },
        'fr': {
            'name': 'Français',
            'instructions': 'Transcrire en français',
            'example_text_1': 'Première phrase',
            'example_text_2': 'Deuxième phrase',
            'char_limit': 45
        },
        'de': {
            'name': 'Deutsch',
            'instructions': 'Auf Deutsch transkribieren',
            'example_text_1': 'Erster Satz',
            'example_text_2': 'Zweiter Satz',
            'char_limit': 40
        },
        'ru': {
            'name': 'Русский',
            'instructions': 'Транскрибировать на русском языке',
            'example_text_1': 'Первое предложение',
            'example_text_2': 'Второе предложение',
            'char_limit': 35
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable or config.")
        
        self.base_url = config.get('base_url', 'https://generativelanguage.googleapis.com')
        self.model = config.get('model', 'gemini-1.5-flash')
        self.timeout = config.get('timeout', 300)
        self.rate_limit = config.get('rate_limit', 15)
        self.default_language = config.get('default_language', 'zh')  # 默认简体中文
        self.prompt_template = config.get('prompt_template', 
            "请转录以下音频内容为中文字幕，只输出转录文本，不要添加任何解释或格式：\n\n音频内容：{audio_text}")
    
    def _generate_srt_prompt(self, language: Optional[str] = None, time_offset: float = 0.0) -> str:
        """
        生成优化的SRT格式提示词
        
        Args:
            language: 目标语言代码
            time_offset: 时间偏移（用于多片段处理）
            
        Returns:
            优化的提示词
        """
        # 确定目标语言（优先使用传入参数，其次使用配置默认值）
        target_lang = language or self.default_language
        
        # 处理语言代码映射
        if target_lang.startswith('zh'):
            if 'tw' in target_lang.lower() or 'hant' in target_lang.lower():
                lang_config = self.LANGUAGE_CONFIGS.get('zh-tw', self.LANGUAGE_CONFIGS['zh'])
            else:
                lang_config = self.LANGUAGE_CONFIGS['zh']
        else:
            lang_config = self.LANGUAGE_CONFIGS.get(target_lang, self.LANGUAGE_CONFIGS['zh'])
        
        # 获取片段信息
        segment_index = getattr(self, '_segment_index', 1)
        
        # 基础转录要求
        base_requirements = [
            "按照自然的语句停顿进行分段",
            "忽略背景音乐、噪音和非语音声音",
            "保持语言的自然流畅性和准确性",
            "如果有多个说话者，请按时间顺序输出",
            "不要重复输出相同的内容或单个字符",
            "对于无意义的语气词（如'啊'、'哈'等），请适度简化",
            "忽略末尾的标点符号（如，。）"
        ]
        
        # 添加语言特定要求
        base_requirements.append(lang_config['instructions'])
        
        # 时间轴要求
        timing_requirements = [
            f"这是音频的第{segment_index}个片段",
            f"前面片段的总时长为{time_offset:.1f}秒",
            "请在此基础上继续计算时间戳",
            f"每个字幕条目的开始时间应该加上{time_offset:.1f}秒"
        ]
        
        # 格式说明
        format_notes = [
            "序号从1开始递增",
            "时间格式：时:分:秒,毫秒",
            "每个字幕条目之间用空行分隔",
            f"字幕文字简洁准确，每行不超过{lang_config['char_limit']}个字符"
        ]
        
        # 构建完整提示词
        newline = "\n"
        prompt = f"""你是一个专业的音频转录助手。请将这段音频转录为标准SRT字幕格式，严格遵循以下要求：

转录要求：
{newline.join([f"{i+1}. {req}" for i, req in enumerate(base_requirements)])}

时间轴要求（重要）：
{newline.join([f"{i+1}. {req}" for i, req in enumerate(timing_requirements)])}

输出格式要求（标准SRT格式）：
1
00:00:01,000 --> 00:00:03,500
{lang_config['example_text_1']}

2
00:00:04,000 --> 00:00:06,200
{lang_config['example_text_2']}

格式说明：
{newline.join([f"- {note}" for note in format_notes])}

请开始转录并输出标准SRT格式："""
        
        return prompt
    
    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """使用Gemini API转录音频"""
        try:
            self.logger.info(f"开始使用 Gemini API 转录音频: {audio_path}")
            self.logger.info(f"使用 Gemini 模型: {self.model}")
            
            # 准备音频数据 - 优先使用原始格式
            audio_file_to_use = audio_path
            mime_type = "audio/wav"  # 默认使用 WAV 格式
            
            # 检查文件格式
            if audio_path.lower().endswith('.mp3'):
                mime_type = "audio/mp3"
            elif audio_path.lower().endswith('.wav'):
                mime_type = "audio/wav"
            elif audio_path.lower().endswith('.flac'):
                mime_type = "audio/flac"
            else:
                # 对于其他格式，尝试转换为 MP3
                self.logger.info(f"音频格式不常见，尝试转换为 MP3 格式")
                audio_file_to_use = self._convert_audio_to_mp3(audio_path)
                mime_type = "audio/mp3"
            
            self.logger.info(f"使用音频格式: {mime_type}")
            
            # 检查音频文件大小（仅记录，不拒绝处理）
            file_size = os.path.getsize(audio_file_to_use)
            file_size_mb = file_size / (1024 * 1024)
            if file_size_mb > 9.5:  # 10MB
                self.logger.warning(f"音频文件较大 ({file_size_mb:.1f}MB)，应在上层进行分段处理")
            else:
                self.logger.info(f"音频文件大小: {file_size_mb:.1f}MB")
            
            # 获取音频时长（移除严格限制）
            try:
                import ffmpeg
                probe = ffmpeg.probe(audio_file_to_use)
                duration = float(probe['format']['duration'])
                self.logger.info(f"音频时长: {duration:.1f}秒")
                
            except Exception as e:
                self.logger.warning(f"无法获取音频时长: {str(e)}")
                duration = 30.0  # 默认时长
            
            # 准备音频数据
            audio_base64 = self._audio_to_base64(audio_path)
            
            # 构建API请求
            url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': self.api_key
            }
            
            # 使用优化的多语言提示词生成器
            time_offset = getattr(self, '_current_offset', 0.0)
            segment_start_offset = time_offset  # 设置片段偏移
            
            improved_prompt = self._generate_srt_prompt(language, time_offset)
            
            payload = {
                "contents": [{
                    "parts": [
                        {
                            "text": improved_prompt
                        },
                        {
                            "inline_data": {
                                "mime_type": "audio/wav",
                                "data": audio_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.0,  # 更低的随机性以获得一致性
                    "maxOutputTokens": 65536,
                }
            }
            
            # 发送请求
            self.logger.info("正在调用 Gemini API，请稍候...")
            response = requests.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                # self.logger.info(f"Gemini API 调用成功，响应: {result}")
                
                # 添加详细的调试日志：显示API原始返回结果
                # self.logger.info("=== Gemini API 原始返回结果 ===")
                # self.logger.info(f"完整响应: {result}")
                
                if 'candidates' in result and result['candidates']:
                    candidate = result['candidates'][0]
                    self.logger.info(f"候选结果: {candidate}")
                    
                    if 'content' in candidate and 'parts' in candidate['content']:
                        parts = candidate['content']['parts']
                        self.logger.info(f"内容部分数量: {len(parts)}")
                        for i, part in enumerate(parts):
                            self.logger.info(f"第{i+1}部分: {part}")
                            if 'text' in part:
                                text_content = part['text'].strip()
                                self.logger.info(f"文本内容长度: {len(text_content)}")
                                # self.logger.info(f"文本前200字符: {repr(text_content[:200])}")
                    else:
                        self.logger.warning("候选结果中没有 content.parts")
                else:
                    self.logger.warning("响应中没有 candidates")
                
                self.logger.info("=== 结束原始返回结果 ===")
                
                # 解析响应
                if 'candidates' in result and result['candidates']:
                    candidate = result['candidates'][0]
                    
                    # 检查是否有内容
                    if 'content' not in candidate or 'parts' not in candidate['content']:
                        # 可能是静音片段，返回空转录
                        self.logger.info("检测到静音片段或无语音内容")
                        segments = self._create_segments_from_text("", duration, segment_start_offset)
                        return {
                            'text': '',
                            'language': language or 'zh',
                            'engine': 'gemini',
                            'segments': segments
                        }
                    
                    parts = candidate['content']['parts']
                    if not parts or 'text' not in parts[0]:
                        # 静音片段处理
                        self.logger.info("检测到静音片段")
                        segments = self._create_segments_from_text("", duration, segment_start_offset)
                        return {
                            'text': '',
                            'language': language or 'zh',
                            'engine': 'gemini',
                            'segments': segments
                        }
                    
                    transcript = parts[0]['text']
                    
                    # 清理转录文本
                    transcript = transcript.strip()
                    if not transcript:
                        raise RuntimeError("Gemini API 返回空的转录结果")
                    
                    # 尝试解析SRT格式的响应
                    try:
                        segments = self._parse_srt_response(transcript, segment_start_offset)
                        
                        if not segments:
                            # 如果解析SRT失败，回退到文本分段处理
                            self.logger.warning("无法解析SRT格式，回退到文本分段处理")
                            segments = self._create_segments_from_text(transcript, duration, segment_start_offset)
                            timing_note = 'Timestamps are estimated based on text length, not audio-aligned'
                            timing_accuracy = 'low'
                        else:
                            self.logger.info(f"成功解析SRT格式，获得 {len(segments)} 个字幕段")
                            timing_note = 'Timestamps provided by Gemini API based on audio analysis'
                            timing_accuracy = 'medium'  # Gemini提供的时间戳质量
                            
                    except Exception as e:
                        self.logger.warning(f"SRT解析失败: {str(e)}，回退到文本分段处理")
                        segments = self._create_segments_from_text(transcript, duration, segment_start_offset)
                        timing_note = 'Timestamps are estimated based on text length, not audio-aligned'
                        timing_accuracy = 'low'
                    
                    # 获取纯文本（从segments中提取）
                    pure_text = ' '.join([seg['text'] for seg in segments if seg['text'].strip()])
                    
                    self.logger.info(f"Gemini 转录完成，生成 {len(segments)} 个段落")
                    
                    return {
                        'text': pure_text,
                        'language': language or 'zh',
                        'engine': 'gemini',
                        'segments': segments,
                        # 时间戳来源标识
                        'timestamp_source': 'gemini_api' if timing_accuracy == 'medium' else 'estimated',
                        'timing_accuracy': timing_accuracy,
                        'timing_note': timing_note
                    }
                else:
                    raise RuntimeError("Gemini API 返回格式异常")
            else:
                error_msg = f"Gemini API 请求失败: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
                
        except Exception as e:
            error_msg = f"Gemini 转录失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _parse_srt_response(self, srt_text: str, segment_start_offset: float = 0.0) -> List[Dict[str, Any]]:
        """
        解析Gemini返回的SRT格式文本
        
        Args:
            srt_text: SRT格式的文本
            segment_start_offset: 该片段在整个音频中的开始时间偏移
            
        Returns:
            segments列表
        """
        import re
        
        segments = []
        
        # SRT格式正则表达式
        # 匹配序号、时间范围和文本
        srt_pattern = r'(\d+)\s*\n([0-9:,]+)\s*-->\s*([0-9:,]+)\s*\n([^\n]*(?:\n(?!\d+\s*\n[0-9:,]+)[^\n]*)*?)'
        
        matches = re.findall(srt_pattern, srt_text, re.MULTILINE | re.DOTALL)
        
        if not matches:
            self.logger.warning("无法解析SRT格式，可能格式不正确")
            return []
        
        segments = []
        gemini_already_offset = False  # 用于记录是否检测到偏移
        
        for i, (seq_num, start_time, end_time, text) in enumerate(matches):
            try:
                # 解析时间戳
                start_seconds = self._parse_srt_time(start_time.strip())
                end_seconds = self._parse_srt_time(end_time.strip())
                
                # 清理文本
                clean_text = text.strip()
                if not clean_text:
                    continue
                
                # 只在第一个segment时检查Gemini是否已经包含偏移量
                if i == 0 and segment_start_offset > 0:
                    # 如果Gemini返回的第一个时间戳接近或大于偏移量，说明已经包含了偏移
                    gemini_already_offset = start_seconds >= segment_start_offset * 0.1  # 大于10%就认为已偏移
                    if gemini_already_offset:
                        self.logger.info(f"Gemini已在时间戳中包含偏移量，不再添加额外偏移")
                    else:
                        self.logger.info(f"Gemini返回相对时间戳，需要添加偏移量 {segment_start_offset}秒")
                
                # 根据检测结果设置实际时间
                if gemini_already_offset:
                    # 不添加额外偏移，直接使用Gemini返回的时间戳
                    actual_start = start_seconds
                    actual_end = end_seconds
                else:
                    # Gemini返回的是相对时间，需要添加偏移
                    actual_start = start_seconds + segment_start_offset
                    actual_end = end_seconds + segment_start_offset
                
                # 构建 segment
                segment = {
                    'id': i,
                    'seek': int(actual_start * 100),
                    'start': actual_start,  # 使用处理后的绝对时间
                    'end': actual_end,
                    'text': clean_text,
                    'tokens': [],
                    'temperature': 0.0,
                    'avg_logprob': -0.1,  # 高置信度，因为是AI直接提供的
                    'compression_ratio': 1.0,
                    'no_speech_prob': 0.01,  # 低无语音概率
                    'timestamp_source': 'gemini_api',  # 由Gemini API提供
                    'estimated_timing': False,  # 不是估算的
                    'api_source': 'gemini',
                    'gemini_offset_applied': gemini_already_offset  # 所有segment都设置同样的状态
                }
                
                segments.append(segment)
                
            except Exception as e:
                self.logger.warning(f"解析第{seq_num}个SRT条目失败: {str(e)}")
                continue
        
        self.logger.info(f"成功解析 {len(segments)} 个SRT条目")
        return segments
    
    def _parse_srt_time(self, time_str: str) -> float:
        """
        将SRT时间格式转换为秒数
        
        Args:
            time_str: SRT时间格式 '00:01:23,456'
            
        Returns:
            秒数 (float)
        """
        try:
            # 处理 '00:01:23,456' 格式
            if ',' in time_str:
                time_part, ms_part = time_str.split(',')
                milliseconds = int(ms_part)
            else:
                time_part = time_str
                milliseconds = 0
            
            # 解析时分秒
            time_parts = time_part.split(':')
            if len(time_parts) == 3:
                hours, minutes, seconds = map(int, time_parts)
            elif len(time_parts) == 2:
                hours = 0
                minutes, seconds = map(int, time_parts)
            else:
                raise ValueError(f"无法解析时间格式: {time_str}")
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
            return total_seconds
            
        except Exception as e:
            self.logger.error(f"时间解析错误: {time_str} -> {str(e)}")
            return 0.0

    def _set_segment_context(self, segment_index: int, total_offset: float):
        """
        为分段处理设置上下文信息
        
        Args:
            segment_index: 当前片段的索引（从1开始）
            total_offset: 前面所有片段的总时长
        """
        self._segment_index = segment_index
        self._current_offset = total_offset
    
    def _create_segments_from_text(self, text: str, duration: float, segment_start_offset: float = 0.0) -> List[Dict[str, Any]]:
        """
        从文本创建合理的段落分割
        
        重要提示：由于外部API（如Gemini）不提供时间戳信息，
        这里的时间戳是基于文本长度和音频时长的**估算值**，
        并非真实的音频对齐时间戳。
        
        Args:
            text: 转录文本
            duration: 音频片段时长 
            segment_start_offset: 该片段在整个音频中的开始时间偏移
            
        Returns:
            段落列表，包含估算的时间戳
        """
        import re
        
        # 处理空文本的情况（静音片段）
        if not text or text.strip() == "":
            # 为静音片段创建一个空的时间段，保持时间轴连续性
            return [{
                'id': 0,
                'seek': int(segment_start_offset * 100),
                'start': 0.0,  # 相对于片段的开始时间
                'end': duration,  # 相对于片段的结束时间
                'text': '',  # 空文本表示静音
                'tokens': [],
                'temperature': 0.0,
                'avg_logprob': -1.0,  # 低概率表示静音
                'compression_ratio': 1.0,
                'no_speech_prob': 0.95,  # 高概率表示无语音
                'timestamp_source': 'silent',  # 静音片段
                'estimated_timing': True,
                'api_source': 'external'
            }]
        
        # 按标点符号和自然停顿分割文本，优先按行分割
        sentences = []
        
        # 第一步：按换行符分割（Gemini可能按要求返回了分行的结果）
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 如果行太长，再按句号分割
            if len(line) > 30:  # 30字以上认为过长
                sub_parts = re.split(r'[。！？]', line)
                for sub_part in sub_parts:
                    sub_part = sub_part.strip()
                    if sub_part:
                        # 如果还是太长，按逗号分割
                        if len(sub_part) > 25:
                            comma_parts = re.split(r'[，、；]', sub_part)
                            for comma_part in comma_parts:
                                comma_part = comma_part.strip()
                                if comma_part:
                                    sentences.append(comma_part)
                        else:
                            sentences.append(sub_part)
            else:
                sentences.append(line)
        
        # 如果没有找到合适的分割点，按字数分割
        if not sentences or len(sentences) == 1:
            # 按每50字分割
            sentences = []
            for i in range(0, len(text), 50):
                chunk = text[i:i+50].strip()
                if chunk:
                    sentences.append(chunk)
        
        if not sentences:
            sentences = [text] if text.strip() else ['']
        
        segments = []
        # 对于有内容的音频片段，使用更智能的时间分配策略
        total_chars = sum(len(s) for s in sentences)
        
        # 根据音频时长和内容量智能调整语音区间
        # 对于长音频，假设语音更可能分布在整个时间范围内
        if duration <= 60:  # 1分钟以内的短音频
            if len(text.strip()) < 30:  # 短文本
                # 短音频短文本，可能语音在中间部分
                speech_start_ratio = 0.25
                speech_end_ratio = 0.75
            else:  # 长文本
                # 短音频长文本，语音更可能占满大部分时间
                speech_start_ratio = 0.1
                speech_end_ratio = 0.9
        else:  # 长音频（超过1分钟）
            # 对于长音频，估算语音密度来决定时间分布
            text_density = len(text.strip()) / duration  # 每秒字符数
            
            if text_density < 1.5:  # 低密度，可能有较多静音或音乐
                # 估算语音可能在中间部分
                speech_start_ratio = 0.2
                speech_end_ratio = 0.8
            elif text_density > 3:  # 高密度，语音较密集
                # 语音可能贯穿整个音频
                speech_start_ratio = 0.05
                speech_end_ratio = 0.95
            else:  # 中等密度
                speech_start_ratio = 0.1
                speech_end_ratio = 0.9
        
        speech_start_time = duration * speech_start_ratio
        speech_end_time = duration * speech_end_ratio
        speech_duration = speech_end_time - speech_start_time
        
        current_time = speech_start_time
        
        for i, sentence in enumerate(sentences):
            if not sentence:
                continue
            
            # 根据文字数量分配时间
            char_ratio = len(sentence) / total_chars if total_chars > 0 else 1.0 / len(sentences)
            segment_duration = speech_duration * char_ratio
            
            # 确保每个段落至少有0.5秒，最多不超过剩余时间
            segment_duration = max(0.5, min(segment_duration, speech_end_time - current_time))
            
            start_time = current_time
            end_time = min(current_time + segment_duration, speech_end_time)
            
            # 最后一个句子延伸到语音结束时间
            if i == len(sentences) - 1:
                end_time = speech_end_time
            
            segments.append({
                'id': i,
                'seek': int((segment_start_offset + start_time) * 100),
                'start': start_time,  # 相对于当前片段的时间
                'end': end_time,
                'text': sentence,
                'tokens': [],
                'temperature': 0.0,
                'avg_logprob': -0.3,
                'compression_ratio': 1.0,
                'no_speech_prob': 0.05,
                # 重要：标识这些时间戳是估算的，不是真实的音频对齐
                'timestamp_source': 'estimated',  # 时间戳来源：estimated 表示估算，audio_aligned 表示真实对齐
                'estimated_timing': True,  # 明确标识为估算时间
                'api_source': 'gemini'  # 数据来源
            })
            
            current_time = end_time
        
        return segments


class OpenAITranscriber(BaseExternalTranscriber):
    """OpenAI API 转录器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or config.")
        
        self.base_url = config.get('base_url', 'https://api.openai.com/v1')
        self.model = config.get('model', 'whisper-1')
        self.timeout = config.get('timeout', 300)
        self.language = config.get('language', 'zh')
        self.response_format = config.get('response_format', 'srt')
    
    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """使用OpenAI Whisper API转录音频"""
        try:
            self.logger.info(f"开始使用 OpenAI API 转录音频: {audio_path}")
            
            url = f"{self.base_url}/audio/transcriptions"
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            # 准备文件数据
            with open(audio_path, 'rb') as audio_file:
                files = {
                    'file': (Path(audio_path).name, audio_file, 'audio/wav'),
                    'model': (None, self.model),
                    'language': (None, language or self.language),
                    'response_format': (None, 'verbose_json'),
                    'timestamp_granularities[]': (None, 'segment')
                }
                
                response = requests.post(
                    url, 
                    headers=headers, 
                    files=files, 
                    timeout=self.timeout
                )
            
            if response.status_code == 200:
                result = response.json()
                
                return {
                    'text': result.get('text', ''),
                    'language': result.get('language', language or 'zh'),
                    'engine': 'openai',
                    'segments': result.get('segments', [])
                }
            else:
                error_msg = f"OpenAI API 请求失败: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
                
        except Exception as e:
            error_msg = f"OpenAI 转录失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

class ExternalTranscriberManager:
    """外部转录器管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化管理器
        
        Args:
            config: 完整配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 外部API配置
        self.external_apis = config.get('external_apis', {})
        
        # 转录引擎配置
        self.engine_config = config.get('transcription_engine', {})
        self.default_engine = self.engine_config.get('default_engine', 'whisper')
        self.enable_fallback = self.engine_config.get('enable_fallback', True)
        self.fallback_order = self.engine_config.get('fallback_order', ['whisper', 'gemini', 'openai'])
        
        # 初始化转录器
        self.transcribers = {}
        self._initialize_transcribers()
    
    def _initialize_transcribers(self):
        """初始化所有可用的转录器"""
        # Gemini转录器
        if 'gemini' in self.external_apis:
            try:
                self.transcribers['gemini'] = GeminiTranscriber(self.external_apis['gemini'])
                self.logger.info("Gemini 转录器初始化成功")
            except Exception as e:
                self.logger.warning(f"Gemini 转录器初始化失败: {str(e)}")
        
        # OpenAI转录器
        if 'openai' in self.external_apis:
            try:
                self.transcribers['openai'] = OpenAITranscriber(self.external_apis['openai'])
                self.logger.info("OpenAI 转录器初始化成功")
            except Exception as e:
                self.logger.warning(f"OpenAI 转录器初始化失败: {str(e)}")
    
    def get_available_engines(self) -> List[str]:
        """获取可用的转录引擎列表"""
        engines = ['whisper']  # Whisper始终可用
        engines.extend(self.transcribers.keys())
        return engines
    
    def transcribe_with_engine(self, audio_path: str, engine: str, language: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        使用指定引擎转录音频
        
        Args:
            audio_path: 音频文件路径
            engine: 转录引擎名称
            language: 语言代码
            
        Returns:
            转录结果，如果是Whisper引擎返回None
        """
        if engine == 'whisper':
            # 返回None，让调用方使用本地Whisper
            return None
        
        if engine not in self.transcribers:
            raise ValueError(f"转录引擎 '{engine}' 不可用")
        
        return self.transcribers[engine].transcribe_audio(audio_path, language)
    
    def transcribe_segments_with_engine(
        self, 
        audio_segments: List[str], 
        engine: str, 
        language: Optional[str] = None,
        segment_length: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        使用指定引擎转录多个音频片段并合并结果
        
        Args:
            audio_segments: 音频片段文件路径列表
            engine: 转录引擎名称
            language: 语言代码
            segment_length: 每个片段的时长（秒）
            
        Returns:
            合并后的转录结果
        """
        if engine == 'whisper':
            # Whisper 使用本地处理，返回 None
            return None
        
        if engine not in self.transcribers:
            raise ValueError(f"转录引擎 '{engine}' 不可用")
        
        # 转录所有片段
        transcriber = self.transcribers[engine]
        segment_results = transcriber.transcribe_segments(audio_segments, language)
        
        # 合并结果
        return self._merge_segment_results(segment_results, segment_length)
    
    def _merge_segment_results(self, segment_results: List[Dict[str, Any]], segment_length: float) -> Dict[str, Any]:
        """
        合并分段转录结果，支持正确的时间轴处理
        
        Args:
            segment_results: 每个片段的转录结果列表
            segment_length: 每个片段的时长（秒）
            
        Returns:
            合并后的转录结果
        """
        all_segments = []
        all_text_parts = []
        detected_language = None
        detected_engine = None
        
        for i, result in enumerate(segment_results):
            if 'error' in result:
                self.logger.warning(f"片段 {i+1} 转录失败: {result['error']}")
                # 为失败的片段创建一个静音时间段，保持时间轴连续性
                segment_start_offset = result.get('segment_start_offset', i * segment_length)
                segment_duration = result.get('segment_duration', segment_length)
                
                silent_segment = {
                    'id': len(all_segments),
                    'seek': int(segment_start_offset * 100),
                    'start': segment_start_offset,
                    'end': segment_start_offset + segment_duration,
                    'text': '',  # 空文本表示转录失败或静音
                    'tokens': [],
                    'temperature': 0.0,
                    'avg_logprob': -2.0,  # 很低的概率表示转录失败
                    'compression_ratio': 1.0,
                    'no_speech_prob': 0.99  # 很高概率表示无语音或转录失败
                }
                all_segments.append(silent_segment)
                continue
            
            # 获取语言和引擎信息
            if not detected_language and result.get('language'):
                detected_language = result['language']
            if not detected_engine and result.get('engine'):
                detected_engine = result['engine']
            
            # 添加文本（即使是空文本也要记录）
            text_content = result.get('text', '').strip()
            if text_content:
                all_text_parts.append(text_content)
            
            # 处理segments
            if 'segments' in result and result['segments']:
                # 检查segments是否已经包含绝对时间（由新的transcribe_segments方法提供）
                for segment in result['segments']:
                    adjusted_segment = segment.copy()
                    
                    # 调试信息：显示原始 segment 信息
                    self.logger.info(f"处理segment: {segment.get('text', '')[:30]}, start={segment.get('start', 0):.1f}s, gemini_offset_applied={segment.get('gemini_offset_applied', 'N/A')}")
                    
                    # 检查是否已经有绝对时间（absolute_start, absolute_end）
                    if 'absolute_start' in segment and 'absolute_end' in segment:
                        # 使用已经计算好的绝对时间
                        adjusted_segment['start'] = segment['absolute_start']
                        adjusted_segment['end'] = segment['absolute_end']
                        # 删除临时字段
                        adjusted_segment.pop('absolute_start', None)
                        adjusted_segment.pop('absolute_end', None)
                        self.logger.info(f"使用绝对时间: {adjusted_segment['start']:.1f}s-{adjusted_segment['end']:.1f}s")
                    elif segment.get('gemini_offset_applied', False) == True:
                        # Gemini已经在时间戳中包含了偏移量，不需要额外添加
                        # 直接使用Gemini返回的时间戳
                        self.logger.info(f"使用Gemini已偏移的时间戳: {adjusted_segment['start']:.1f}s-{adjusted_segment['end']:.1f}s [{adjusted_segment.get('text', '')[:20]}]")
                        # 不修改start和end
                    else:
                        # 回退到传统的偏移计算（用于兼容旧的实现）
                        segment_start_offset = result.get('segment_start_offset', i * segment_length)
                        self.logger.info(f"添加传统偏移: {segment_start_offset}秒, 原始时间: {adjusted_segment['start']:.1f}s")
                        adjusted_segment['start'] += segment_start_offset
                        adjusted_segment['end'] += segment_start_offset
                        self.logger.info(f"添加偏移后: {adjusted_segment['start']:.1f}s-{adjusted_segment['end']:.1f}s")
                    
                    # 更新seek值
                    if 'seek' in adjusted_segment:
                        adjusted_segment['seek'] = int(adjusted_segment['start'] * 100)
                    
                    # 更新段落ID
                    adjusted_segment['id'] = len(all_segments)
                    
                    # 调整单词时间戳（如果有）
                    if 'words' in adjusted_segment:
                        for word in adjusted_segment['words']:
                            if 'start' in word and 'end' in word:
                                # 对于单词时间戳，需要加上同样的偏移
                                if 'absolute_start' not in segment:  # 只有在没有绝对时间时才需要调整
                                    segment_start_offset = result.get('segment_start_offset', i * segment_length)
                                    word['start'] += segment_start_offset
                                    word['end'] += segment_start_offset
                    
                    all_segments.append(adjusted_segment)
            else:
                # 如果没有segments，为该片段创建一个占位时间段，保持时间轴连续性
                segment_start_offset = result.get('segment_start_offset', i * segment_length)
                segment_duration = result.get('segment_duration', segment_length)
                
                # 判断是否为静音片段
                is_silent = not text_content or text_content == ''
                
                placeholder_segment = {
                    'id': len(all_segments),
                    'seek': int(segment_start_offset * 100),
                    'start': segment_start_offset,
                    'end': segment_start_offset + segment_duration,
                    'text': text_content if text_content else '',  # 静音片段为空文本
                    'tokens': [],
                    'temperature': 0.0,
                    'avg_logprob': -1.0 if text_content else -2.0,  # 静音片段更低的概率
                    'compression_ratio': 1.0,
                    'no_speech_prob': 0.95 if is_silent else 0.1,  # 静音片段高概率无语音
                    'timestamp_source': 'silent' if is_silent else 'placeholder'
                }
                all_segments.append(placeholder_segment)
                
                self.logger.info(f"片段 {i+1} {'为静音片段' if is_silent else '无segments数据'}，创建占位时间段: {segment_start_offset:.1f}s-{segment_start_offset + segment_duration:.1f}s")
        
        # 创建合并结果
        # 过滤空的文本片段，但保留所有segments以维持时间轴完整性
        merged_result = {
            'text': ' '.join(all_text_parts),
            'segments': all_segments,
            'language': detected_language or 'zh',
            'engine': detected_engine or 'unknown'
        }
        
        self.logger.info(f"分段转录完成，检测到语言: {detected_language}, 文本长度: {len(merged_result['text'])}, 使用引擎: {detected_engine}")
        
        return merged_result
    
    def transcribe_with_fallback(self, audio_path: str, language: Optional[str] = None, preferred_engine: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        使用回退机制转录音频
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
            preferred_engine: 首选引擎
            
        Returns:
            转录结果，如果使用Whisper引擎返回None
        """
        # 确定尝试顺序
        engines_to_try = []
        if preferred_engine:
            engines_to_try.append(preferred_engine)
        
        if self.enable_fallback:
            for engine in self.fallback_order:
                if engine not in engines_to_try:
                    engines_to_try.append(engine)
        
        # 依次尝试每个引擎
        last_error = None
        for engine in engines_to_try:
            try:
                self.logger.info(f"尝试使用 {engine} 引擎转录")
                result = self.transcribe_with_engine(audio_path, engine, language)
                
                if result is None and engine == 'whisper':
                    # 返回None让调用方使用本地Whisper
                    return None
                
                if result:
                    self.logger.info(f"转录成功，使用引擎: {engine}")
                    return result
                    
            except Exception as e:
                last_error = e
                self.logger.warning(f"引擎 {engine} 转录失败: {str(e)}")
                continue
        
        # 所有引擎都失败
        if last_error:
            raise RuntimeError(f"所有转录引擎都失败，最后错误: {str(last_error)}")
        else:
            raise RuntimeError("没有可用的转录引擎")