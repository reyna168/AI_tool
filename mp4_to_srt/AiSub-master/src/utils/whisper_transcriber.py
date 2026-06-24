"""
Whisper 语音识别模块
使用 OpenAI Whisper 模型进行语音转文本
"""

import os
import logging
import torch
import whisper
from typing import Dict, List, Optional, Union
from pathlib import Path
from tqdm import tqdm
import warnings

# 忽略一些不重要的警告
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


class WhisperTranscriber:
    """Whisper 语音识别器"""
    
    # 可用的模型大小和对应的参数
    MODEL_SIZES = {
        'tiny': {'params': '39M', 'vram': '~1GB', 'speed': '~32x'},
        'base': {'params': '74M', 'vram': '~1GB', 'speed': '~16x'}, 
        'small': {'params': '244M', 'vram': '~2GB', 'speed': '~6x'},
        'medium': {'params': '769M', 'vram': '~5GB', 'speed': '~2x'},
        'large': {'params': '1550M', 'vram': '~10GB', 'speed': '~1x'},
        'large-v2': {'params': '1550M', 'vram': '~10GB', 'speed': '~1x'},
        'large-v3': {'params': '1550M', 'vram': '~10GB', 'speed': '~1x'}
    }
    
    def __init__(
        self, 
        model_size: str = "base",
        device: Optional[str] = None,
        download_root: Optional[str] = None,
        device_config: Optional[Dict] = None
    ):
        """
        初始化 Whisper 转录器
        
        Args:
            model_size: 模型大小 (tiny, base, small, medium, large, large-v2, large-v3)
            device: 设备类型 (cuda, cpu, auto)
            download_root: 模型下载目录
            device_config: 详细设备配置字典
        """
        self.model_size = model_size
        self.logger = logging.getLogger(__name__)
        self.device_config = device_config or {}
        
        # 设备选择逻辑
        self.device = self._select_device(device)
        
        # 设置CUDA配置
        self._setup_cuda_config()
        
        self.logger.info(f"使用设备: {self.device}")
        
        # 设置模型下载目录
        if download_root:
            os.environ["XDG_CACHE_HOME"] = download_root
        
        # 加载模型
        self.model = None
        self._load_model()
    
    def _select_device(self, device: Optional[str]) -> str:
        """
        选择计算设备
        
        Args:
            device: 指定的设备类型
            
        Returns:
            最终选择的设备
        """
        # 优先使用传入的device参数，其次使用device_config
        preferred_device = device or self.device_config.get('preferred_device', 'auto')
        
        if preferred_device == "auto":
            return self._auto_detect_device()
        elif preferred_device == "cuda":
            return self._setup_cuda_device()
        elif preferred_device == "cpu":
            return self._setup_cpu_device()
        else:
            self.logger.warning(f"未知设备类型: {preferred_device}，使用自动检测")
            return self._auto_detect_device()
    
    def _auto_detect_device(self) -> str:
        """自动检测最佳设备"""
        cuda_config = self.device_config.get('cuda', {})
        
        if cuda_config.get('enabled', True) and torch.cuda.is_available():
            self.logger.info("检测到 NVIDIA CUDA 支持")
            return "cuda"
        else:
            self.logger.info("未检测到 CUDA 支持，使用 CPU")
            # 检查 AMD GPU
            try:
                import subprocess
                result = subprocess.run(['rocm-smi'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
                if result.returncode == 0:
                    self.logger.info("检测到 AMD GPU，但 Whisper 不支持 ROCm，使用 CPU")
            except:
                pass
            return "cpu"
    
    def _setup_cuda_device(self) -> str:
        """设置CUDA设备"""
        if not torch.cuda.is_available():
            self.logger.warning("CUDA 不可用，回退到 CPU")
            return "cpu"
        
        cuda_config = self.device_config.get('cuda', {})
        
        # 设置设备ID
        device_id = cuda_config.get('device_id', -1)
        if device_id >= 0 and device_id < torch.cuda.device_count():
            torch.cuda.set_device(device_id)
            self.logger.info(f"使用 CUDA 设备 {device_id}")
            return f"cuda:{device_id}"
        else:
            self.logger.info("使用默认 CUDA 设备")
            return "cuda"
    
    def _setup_cpu_device(self) -> str:
        """设置CPU设备"""
        cpu_config = self.device_config.get('cpu', {})
        
        # 设置CPU线程数
        num_threads = cpu_config.get('num_threads', 0)
        if num_threads > 0:
            torch.set_num_threads(num_threads)
            self.logger.info(f"设置 CPU 线程数: {num_threads}")
        
        return "cpu"
    
    def _setup_cuda_config(self) -> None:
        """设置CUDA相关配置"""
        if not self.device.startswith("cuda"):
            return
        
        cuda_config = self.device_config.get('cuda', {})
        
        # 设置内存分配策略
        if cuda_config.get('allow_growth', True):
            # 允许内存增长，避免预先分配所有内存
            os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
            self.logger.debug("启用 CUDA 内存动态分配")
        
        # 设置内存分数（如果指定）
        memory_fraction = cuda_config.get('memory_fraction', 0)
        if memory_fraction > 0 and memory_fraction <= 1.0:
            # PyTorch中没有直接的memory_fraction设置，这里只记录日志
            self.logger.info(f"指定 CUDA 内存分数: {memory_fraction:.2f}")
    
    def _load_model(self) -> None:
        """加载 Whisper 模型"""
        try:
            self.logger.info(f"正在加载 Whisper {self.model_size} 模型...")
            
            # 检查模型大小是否有效
            if self.model_size not in self.MODEL_SIZES:
                available_models = ", ".join(self.MODEL_SIZES.keys())
                raise ValueError(f"无效的模型大小: {self.model_size}。可用模型: {available_models}")
            
            # 显示模型信息
            model_info = self.MODEL_SIZES[self.model_size]
            self.logger.info(f"模型参数: {model_info['params']}, 预计显存: {model_info['vram']}, 相对速度: {model_info['speed']}")
            
            # 加载模型
            self.model = whisper.load_model(self.model_size, device=self.device)
            
            self.logger.info(f"Whisper {self.model_size} 模型加载成功")
            
        except Exception as e:
            error_msg = f"模型加载失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def transcribe_audio(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        temperature: float = 0.0,
        beam_size: Optional[int] = None,
        best_of: Optional[int] = None,
        patience: Optional[float] = None,
        condition_on_previous_text: bool = True,
        initial_prompt: Optional[str] = None,
        word_timestamps: bool = True,
        prepend_punctuations: str = "\"'([{-",
        append_punctuations: str = "\"'.。,，!！?？:：)]}、",
        suppress_blank: bool = True,
        suppress_tokens: Optional[List[int]] = None,
        without_timestamps: bool = False,
        max_initial_timestamp: Optional[float] = None,
        no_speech_threshold: Optional[float] = None,
        logprob_threshold: Optional[float] = None,
        compression_ratio_threshold: Optional[float] = None,
        verbose: bool = False
    ) -> Dict:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码 (如 'zh', 'en', 'ja' 等)，None 为自动检测
            task: 任务类型 ('transcribe' 或 'translate')
            temperature: 温度参数，控制随机性 (0.0-1.0)
            beam_size: 束搜索大小
            best_of: 最佳候选数量
            patience: 耐心参数
            condition_on_previous_text: 是否基于前文进行条件化
            initial_prompt: 初始提示文本
            word_timestamps: 是否包含单词级时间戳
            prepend_punctuations: 前置标点符号
            append_punctuations: 后置标点符号
            suppress_blank: 是否抑制空白
            suppress_tokens: 要抑制的token列表
            without_timestamps: 是否不包含时间戳
            max_initial_timestamp: 最大初始时间戳
            verbose: 是否显示详细信息
            
        Returns:
            包含转录结果的字典
        """
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
            if self.model is None:
                raise RuntimeError("模型未加载")
            
            self.logger.info(f"开始转录音频: {audio_path}")
            
            # 准备转录参数
            options = {
                "language": language,
                "task": task,
                "temperature": temperature,
                "condition_on_previous_text": condition_on_previous_text,
                "word_timestamps": word_timestamps,
                "prepend_punctuations": prepend_punctuations,
                "append_punctuations": append_punctuations,
                "suppress_blank": suppress_blank,
                "without_timestamps": without_timestamps,
                "verbose": verbose
            }
            
            # 添加可选参数
            if beam_size is not None:
                options["beam_size"] = beam_size
            if best_of is not None:
                options["best_of"] = best_of
            if patience is not None:
                options["patience"] = patience
            if initial_prompt is not None:
                options["initial_prompt"] = initial_prompt
            if suppress_tokens is not None:
                options["suppress_tokens"] = suppress_tokens
            if max_initial_timestamp is not None:
                options["max_initial_timestamp"] = max_initial_timestamp
            if no_speech_threshold is not None:
                options["no_speech_threshold"] = no_speech_threshold
            if logprob_threshold is not None:
                options["logprob_threshold"] = logprob_threshold
            if compression_ratio_threshold is not None:
                options["compression_ratio_threshold"] = compression_ratio_threshold
            
            # 执行转录
            self.logger.info("开始语音识别...")
            result = self.model.transcribe(audio_path, **options)
            
            # 处理结果
            detected_language = result.get("language", "unknown")
            self.logger.info(f"转录完成，检测到语言: {detected_language}")
            self.logger.info(f"转录文本长度: {len(result.get('text', ''))}")
            
            return result
            
        except Exception as e:
            error_msg = f"音频转录失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def transcribe_segments(
        self,
        audio_segments: List[str],
        **kwargs
    ) -> List[Dict]:
        """
        转录多个音频片段
        
        Args:
            audio_segments: 音频片段文件路径列表
            **kwargs: 转录参数
            
        Returns:
            转录结果列表
        """
        results = []
        
        with tqdm(total=len(audio_segments), desc="转录音频片段") as pbar:
            for i, segment_path in enumerate(audio_segments):
                try:
                    self.logger.debug(f"转录片段 {i+1}/{len(audio_segments)}: {segment_path}")
                    
                    result = self.transcribe_audio(segment_path, **kwargs)
                    results.append(result)
                    
                    pbar.update(1)
                    pbar.set_postfix({
                        "当前片段": f"{i+1}/{len(audio_segments)}",
                        "语言": result.get("language", "unknown")
                    })
                    
                except Exception as e:
                    self.logger.error(f"转录片段 {segment_path} 失败: {str(e)}")
                    # 添加空结果以保持片段顺序
                    results.append({
                        "text": "",
                        "segments": [],
                        "language": "unknown",
                        "error": str(e)
                    })
                    pbar.update(1)
        
        return results
    
    def get_model_info(self) -> Dict:
        """
        获取当前模型信息
        
        Returns:
            模型信息字典
        """
        if self.model_size in self.MODEL_SIZES:
            model_info = self.MODEL_SIZES[self.model_size].copy()
            model_info.update({
                "model_size": self.model_size,
                "device": self.device,
                "loaded": self.model is not None
            })
            return model_info
        return {}
    
    @staticmethod
    def list_available_models() -> Dict[str, Dict]:
        """
        列出所有可用的模型
        
        Returns:
            模型信息字典
        """
        return WhisperTranscriber.MODEL_SIZES.copy()
    
    @staticmethod
    def get_basic_config() -> Dict:
        """
        获取基础的Whisper参数配置（最少的额外参数，接近原生Whisper默认配置）
        
        Returns:
            基础配置字典
        """
        return {
            'language': 'zh',
            'task': 'transcribe',
            'temperature': 0.0,
            'word_timestamps': True,
            'initial_prompt': "以下是一段中文音频的转录。",  # 只保留简单提示
            'verbose': False
            # 其他参数使用Whisper默认值，不额外指定
        }
    
    @staticmethod
    def get_chinese_optimized_config() -> Dict:
        """
        获取中文优化的Whisper参数配置
        
        Returns:
            中文优化配置字典
        """
        return {
            'language': 'zh',
            'task': 'transcribe',
            'temperature': 0.0,
            'condition_on_previous_text': True,  # 启用上下文关联，提高中文连贯性
            'initial_prompt': "以下是一段中文音频的转录。请准确识别每个字词，保持语言的连贯性和自然性。",
            'word_timestamps': True,
            'suppress_tokens': [50256, 50257, 50358, 50359, 50360],  # 精准抑制噪音token
            'no_speech_threshold': 0.5,  # 优化的语音检测阈值
            'logprob_threshold': -1.0,
            'compression_ratio_threshold': 2.4,
            'beam_size': 5,      # 增加搜索候选，提高质量
            'best_of': 5,        # 提高选择质量
            'patience': 1.0,     # 耐心参数
            'prepend_punctuations': "\"'([{-",
            'append_punctuations': "\"'.。,，!！?？:：)]}、",  # 中文标点优化
            'verbose': False
        }
    
    @staticmethod
    def get_speed_optimized_config() -> Dict:
        """
        获取速度优化的Whisper参数配置（牺牲部分质量换取速度）
        
        Returns:
            速度优化配置字典
        """
        return {
            'language': 'zh',
            'task': 'transcribe',
            'temperature': 0.0,
            'condition_on_previous_text': False,  # 关闭以提高速度
            'initial_prompt': "",                 # 清空以提高速度
            'word_timestamps': True,
            'suppress_tokens': [-1],               # 使用默认设置
            'no_speech_threshold': 0.6,
            'logprob_threshold': -1.0,
            'compression_ratio_threshold': 2.4,
            'verbose': False
        }
    
    def transcribe_with_basic_config(self, audio_path: str, **override_params) -> Dict:
        """
        使用基础配置转录音频（接近原生Whisper行为）
        
        Args:
            audio_path: 音频文件路径
            **override_params: 覆盖的参数
            
        Returns:
            转录结果字典
        """
        config = self.get_basic_config()
        config.update(override_params)
        return self.transcribe_audio(audio_path, **config)
    
    def transcribe_with_chinese_optimization(self, audio_path: str, **override_params) -> Dict:
        """
        使用中文优化配置转录音频
        
        Args:
            audio_path: 音频文件路径
            **override_params: 覆盖的参数
            
        Returns:
            转录结果字典
        """
        config = self.get_chinese_optimized_config()
        config.update(override_params)
        return self.transcribe_audio(audio_path, **config)
    
    def transcribe_with_speed_optimization(self, audio_path: str, **override_params) -> Dict:
        """
        使用速度优化配置转录音频
        
        Args:
            audio_path: 音频文件路径
            **override_params: 覆盖的参数
            
        Returns:
            转录结果字典
        """
        config = self.get_speed_optimized_config()
        config.update(override_params)
        return self.transcribe_audio(audio_path, **config)
    
    @staticmethod
    def estimate_processing_time(duration_seconds: float, model_size: str = "base") -> float:
        """
        估算处理时间
        
        Args:
            duration_seconds: 音频时长（秒）
            model_size: 模型大小
            
        Returns:
            预估处理时间（秒）
        """
        if model_size not in WhisperTranscriber.MODEL_SIZES:
            model_size = "base"
        
        # 根据模型速度倍数估算
        speed_multipliers = {
            'tiny': 32, 'base': 16, 'small': 6,
            'medium': 2, 'large': 1, 'large-v2': 1, 'large-v3': 1
        }
        
        multiplier = speed_multipliers.get(model_size, 16)
        
        # 考虑设备性能差异
        device_factor = 0.5 if torch.cuda.is_available() else 2.0
        
        estimated_time = (duration_seconds / multiplier) * device_factor
        return max(estimated_time, 1.0)  # 最少1秒
    
    def cleanup(self) -> None:
        """清理资源 - 只清理内存，不删除模型文件"""
        try:
            if self.model is not None:
                # 只从内存中卸载模型，不删除模型文件
                del self.model
                self.model = None
                self.logger.info("模型从内存中清理，模型文件已保留")
                
            # 清理 GPU 缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                self.logger.debug("GPU 缓存已清理")
                
        except Exception as e:
            self.logger.warning(f"清理资源时出现警告: {str(e)}")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()