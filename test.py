#!/usr/bin/env python3
"""
tydeus 项目物体检测测试文件
用于测试YOLO物体检测功能
"""
import os
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.object_detection import ObjectDetection, detect_object
from config import FILE_OBJECT_NAME

# 测试图片路径
TEST_IMAGE_PATH = "/home/pi/projects/tydeus/temp_data/yolo_test.jpg"


def test_object_detection():
    """测试物体检测功能"""
    print("=" * 60)
    print("YOLO物体检测测试")
    print("=" * 60)
    print(f"测试图片: {TEST_IMAGE_PATH}")
    print(f"输出文件: {FILE_OBJECT_NAME}")
    print("=" * 60)
    
    # 检查测试图片是否存在
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"\n✗ 测试图片不存在: {TEST_IMAGE_PATH}")
        print("  请确保测试图片存在")
        return False
    
    print(f"\n✓ 测试图片存在")
    file_size = os.path.getsize(TEST_IMAGE_PATH)
    print(f"  文件大小: {file_size / 1024:.2f} KB")
    
    try:
        print("\n[步骤1] 初始化物体检测工具...")
        detector = ObjectDetection()
        print("  ✓ 初始化成功")
        
        print("\n[步骤2] 开始检测物体...")
        print("  注意: 首次运行会加载模型，可能需要一些时间...")
        
        success = detector.detect_and_save(TEST_IMAGE_PATH)
        
        if not success:
            print("\n✗ 检测失败")
            return False
        
        print("\n[步骤3] 读取检测结果...")
        if not os.path.exists(FILE_OBJECT_NAME):
            print(f"  ✗ 输出文件不存在: {FILE_OBJECT_NAME}")
            return False
        
        with open(FILE_OBJECT_NAME, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        object_name = result.get("object_name", "null")
        
        print(f"\n✓ 检测完成！")
        print(f"  检测结果: {object_name}")
        print(f"  结果文件: {FILE_OBJECT_NAME}")
        print(f"\n结果文件内容:")
        print(json.dumps(result, ensure_ascii=False, indent=4))
        
        if object_name == "null":
            print("\n⚠ 注意: 检测结果为 'null'，可能是:")
            print("  - 图片中未检测到hearer")
            print("  - 图片中未检测到其他有效物体")
            print("  - 检测过程中出现错误")
        
        return True
        
    except ImportError as e:
        print(f"\n✗ 导入错误: {e}")
        print("  提示: 请确保已安装所需依赖: pip install ultralytics opencv-python numpy")
        return False
    except Exception as e:
        print(f"\n✗ 检测过程发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_convenience_function():
    """测试便捷函数"""
    print("\n" + "=" * 60)
    print("便捷函数测试")
    print("=" * 60)
    
    try:
        print("\n使用便捷函数 detect_object()...")
        success = detect_object(TEST_IMAGE_PATH)
        
        if success:
            print("  ✓ 便捷函数调用成功")
            
            # 读取结果
            with open(FILE_OBJECT_NAME, 'r', encoding='utf-8') as f:
                result = json.load(f)
            print(f"  检测结果: {result.get('object_name', 'null')}")
            return True
        else:
            print("  ✗ 便捷函数调用失败")
            return False
            
    except Exception as e:
        print(f"  ✗ 便捷函数测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("tydeus 项目物体检测测试")
    print("=" * 60)
    
    try:
        # 测试1: 使用类方法
        success1 = test_object_detection()
        
        # 测试2: 使用便捷函数
        success2 = test_convenience_function()
        
        # 输出测试结果汇总
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        print(f"类方法测试: {'✓ 通过' if success1 else '✗ 失败'}")
        print(f"便捷函数测试: {'✓ 通过' if success2 else '✗ 失败'}")
        print("=" * 60)
        
        if success1 and success2:
            print("\n🎉 所有测试通过！")
        else:
            print("\n⚠️  部分测试失败，请检查")
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程发生异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
