"""
SRT 字幕生成器模块
将语音识别结果转换为 SRT 字幕格式
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import pysrt


class SRTGenerator:
    """SRT 字幕生成器"""
    
    def __init__(self):
        """初始化 SRT 生成器"""
        self.logger = logging.getLogger(__name__)
    
    def generate_srt_from_whisper(
        self,
        whisper_result: Dict,
        output_path: str,
        max_line_length: int = 80,
        max_lines_per_subtitle: int = 2,
        min_subtitle_duration: float = 1.0,
        max_subtitle_duration: float = 10.0,
        merge_threshold: float = 0.5,
        encoding: str = 'utf-8'
    ) -> str:
        """
        从 Whisper 结果生成 SRT 字幕文件
        
        Args:
            whisper_result: Whisper 转录结果
            output_path: 输出 SRT 文件路径
            max_line_length: 每行最大字符数
            max_lines_per_subtitle: 每个字幕最大行数
            min_subtitle_duration: 最小字幕持续时间（秒）
            max_subtitle_duration: 最大字幕持续时间（秒）
            merge_threshold: 相邻字幕合并阈值（秒）
            encoding: 文件编码
            
        Returns:
            生成的 SRT 文件路径
        """
        try:
            # 检查输入数据
            if not whisper_result or 'segments' not in whisper_result:
                raise ValueError("无效的 Whisper 结果")
            
            segments = whisper_result['segments']
            if not segments:
                raise ValueError("Whisper 结果中没有分段信息")
            
            self.logger.info(f"开始生成 SRT 字幕，共 {len(segments)} 个分段")
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 预处理分段
            processed_segments = self._preprocess_segments(
                segments,
                min_subtitle_duration,
                max_subtitle_duration,
                merge_threshold
            )
            
            # 创建 SRT 字幕项
            srt_items = []
            for i, segment in enumerate(processed_segments):
                subtitle_items = self._create_subtitle_items(
                    segment,
                    i + 1,
                    max_line_length,
                    max_lines_per_subtitle
                )
                srt_items.extend(subtitle_items)
            
            # 重新编号
            for i, item in enumerate(srt_items):
                item.index = i + 1
            
            # 保存 SRT 文件
            self._save_srt_file(srt_items, output_path, encoding)
            
            self.logger.info(f"SRT 字幕生成成功: {output_path}")
            self.logger.info(f"共生成 {len(srt_items)} 个字幕项")
            
            return output_path
            
        except Exception as e:
            error_msg = f"SRT 字幕生成失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def generate_srt_from_segments(
        self,
        segment_results: List[Dict],
        output_path: str,
        segment_duration: float = 300.0,
        **kwargs
    ) -> str:
        """
        从多个分段结果生成 SRT 字幕
        
        Args:
            segment_results: 分段转录结果列表
            output_path: 输出 SRT 文件路径
            segment_duration: 每个分段的时长（秒）
            **kwargs: 其他参数
            
        Returns:
            生成的 SRT 文件路径
        """
        try:
            all_segments = []
            current_offset = 0.0
            
            for i, result in enumerate(segment_results):
                if 'segments' in result and result['segments']:
                    # 调整时间戳
                    for segment in result['segments']:
                        adjusted_segment = segment.copy()
                        adjusted_segment['start'] = segment['start'] + current_offset
                        adjusted_segment['end'] = segment['end'] + current_offset
                        
                        # 调整单词级时间戳
                        if 'words' in adjusted_segment:
                            for word in adjusted_segment['words']:
                                word['start'] = word['start'] + current_offset
                                word['end'] = word['end'] + current_offset
                        
                        all_segments.append(adjusted_segment)
                
                current_offset += segment_duration
            
            # 创建合并的结果
            merged_result = {
                'segments': all_segments,
                'text': ' '.join([seg.get('text', '') for seg in all_segments]),
                'language': segment_results[0].get('language', 'unknown') if segment_results else 'unknown'
            }
            
            return self.generate_srt_from_whisper(merged_result, output_path, **kwargs)
            
        except Exception as e:
            error_msg = f"从分段结果生成 SRT 失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _preprocess_segments(
        self,
        segments: List[Dict],
        min_duration: float,
        max_duration: float,
        merge_threshold: float
    ) -> List[Dict]:
        """
        预处理分段，合并过短的分段，分割过长的分段
        
        Args:
            segments: 原始分段列表
            min_duration: 最小持续时间
            max_duration: 最大持续时间
            merge_threshold: 合并阈值
            
        Returns:
            处理后的分段列表
        """
        if not segments:
            return []
        
        processed = []
        
        for segment in segments:
            duration = segment['end'] - segment['start']
            
            # 如果分段太长，尝试分割
            if duration > max_duration:
                split_segments = self._split_long_segment(segment, max_duration)
                processed.extend(split_segments)
            else:
                processed.append(segment)
        
        # 合并过短的相邻分段
        merged = []
        i = 0
        while i < len(processed):
            current = processed[i]
            current_duration = current['end'] - current['start']
            
            # 如果当前分段太短，尝试与下一个合并
            if (current_duration < min_duration and 
                i + 1 < len(processed) and
                processed[i + 1]['start'] - current['end'] <= merge_threshold):
                
                next_segment = processed[i + 1]
                merged_segment = {
                    'start': current['start'],
                    'end': next_segment['end'],
                    'text': current['text'] + ' ' + next_segment['text']
                }
                
                # 合并单词级时间戳
                if 'words' in current and 'words' in next_segment:
                    merged_segment['words'] = current['words'] + next_segment['words']
                
                merged.append(merged_segment)
                i += 2  # 跳过下一个分段
            else:
                merged.append(current)
                i += 1
        
        return merged
    
    def _split_long_segment(self, segment: Dict, max_duration: float) -> List[Dict]:
        """
        分割过长的分段
        
        Args:
            segment: 要分割的分段
            max_duration: 最大持续时间
            
        Returns:
            分割后的分段列表
        """
        duration = segment['end'] - segment['start']
        if duration <= max_duration:
            return [segment]
        
        # 如果有单词级时间戳，按单词分割
        if 'words' in segment and segment['words']:
            return self._split_by_words(segment, max_duration)
        
        # 否则按时间均匀分割
        return self._split_by_time(segment, max_duration)
    
    def _split_by_words(self, segment: Dict, max_duration: float) -> List[Dict]:
        """
        基于单词边界分割分段
        
        Args:
            segment: 要分割的分段
            max_duration: 最大持续时间
            
        Returns:
            分割后的分段列表
        """
        words = segment['words']
        if not words:
            return [segment]
        
        splits = []
        current_start = segment['start']
        current_words = []
        current_text_parts = []
        
        for word in words:
            word_end = word.get('end', word.get('start', current_start))
            
            # 检查添加这个单词是否会超过最大持续时间
            if (word_end - current_start) > max_duration and current_words:
                # 创建当前分段
                split_segment = {
                    'start': current_start,
                    'end': current_words[-1].get('end', current_words[-1].get('start', current_start)),
                    'text': ' '.join(current_text_parts),
                    'words': current_words
                }
                splits.append(split_segment)
                
                # 开始新的分段
                current_start = word.get('start', current_start)
                current_words = [word]
                current_text_parts = [word.get('word', '')]
            else:
                current_words.append(word)
                current_text_parts.append(word.get('word', ''))
        
        # 添加最后一个分段
        if current_words:
            split_segment = {
                'start': current_start,
                'end': segment['end'],
                'text': ' '.join(current_text_parts),
                'words': current_words
            }
            splits.append(split_segment)
        
        return splits if splits else [segment]
    
    def _split_by_time(self, segment: Dict, max_duration: float) -> List[Dict]:
        """
        基于时间均匀分割分段
        
        Args:
            segment: 要分割的分段
            max_duration: 最大持续时间
            
        Returns:
            分割后的分段列表
        """
        duration = segment['end'] - segment['start']
        num_splits = int(duration / max_duration) + 1
        split_duration = duration / num_splits
        
        splits = []
        text_parts = segment['text'].split()
        words_per_split = max(1, len(text_parts) // num_splits)
        
        for i in range(num_splits):
            start_time = segment['start'] + i * split_duration
            end_time = min(segment['start'] + (i + 1) * split_duration, segment['end'])
            
            # 分配文本
            start_word_idx = i * words_per_split
            end_word_idx = min((i + 1) * words_per_split, len(text_parts))
            if i == num_splits - 1:  # 最后一个分段包含剩余所有文本
                end_word_idx = len(text_parts)
            
            split_text = ' '.join(text_parts[start_word_idx:end_word_idx])
            
            split_segment = {
                'start': start_time,
                'end': end_time,
                'text': split_text
            }
            splits.append(split_segment)
        
        return splits
    
    def _create_subtitle_items(
        self,
        segment: Dict,
        base_index: int,
        max_line_length: int,
        max_lines: int
    ) -> List[pysrt.SubRipItem]:
        """
        创建字幕项
        
        Args:
            segment: 分段数据
            base_index: 基础索引
            max_line_length: 最大行长度
            max_lines: 最大行数
            
        Returns:
            字幕项列表
        """
        text = segment['text'].strip()
        if not text:
            return []
        
        # 分割文本为多行
        lines = self._split_text_to_lines(text, max_line_length, max_lines)
        
        # 计算时间戳
        start_time = self._seconds_to_timedelta(segment['start'])
        end_time = self._seconds_to_timedelta(segment['end'])
        
        # 如果只有一个分组，创建单个字幕项
        if len(lines) == 1:
            item = pysrt.SubRipItem(
                index=base_index,
                start=start_time,
                end=end_time,
                text='\n'.join(lines[0])
            )
            return [item]
        
        # 多个分组，按时间分配
        items = []
        total_duration = segment['end'] - segment['start']
        duration_per_group = total_duration / len(lines)
        
        for i, line_group in enumerate(lines):
            group_start = segment['start'] + i * duration_per_group
            group_end = segment['start'] + (i + 1) * duration_per_group
            
            item = pysrt.SubRipItem(
                index=base_index + i,
                start=self._seconds_to_timedelta(group_start),
                end=self._seconds_to_timedelta(group_end),
                text='\n'.join(line_group)
            )
            items.append(item)
        
        return items
    
    def _split_text_to_lines(
        self,
        text: str,
        max_line_length: int,
        max_lines: int
    ) -> List[List[str]]:
        """
        将文本分割为适合的行
        
        Args:
            text: 要分割的文本
            max_line_length: 每行最大长度
            max_lines: 每组最大行数
            
        Returns:
            行分组列表
        """
        # 基本的文本分割逻辑
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            # 检查是否需要换行
            if current_length + word_length + len(current_line) > max_line_length and current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
            else:
                current_line.append(word)
                current_length += word_length
        
        # 添加最后一行
        if current_line:
            lines.append(' '.join(current_line))
        
        # 将行分组
        groups = []
        for i in range(0, len(lines), max_lines):
            groups.append(lines[i:i + max_lines])
        
        return groups
    
    def _seconds_to_timedelta(self, seconds: float) -> pysrt.SubRipTime:
        """
        将秒数转换为 SRT 时间格式
        
        Args:
            seconds: 秒数
            
        Returns:
            SRT 时间对象
        """
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return pysrt.SubRipTime(
            hours=hours,
            minutes=minutes,
            seconds=secs,
            milliseconds=milliseconds
        )
    
    def _save_srt_file(
        self,
        srt_items: List[pysrt.SubRipItem],
        output_path: str,
        encoding: str
    ) -> None:
        """
        保存 SRT 文件
        
        Args:
            srt_items: SRT 字幕项列表
            output_path: 输出文件路径
            encoding: 文件编码
        """
        try:
            srt_file = pysrt.SubRipFile(srt_items)
            srt_file.save(output_path, encoding=encoding)
            
            # 验证文件
            if not os.path.exists(output_path):
                raise RuntimeError("SRT 文件保存失败")
            
            file_size = os.path.getsize(output_path)
            self.logger.info(f"SRT 文件已保存: {output_path} ({file_size} 字节)")
            
        except Exception as e:
            error_msg = f"保存 SRT 文件失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def validate_srt_file(self, srt_path: str) -> Dict:
        """
        验证 SRT 文件
        
        Args:
            srt_path: SRT 文件路径
            
        Returns:
            验证结果字典
        """
        try:
            srt_file = pysrt.open(srt_path)
            
            result = {
                'valid': True,
                'subtitle_count': len(srt_file),
                'total_duration': 0.0,
                'errors': []
            }
            
            if srt_file:
                last_item = srt_file[-1]
                result['total_duration'] = (
                    last_item.end.hours * 3600 +
                    last_item.end.minutes * 60 +
                    last_item.end.seconds +
                    last_item.end.milliseconds / 1000.0
                )
            
            return result
            
        except Exception as e:
            return {
                'valid': False,
                'subtitle_count': 0,
                'total_duration': 0.0,
                'errors': [str(e)]
            }