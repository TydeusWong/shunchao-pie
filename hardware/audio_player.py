#!/usr/bin/env python3
"""
音频播放工具
支持多种音频格式的播放，使用MPV播放器
高独立性、低耦合、高鲁棒性设计
"""
import subprocess
import os
import sys
import logging
from typing import Optional, List

# 导入配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DEBUG_LOG

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if DEBUG_LOG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioPlayer:
    """
    音频播放工具类
    支持文件播放和流式播放
    """
    
    def __init__(self, audio_device: str = "pulse"):
        """
        初始化音频播放器
        
        参数:
            audio_device: 音频设备，默认"pulse"（PulseAudio）
        """
        self.audio_device = audio_device
        self.mpv_process = None
        self._mpv_installed = None
    
    def check_mpv_installed(self) -> bool:
        """检查MPV播放器是否安装"""
        if self._mpv_installed is not None:
            return self._mpv_installed
        
        try:
            result = subprocess.run(
                ['mpv', '--version'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=True
            )
            self._mpv_installed = True
            logger.debug("MPV播放器已安装")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self._mpv_installed = False
            logger.warning("MPV播放器未安装")
            return False
    
    def play_file(self, 
                  file_path: str,
                  volume: Optional[float] = None,
                  wait: bool = True,
                  delete_after_play: bool = True) -> bool:
        """
        播放音频文件
        
        参数:
            file_path: 音频文件路径
            volume: 音量（0-100），None表示使用默认
            wait: 是否等待播放完成
            delete_after_play: 播放完成后是否删除文件，默认True
        
        返回:
            成功返回True，失败返回False
        """
        if not self.check_mpv_installed():
            logger.error("MPV播放器未安装！请运行: sudo apt update && sudo apt install -y mpv")
            return False
        
        if not os.path.exists(file_path):
            logger.error(f"音频文件不存在: {file_path}")
            return False
        
        try:
            cmd = ['mpv', '--no-terminal', f'--audio-device={self.audio_device}']
            
            if volume is not None:
                cmd.extend(['--volume', str(volume)])
            
            cmd.append(file_path)
            
            logger.info(f"播放音频文件: {file_path}")
            
            if wait:
                # 等待播放完成
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=None
                )
                success = result.returncode == 0
                if success:
                    logger.info("播放完成")
                    
                    # 播放完成后删除文件
                    if delete_after_play:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                logger.info(f"已删除音频文件: {file_path}")
                            else:
                                logger.warning(f"文件不存在，无法删除: {file_path}")
                        except Exception as e:
                            logger.warning(f"删除文件失败: {file_path}, 错误: {e}")
                            # 删除失败不影响返回值
                else:
                    logger.warning(f"播放可能异常结束，返回码: {result.returncode}")
                return success
            else:
                # 后台播放
                self.mpv_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info(f"后台播放已启动，PID: {self.mpv_process.pid}")
                
                # 后台播放时不删除文件（因为无法确定播放完成时间）
                if delete_after_play:
                    logger.warning("后台播放模式下，delete_after_play参数无效（无法确定播放完成时间）")
                
                return True
                
        except Exception as e:
            logger.exception(f"播放文件异常: {e}")
            return False
    
    def start_stream(self) -> bool:
        """
        启动流式播放（从stdin读取音频数据）
        
        返回:
            成功返回True，失败返回False
        """
        if not self.check_mpv_installed():
            logger.error("MPV播放器未安装！请运行: sudo apt update && sudo apt install -y mpv")
            return False
        
        if self.mpv_process is not None:
            logger.warning("流式播放已启动，先停止现有播放")
            self.stop_stream()
        
        try:
            cmd = [
                'mpv',
                '--no-cache',
                '--no-terminal',
                f'--audio-device={self.audio_device}',
                '--',
                'fd://0'
            ]
            
            self.mpv_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False
            )
            
            logger.info("流式播放已启动")
            return True
            
        except Exception as e:
            logger.exception(f"启动流式播放异常: {e}")
            return False
    
    def play_stream_chunk(self, audio_data: bytes) -> bool:
        """
        播放流式音频数据块
        
        参数:
            audio_data: 音频数据（bytes或hex字符串）
        
        返回:
            成功返回True，失败返回False
        """
        if self.mpv_process is None or self.mpv_process.stdin is None:
            logger.error("流式播放未启动，请先调用start_stream()")
            return False
        
        try:
            # 如果是hex字符串，转换为bytes
            if isinstance(audio_data, str):
                audio_bytes = bytes.fromhex(audio_data)
            else:
                audio_bytes = audio_data
            
            if not audio_bytes:
                logger.warning("音频数据为空")
                return False
            
            self.mpv_process.stdin.write(audio_bytes)
            self.mpv_process.stdin.flush()
            
            logger.debug(f"已发送 {len(audio_bytes)} 字节音频数据")
            return True
            
        except BrokenPipeError:
            logger.error("MPV进程管道已断开")
            self.mpv_process = None
            return False
        except Exception as e:
            logger.exception(f"播放音频块异常: {e}")
            return False
    
    def stop_stream(self, timeout: float = 10.0) -> bool:
        """
        停止流式播放
        
        参数:
            timeout: 等待超时时间（秒）
        
        返回:
            成功返回True，失败返回False
        """
        if self.mpv_process is None:
            return True
        
        try:
            # 关闭stdin
            if self.mpv_process.stdin and not self.mpv_process.stdin.closed:
                try:
                    self.mpv_process.stdin.close()
                except Exception as e:
                    logger.warning(f"关闭stdin异常: {e}")
            
            # 等待进程结束
            try:
                self.mpv_process.wait(timeout=timeout)
                logger.info("流式播放已停止")
            except subprocess.TimeoutExpired:
                logger.warning("等待超时，强制终止进程")
                self.mpv_process.terminate()
                try:
                    self.mpv_process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    logger.error("强制终止失败，使用kill")
                    self.mpv_process.kill()
                    self.mpv_process.wait()
            
            self.mpv_process = None
            return True
            
        except Exception as e:
            logger.exception(f"停止流式播放异常: {e}")
            self.mpv_process = None
            return False
    
    def is_playing(self) -> bool:
        """
        检查是否正在播放
        
        返回:
            正在播放返回True，否则返回False
        """
        if self.mpv_process is None:
            return False
        
        # 检查进程是否还在运行
        poll_result = self.mpv_process.poll()
        if poll_result is not None:
            # 进程已结束
            self.mpv_process = None
            return False
        
        return True
    
    def cleanup(self):
        """清理资源"""
        if self.mpv_process is not None:
            self.stop_stream()
        logger.debug("资源已清理")


