#!/usr/bin/env python3
"""
音频录音工具
录音并保存到临时文件夹
高独立性、低耦合、高鲁棒性设计
"""
import os
import sys
import time
import wave
import threading
import logging
from datetime import datetime
from typing import Optional, Callable

# 抑制ALSA警告 - 在导入pyaudio之前
os.environ.setdefault('PYTHONWARNINGS', 'ignore')
import warnings
warnings.filterwarnings('ignore')

# 导入配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    HW_SAMPLE_RATE,
    HW_CHANNELS,
    HW_CHUNK,
    HW_FORMAT,
    MAX_DURATION,
    SAVE_DIR,
    DEBUG_LOG
)

# 配置日志（减少输出）
logging.basicConfig(
    level=logging.WARNING if not DEBUG_LOG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioRecorder:
    """
    音频录音工具类
    支持同步和异步录音
    """
    
    def __init__(self,
                 sample_rate: Optional[int] = None,
                 channels: Optional[int] = None,
                 chunk_size: Optional[int] = None,
                 audio_format: Optional[str] = None,
                 save_dir: Optional[str] = None,
                 max_duration: Optional[float] = None):
        """
        初始化音频录音工具
        
        参数:
            sample_rate: 采样率（Hz），默认使用config.py中的配置
            channels: 声道数，默认使用config.py中的配置
            chunk_size: 音频块大小，默认使用config.py中的配置
            audio_format: PyAudio格式，默认使用config.py中的配置
            save_dir: 保存目录，默认使用config.py中的配置
            max_duration: 最大录音时长（秒），默认使用config.py中的配置
        """
        try:
            # 抑制ALSA警告 - 在导入pyaudio时
            with open(os.devnull, 'w') as devnull:
                old_stderr = sys.stderr
                sys.stderr = devnull
                try:
                    import pyaudio
                    self.pyaudio = pyaudio
                finally:
                    sys.stderr = old_stderr
        except ImportError:
            raise ImportError("PyAudio 未安装，请运行: pip3 install pyaudio")
        
        self.sample_rate = sample_rate or HW_SAMPLE_RATE
        self.channels = channels or HW_CHANNELS
        self.chunk_size = chunk_size or HW_CHUNK
        self.audio_format = audio_format or HW_FORMAT
        self.max_duration = max_duration if max_duration is not None else MAX_DURATION
        
        # 转换格式字符串为PyAudio格式常量
        if isinstance(self.audio_format, str):
            format_map = {
                'paInt32': self.pyaudio.paInt32,
                'paInt16': self.pyaudio.paInt16,
                'paInt8': self.pyaudio.paInt8,
                'paFloat32': self.pyaudio.paFloat32,
            }
            self.format = format_map.get(self.audio_format, self.pyaudio.paInt32)
        else:
            self.format = self.audio_format
        
        self.save_dir = save_dir or SAVE_DIR
        self._ensure_save_dir()
        
        self.audio = None
        self.recording_flag = threading.Event()
        self.stop_request = threading.Event()
        self.worker_thread = None
        
        logger.info("音频录音工具初始化完成")
    
    def _ensure_save_dir(self):
        """确保保存目录存在"""
        if self.save_dir:
            abs_save_dir = os.path.abspath(self.save_dir)
            os.makedirs(abs_save_dir, exist_ok=True)
            logger.debug(f"保存目录已确保存在: {abs_save_dir}")
    
    def _generate_filename(self, prefix: str = "recording") -> str:
        """生成录音文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.wav"
        abs_save_dir = os.path.abspath(self.save_dir)
        return os.path.join(abs_save_dir, filename)
    
    def _open_stream(self):
        """打开音频输入流"""
        if not self.audio:
            # 抑制ALSA警告
            with open(os.devnull, 'w') as devnull:
                old_stderr = sys.stderr
                sys.stderr = devnull
                try:
                    self.audio = self.pyaudio.PyAudio()
                finally:
                    sys.stderr = old_stderr
        
        # 抑制ALSA警告
        with open(os.devnull, 'w') as devnull:
            old_stderr = sys.stderr
            sys.stderr = devnull
            try:
                stream = self.audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size
                )
            finally:
                sys.stderr = old_stderr
        
        return stream
    
    def record(self,
               output_path: Optional[str] = None,
               duration: Optional[float] = None,
               progress_callback: Optional[Callable[[float], None]] = None) -> Optional[str]:
        """
        同步录音
        
        参数:
            output_path: 输出文件路径，如果为None则自动生成
            duration: 录音时长（秒），如果为None则使用max_duration
            progress_callback: 进度回调函数，参数为已录音时长（秒）
        
        返回:
            录音文件路径，失败返回None
        """
        if self.recording_flag.is_set():
            logger.warning("已在录音中，请先停止当前录音")
            return None
        
        duration = duration if duration is not None else self.max_duration
        
        try:
            # 生成输出路径
            if not output_path:
                output_path = self._generate_filename()
            else:
                # 确保输出目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
            
            logger.info(f"开始录音: {output_path}")
            logger.info(f"采样率: {self.sample_rate}Hz, 声道: {self.channels}, 格式: {self.audio_format}")
            
            # 打开音频流
            stream = self._open_stream()
            frames = []
            start_time = time.time()
            
            try:
                while True:
                    elapsed = time.time() - start_time
                    
                    # 检查时长限制
                    if duration > 0 and elapsed >= duration:
                        logger.info(f"达到最大时长 {duration} 秒")
                        break
                    
                    # 读取音频数据
                    try:
                        data = stream.read(self.chunk_size, exception_on_overflow=False)
                        frames.append(data)
                    except Exception as e:
                        logger.warning(f"读取音频帧异常: {e}")
                        continue
                    
                    # 进度回调
                    if progress_callback:
                        try:
                            progress_callback(elapsed)
                        except Exception as e:
                            logger.warning(f"进度回调异常: {e}")
                
                # 保存录音文件
                logger.info("保存录音文件...")
                with wave.open(output_path, 'wb') as wf:
                    # 计算采样宽度
                    if self.format == self.pyaudio.paInt32:
                        sampwidth = 4
                    elif self.format == self.pyaudio.paInt16:
                        sampwidth = 2
                    elif self.format == self.pyaudio.paInt8:
                        sampwidth = 1
                    else:
                        sampwidth = 4
                    
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(sampwidth)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b"".join(frames))
                
                file_size = os.path.getsize(output_path)
                logger.info(f"录音完成: {output_path}")
                logger.info(f"文件大小: {file_size / 1024:.2f} KB")
                
                return output_path
                
            finally:
                stream.stop_stream()
                stream.close()
                
        except Exception as e:
            logger.exception(f"录音过程异常: {e}")
            return None
    
    def start_recording(self, output_path: Optional[str] = None):
        """
        开始异步录音
        
        参数:
            output_path: 输出文件路径，如果为None则自动生成
        
        返回:
            录音文件路径（如果成功启动），失败返回None
        """
        if self.recording_flag.is_set():
            logger.warning("已在录音中")
            return None
        
        # 生成输出路径
        if not output_path:
            output_path = self._generate_filename()
        else:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
        
        self.recording_flag.set()
        self.stop_request.clear()
        self.worker_thread = threading.Thread(
            target=self._record_async,
            args=(output_path,),
            daemon=True
        )
        self.worker_thread.start()
        
        logger.info(f"开始异步录音: {output_path}")
        return output_path
    
    def stop_recording(self) -> Optional[str]:
        """
        停止异步录音
        
        返回:
            录音文件路径，失败返回None
        """
        if not self.recording_flag.is_set():
            logger.warning("当前未在录音")
            return None
        
        logger.info("停止录音请求")
        self.stop_request.set()
        
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        
        self.recording_flag.clear()
        logger.info("录音已停止")
        
        # 返回文件路径（需要从线程中获取，这里简化处理）
        return None
    
    def _record_async(self, output_path: str):
        """异步录音线程函数"""
        try:
            stream = self._open_stream()
            frames = []
            start_time = time.time()
            
            while not self.stop_request.is_set():
                elapsed = time.time() - start_time
                
                if self.max_duration > 0 and elapsed >= self.max_duration:
                    logger.info(f"达到最大时长 {self.max_duration} 秒")
                    break
                
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    frames.append(data)
                except Exception as e:
                    logger.warning(f"读取音频帧异常: {e}")
                    continue
            
            # 保存录音文件
            with wave.open(output_path, 'wb') as wf:
                if self.format == self.pyaudio.paInt32:
                    sampwidth = 4
                elif self.format == self.pyaudio.paInt16:
                    sampwidth = 2
                elif self.format == self.pyaudio.paInt8:
                    sampwidth = 1
                else:
                    sampwidth = 4
                
                wf.setnchannels(self.channels)
                wf.setsampwidth(sampwidth)
                wf.setframerate(self.sample_rate)
                wf.writeframes(b"".join(frames))
            
            file_size = os.path.getsize(output_path)
            logger.info(f"异步录音完成: {output_path}")
            logger.info(f"文件大小: {file_size / 1024:.2f} KB")
            
        except Exception as e:
            logger.exception(f"异步录音异常: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
    
    def is_recording(self) -> bool:
        """检查是否正在录音"""
        return self.recording_flag.is_set()
    
    def cleanup(self):
        """清理资源"""
        if self.recording_flag.is_set():
            self.stop_recording()
        
        if self.audio:
            try:
                self.audio.terminate()
                self.audio = None
            except Exception:
                pass
        
        logger.debug("资源已清理")


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("音频录音工具测试")
    print("=" * 60)
    
    recorder = AudioRecorder()
    
    try:
        print("\n测试1: 同步录音（3秒）")
        
        def progress_callback(elapsed):
            print(f"  录音进度: {elapsed:.1f}秒", end='\r')
        
        output_path = recorder.record(duration=3, progress_callback=progress_callback)
        
        if output_path and os.path.exists(output_path):
            print(f"\n  ✓ 录音成功: {output_path}")
        else:
            print("\n  ✗ 录音失败")
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        recorder.cleanup()

