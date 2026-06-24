"""
配置加载器模块
用于加载和管理应用配置
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or self._find_config_file()
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
        self.load_config()
    
    def _find_config_file(self) -> str:
        """查找配置文件"""
        possible_paths = [
            "config.yaml",
            "config.yml",
            os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml"),
            os.path.join(os.path.dirname(__file__), "..", "..", "config.yml"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("找不到配置文件 config.yaml 或 config.yml")
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
            
            self.logger.info(f"配置文件加载成功: {self.config_path}")
            
        except Exception as e:
            error_msg = f"配置文件加载失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持嵌套键（如 'whisper.model_size'）
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def get_ffmpeg_config(self) -> Dict[str, Any]:
        """获取 FFmpeg 配置"""
        return self.get('ffmpeg', {})
    
    def get_whisper_config(self) -> Dict[str, Any]:
        """获取 Whisper 配置"""
        return self.get('whisper', {})
    
    def get_whisper_basic_config(self) -> Dict[str, Any]:
        """
        获取 Whisper 基础配置（过滤掉优化参数）
        
        Returns:
            基础配置字典
        """
        whisper_config = self.get_whisper_config()
        transcription_config = whisper_config.get('transcription', {})
        
        # 检查是否启用基础模式
        basic_mode = transcription_config.get('basic_mode', False)
        
        if basic_mode:
            # 基础模式：只使用Whisper默认参数 + 简单提示词
            basic_transcription_config = {
                'language': transcription_config.get('language', 'zh'),
                'task': transcription_config.get('task', 'transcribe'),
                'temperature': transcription_config.get('temperature', 0.0),
                'word_timestamps': transcription_config.get('word_timestamps', True),
                'initial_prompt': transcription_config.get('initial_prompt', ''),
                'verbose': transcription_config.get('verbose', False),
                # 其他参数使用Whisper默认值
                'condition_on_previous_text': False,  # Whisper默认为True，但基础模式关闭
                'suppress_tokens': [-1],  # 使用Whisper默认抑制
                'no_speech_threshold': 0.6,  # Whisper默认值
                'logprob_threshold': -1.0,
                'compression_ratio_threshold': 2.4,
                'prepend_punctuations': "\"'([{-",
                'append_punctuations': "\"'.。,，!！?？:：)]}、"
            }
            
            # 返回基础配置
            basic_config = whisper_config.copy()
            basic_config['transcription'] = basic_transcription_config
            return basic_config
        else:
            # 完整模式：使用所有配置参数
            return whisper_config
    
    def get_device_config(self) -> Dict[str, Any]:
        """
        获取设备配置，兼容旧格式
        
        Returns:
            设备配置字典
        """
        whisper_config = self.get_whisper_config()
        
        # 新格式：使用device_config
        if 'device_config' in whisper_config:
            return whisper_config['device_config']
        
        # 旧格式兼容：使用device字段
        device = whisper_config.get('device', 'auto')
        return {
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
    
    def get_subtitle_config(self) -> Dict[str, Any]:
        """获取字幕配置"""
        return self.get('subtitle', {})
    
    def get_processing_config(self) -> Dict[str, Any]:
        """获取处理配置"""
        return self.get('processing', {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """获取输出配置"""
        return self.get('output', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get('logging', {})


def setup_logging(config: ConfigLoader) -> None:
    """
    设置日志配置
    
    Args:
        config: 配置加载器
    """
    logging_config = config.get_logging_config()
    
    level = getattr(logging, logging_config.get('level', 'INFO').upper(), logging.INFO)
    log_format = logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 基础配置
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[]
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # 彩色日志
    if logging_config.get('colored', True):
        try:
            import colorlog
            formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(formatter)
        except ImportError:
            console_handler.setFormatter(logging.Formatter(log_format))
    else:
        console_handler.setFormatter(logging.Formatter(log_format))
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    log_file = logging_config.get('log_file')
    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(file_handler)
        except Exception as e:
            logging.warning(f"无法创建日志文件处理器: {str(e)}")
    
    # 设置第三方库日志级别
    logging.getLogger('ffmpeg').setLevel(logging.WARNING)
    logging.getLogger('whisper').setLevel(logging.WARNING)
    logging.getLogger('torch').setLevel(logging.WARNING)