def play_audio_file(file_path: str, delete_after_play: bool = True, **kwargs) -> bool:
    """
    便捷函数：快速播放音频文件（播放后自动删除）
    
    参数:
        file_path: 音频文件路径
        delete_after_play: 播放完成后是否删除文件，默认True
        **kwargs: 其他参数传递给AudioPlayer.play_file()
    
    返回:
        成功返回True，失败返回False
    
    示例:
        >>> play_audio_file("output.mp3")  # 播放后自动删除
        True
        >>> play_audio_file("output.mp3", delete_after_play=False)  # 播放后保留文件
        True
    """
    player = AudioPlayer()
    try:
        return player.play_file(file_path, delete_after_play=delete_after_play, **kwargs)
    finally:
        player.cleanup()


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("音频播放工具测试")
    print("=" * 60)
    
    player = AudioPlayer()
    
    # 检查MPV是否安装
    if not player.check_mpv_installed():
        print("\n✗ MPV播放器未安装！")
        print("请运行: sudo apt update && sudo apt install -y mpv")
        sys.exit(1)
    
    print("\n✓ MPV播放器已安装")
    
    # 测试文件播放（需要提供测试文件路径）
    test_file = input("\n请输入测试音频文件路径（留空跳过文件播放测试）: ").strip()
    
    if test_file and os.path.exists(test_file):
        print(f"\n测试1: 播放文件 {test_file}")
        # 注意：测试时会删除文件，所以使用副本或测试文件
        success = player.play_file(test_file, wait=True, delete_after_play=True)
        if success:
            print("✓ 文件播放测试成功")
            if os.path.exists(test_file):
                print("⚠ 文件未被删除（可能删除失败）")
            else:
                print("✓ 文件已自动删除")
        else:
            print("✗ 文件播放测试失败")
    else:
        print("\n跳过文件播放测试")
    
    # 测试流式播放
    print("\n测试2: 流式播放（需要手动输入音频数据）")
    print("提示: 此测试需要实际的音频数据，通常与TTS工具配合使用")
    
    try:
        player.cleanup()
        print("\n✓ 测试完成")
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")

