#!/usr/bin/env python3
"""
音频录制和播放测试文件
先使用 audio_recorder.py 录音，然后使用 audio_player.py 播放
"""
import os
import sys
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hardware.audio_recorder import AudioRecorder
from hardware.audio_player import AudioPlayer, play_audio_file
from config import TEMP_DATA_DIR


def check_bluetooth_audio_device(player: AudioPlayer):
    """检查并显示当前使用的音频设备（如果已连接蓝牙，会自动检测）"""
    print(f"  当前音频设备: {player.audio_device}")
    
    # 检查是否是蓝牙设备
    if 'blue' in player.audio_device.lower() or 'bluetooth' in player.audio_device.lower():
        print("  ✓ 检测到蓝牙音频设备")
        return True
    else:
        print("  ℹ 使用默认音频设备（非蓝牙）")
        return False


def print_section(title):
    """打印测试章节标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def test_recording_and_playback():
    """测试录音和播放功能"""
    print_section("音频录制和播放测试")
    
    # 确保临时目录存在
    os.makedirs(TEMP_DATA_DIR, exist_ok=True)
    
    # 录音文件路径
    recording_file = os.path.join(TEMP_DATA_DIR, "test_recording.wav")
    
    try:
        # ========== 步骤1: 录音 ==========
        print("\n[步骤1] 开始录音...")
        print("  提示: 请对着麦克风说话，录音将持续3秒")
        print("  录音文件将保存到: " + recording_file)
        
        recorder = AudioRecorder()
        
        # 录音3秒
        print("\n  录音中... (3秒)")
        recorded_file = recorder.record(output_path=recording_file, duration=3.0)
        
        if not recorded_file or not os.path.exists(recorded_file):
            print("  ✗ 录音失败")
            return False
        
        file_size = os.path.getsize(recorded_file) / 1024
        print(f"  ✓ 录音成功")
        print(f"  录音文件: {recorded_file}")
        print(f"  文件大小: {file_size:.2f} KB")
        
        recorder.cleanup()
        
        # ========== 步骤2: 播放录音 ==========
        print("\n[步骤2] 播放录音文件...")
        
        # 创建播放器（会自动检测音频设备，包括已连接的蓝牙设备）
        player = AudioPlayer()
        check_bluetooth_audio_device(player)
        
        # 播放录音文件
        print("\n  播放录音文件...")
        success = player.play_file(recorded_file, wait=True, delete_after_play=False)
        
        if success:
            print("  ✓ 播放成功")
            print("  提示: 如果使用蓝牙设备，请检查蓝牙音箱是否有声音输出")
        else:
            print("  ✗ 播放失败")
            return False
        
        player.cleanup()
        
        # ========== 步骤3: 清理 ==========
        print("\n[步骤3] 清理测试文件...")
        if os.path.exists(recorded_file):
            choice = input("  是否删除测试录音文件? (y/n, 默认n): ").strip().lower()
            if choice == 'y':
                os.remove(recorded_file)
                print("  ✓ 测试文件已删除")
            else:
                print(f"  ✓ 测试文件已保留: {recorded_file}")
        
        print("\n✓ 录音和播放测试完成")
        return True
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        return False
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_recordings():
    """测试多次录音和播放"""
    print_section("多次录音和播放测试")
    
    os.makedirs(TEMP_DATA_DIR, exist_ok=True)
    
    try:
        recorder = AudioRecorder()
        player = AudioPlayer()
        
        # 检查音频设备
        check_bluetooth_audio_device(player)
        
        recordings = []
        
        # 录制3段音频
        for i in range(3):
            print(f"\n[录音 {i+1}/3] 请说话，录音2秒...")
            recording_file = os.path.join(TEMP_DATA_DIR, f"test_recording_{i+1}.wav")
            recorded_file = recorder.record(output_path=recording_file, duration=2.0)
            
            if recorded_file and os.path.exists(recorded_file):
                recordings.append(recorded_file)
                file_size = os.path.getsize(recorded_file) / 1024
                print(f"  ✓ 录音成功 ({file_size:.2f} KB)")
            else:
                print("  ✗ 录音失败")
        
        recorder.cleanup()
        
        # 播放所有录音
        print("\n[播放] 依次播放所有录音...")
        for i, recording_file in enumerate(recordings, 1):
            print(f"\n  播放录音 {i}/3...")
            success = player.play_file(recording_file, wait=True, delete_after_play=False)
            if success:
                print(f"  ✓ 播放成功")
            else:
                print(f"  ✗ 播放失败")
            time.sleep(0.1)  # 优化：从0.5秒缩短到0.1秒
        
        player.cleanup()
        
        # 清理文件
        print("\n[清理] 删除测试文件...")
        for recording_file in recordings:
            if os.path.exists(recording_file):
                os.remove(recording_file)
        print("  ✓ 测试文件已删除")
        
        print("\n✓ 多次录音和播放测试完成")
        return True
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        return False
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("tydeus 项目音频录制和播放测试")
    print("=" * 60)
    
    print("\n测试说明:")
    print("  1. 本测试将先进行录音，然后播放录音文件")
    print("  2. 如果已配对蓝牙设备，将尝试使用蓝牙设备播放")
    print("  3. 请确保麦克风和音频输出设备正常工作")
    
    try:
        # 测试1: 基本录音和播放
        success1 = test_recording_and_playback()
        
        # 询问是否进行多次录音测试
        if success1:
            print("\n" + "=" * 60)
            choice = input("\n是否进行多次录音和播放测试? (y/n, 默认n): ").strip().lower()
            if choice == 'y':
                success2 = test_multiple_recordings()
            else:
                success2 = None
        else:
            success2 = None
        
        # 输出测试结果汇总
        print_section("测试结果汇总")
        print(f"基本录音和播放测试: {'✓ 通过' if success1 else '✗ 失败'}")
        if success2 is not None:
            print(f"多次录音和播放测试: {'✓ 通过' if success2 else '✗ 失败'}")
        else:
            print("多次录音和播放测试: ⚠ 跳过")
        print("=" * 60)
        
        if success1:
            print("\n🎉 基本测试通过！")
        else:
            print("\n❌ 基本测试失败")
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程发生异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

