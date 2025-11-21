#!/usr/bin/env python3
"""
tydeus 项目摄像头测试文件
用于测试摄像头拍摄功能
"""
import os
import sys
import time
import cv2
import numpy as np

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMP_DATA_DIR = os.path.join(PROJECT_ROOT, "temp_data")

# 确保 temp_data 文件夹存在
os.makedirs(TEMP_DATA_DIR, exist_ok=True)

# 摄像头分辨率设置（1080p）
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080


def capture_photo_usb_camera():
    """使用USB摄像头拍摄照片"""
    print("尝试使用USB摄像头...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("  ✗ USB摄像头无法打开")
        return None
    
    try:
        # 设置摄像头分辨率为1080p
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        
        # 等待摄像头稳定
        print("  等待摄像头稳定...")
        time.sleep(1)
        
        # 读取几帧以让摄像头调整
        for _ in range(5):
            ret, frame = cap.read()
            if not ret:
                print("  ✗ 无法从USB摄像头读取帧")
                return None
        
        # 拍摄照片
        print("  正在拍摄照片...")
        ret, frame = cap.read()
        
        if not ret or frame is None:
            print("  ✗ 拍摄失败")
            return None
        
        # 获取实际分辨率
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"  实际分辨率: {actual_width}x{actual_height}")
        
        # 如果实际分辨率不是1080p，尝试调整
        if actual_width != CAMERA_WIDTH or actual_height != CAMERA_HEIGHT:
            print(f"  调整图像分辨率到 {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
            frame = cv2.resize(frame, (CAMERA_WIDTH, CAMERA_HEIGHT))
        
        return frame
        
    finally:
        cap.release()


def capture_photo_picamera():
    """使用树莓派摄像头拍摄照片"""
    print("尝试使用树莓派摄像头...")
    try:
        from picamera2 import Picamera2
        
        picam2 = Picamera2()
        
        # 配置摄像头为1080p
        config = picam2.create_still_configuration(
            main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT)}
        )
        picam2.configure(config)
        picam2.start()
        
        # 等待摄像头稳定
        print("  等待摄像头稳定...")
        time.sleep(1)
        
        # 拍摄照片
        print("  正在拍摄照片...")
        frame = picam2.capture_array()
        
        # picamera2 返回的是RGB格式，需要转换为BGR（OpenCV格式）
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        picam2.stop()
        picam2.close()
        
        print(f"  实际分辨率: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
        return frame
        
    except ImportError:
        print("  ⚠ picamera2 未安装，跳过树莓派摄像头测试")
        return None
    except Exception as e:
        print(f"  ✗ 树莓派摄像头错误: {e}")
        return None


def test_camera():
    """测试摄像头拍摄功能"""
    print("=" * 60)
    print("摄像头测试")
    print("=" * 60)
    print(f"目标分辨率: {CAMERA_WIDTH}x{CAMERA_HEIGHT} (1080p)")
    print(f"保存目录: {TEMP_DATA_DIR}")
    print("=" * 60)
    
    frame = None
    
    # 首先尝试USB摄像头
    frame = capture_photo_usb_camera()
    
    # 如果USB摄像头失败，尝试树莓派摄像头
    if frame is None:
        print("\nUSB摄像头不可用，尝试树莓派摄像头...")
        frame = capture_photo_picamera()
    
    if frame is None:
        print("\n✗ 所有摄像头都无法使用")
        return False
    
    # 保存照片
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"photo_{timestamp}.jpg"
    filepath = os.path.join(TEMP_DATA_DIR, filename)
    
    print(f"\n正在保存照片到: {filepath}")
    success = cv2.imwrite(filepath, frame)
    
    if success:
        file_size = os.path.getsize(filepath)
        print(f"✓ 照片保存成功！")
        print(f"  文件名: {filename}")
        print(f"  文件大小: {file_size / 1024:.2f} KB")
        print(f"  分辨率: {frame.shape[1]}x{frame.shape[0]}")
        return True
    else:
        print("✗ 照片保存失败")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("tydeus 项目摄像头测试")
    print("=" * 60)
    
    try:
        success = test_camera()
        
        print("\n" + "=" * 60)
        if success:
            print("✓ 测试通过！")
        else:
            print("✗ 测试失败")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程发生异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
