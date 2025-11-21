#!/usr/bin/env python3
"""
YOLO物体检测工具
用于检测图片中最接近hearer的物体
高独立性、低耦合、高鲁棒性设计
"""
import os
import sys
import json
import cv2
import numpy as np
import logging
from typing import Optional

# 导入配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    PROJECT_ROOT,
    FILE_OBJECT_NAME,
    DEBUG_LOG
)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if DEBUG_LOG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 默认模型路径
DEFAULT_HEARER_MODEL_PATH = os.path.join(PROJECT_ROOT, "yolo", "models", "best.pt")
DEFAULT_GENERAL_MODEL_PATH = os.path.join(PROJECT_ROOT, "yolo", "models", "yolo11n.pt")


class ObjectDetection:
    """
    YOLO物体检测工具类
    用于检测图片中最接近hearer的物体
    """
    
    def __init__(self,
                 hearer_model_path: Optional[str] = None,
                 general_model_path: Optional[str] = None):
        """
        初始化物体检测工具
        
        参数:
            hearer_model_path: hearer模型路径，默认使用项目中的best.pt
            general_model_path: 通用YOLO模型路径，默认使用项目中的yolo11n.pt
        """
        try:
            from ultralytics import YOLO
            self.YOLO = YOLO
        except ImportError:
            raise ImportError("ultralytics 未安装，请运行: pip install ultralytics")
        
        self.hearer_model_path = hearer_model_path or DEFAULT_HEARER_MODEL_PATH
        self.general_model_path = general_model_path or DEFAULT_GENERAL_MODEL_PATH
        
        # 延迟加载模型（首次使用时加载）
        self._hearer_model = None
        self._general_model = None
        
        # 验证模型文件是否存在
        if not os.path.exists(self.hearer_model_path):
            logger.warning(f"hearer模型文件不存在: {self.hearer_model_path}")
        if not os.path.exists(self.general_model_path):
            logger.warning(f"通用模型文件不存在: {self.general_model_path}")
    
    def _load_models(self):
        """延迟加载模型（首次使用时加载）"""
        if self._hearer_model is None:
            try:
                logger.debug(f"加载hearer模型: {self.hearer_model_path}")
                self._hearer_model = self.YOLO(self.hearer_model_path)
                logger.info("hearer模型加载成功")
            except Exception as e:
                logger.exception(f"加载hearer模型失败: {e}")
                raise
        
        if self._general_model is None:
            try:
                logger.debug(f"加载通用模型: {self.general_model_path}")
                self._general_model = self.YOLO(self.general_model_path)
                logger.info("通用模型加载成功")
            except Exception as e:
                logger.exception(f"加载通用模型失败: {e}")
                raise
    
    def detect_closest_object(self, image_path: str) -> Optional[str]:
        """
        检测图片中最接近hearer的物体
        
        参数:
            image_path: 图片路径
        
        返回:
            str: 物体名称，如果检测失败返回"null"
        """
        if not os.path.exists(image_path):
            logger.error(f"图片文件不存在: {image_path}")
            return "null"
        
        try:
            # 加载模型（如果尚未加载）
            self._load_models()
            
            # 读取图片
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"无法读取图片: {image_path}")
                return "null"
            
            logger.debug(f"开始检测图片: {image_path}")
            
            # ---------------- Hearer：只保留置信度最高的 ----------------
            hearer_results = self._hearer_model(img, verbose=False)[0]
            hearer_boxes = hearer_results.boxes.xyxy.cpu().numpy()
            hearer_scores = hearer_results.boxes.conf.cpu().numpy()
            
            if len(hearer_boxes) == 0:
                logger.debug("未检测到hearer")
                return "null"
            
            best_idx = np.argmax(hearer_scores)
            best_hearer_box = hearer_boxes[best_idx]
            logger.debug(f"检测到hearer，置信度: {hearer_scores[best_idx]:.2f}")
            
            # ---------------- General：筛选有效物体 ----------------
            general_results = self._general_model(img, verbose=False)[0]
            other_boxes = general_results.boxes.xyxy.cpu().numpy()
            other_scores = general_results.boxes.conf.cpu().numpy()
            other_classes = general_results.boxes.cls.cpu().numpy()
            class_names = general_results.names
            
            valid_objects = []
            ignore_classes = ["person", "frisbee"]
            
            for o_box, cls_idx, o_score in zip(other_boxes, other_classes, other_scores):
                obj_name = class_names[int(cls_idx)]
                if o_score < 0.3:
                    continue
                if obj_name in ignore_classes:
                    continue
                valid_objects.append((o_box, obj_name))
            
            logger.debug(f"检测到 {len(valid_objects)} 个有效物体")
            
            # ---------------- 没有其他有效物体 ----------------
            if len(valid_objects) == 0:
                logger.debug("未检测到其他有效物体")
                return "null"
            
            # ---------------- 计算中心点距离最近的物体 ----------------
            hx1, hy1, hx2, hy2 = best_hearer_box
            hcx = (hx1 + hx2) / 2
            hcy = (hy1 + hy2) / 2
            
            min_dist = float("inf")
            closest_name = "null"
            for o_box, obj_name in valid_objects:
                ox1, oy1, ox2, oy2 = o_box
                ocx = (ox1 + ox2) / 2
                ocy = (oy1 + oy2) / 2
                dist = np.sqrt((hcx - ocx) ** 2 + (hcy - ocy) ** 2)
                if dist < min_dist:
                    min_dist = dist
                    closest_name = obj_name
            
            logger.info(f"检测到最接近的物体: {closest_name} (距离: {min_dist:.2f})")
            return closest_name
            
        except Exception as e:
            logger.exception(f"物体检测异常: {e}")
            return "null"
    
    def detect_and_save(self, 
                       image_path: str,
                       output_file: Optional[str] = None) -> bool:
        """
        检测物体并保存结果到文件
        
        参数:
            image_path: 图片路径
            output_file: 输出文件路径，默认使用config.py中的FILE_OBJECT_NAME
        
        返回:
            bool: 成功返回True，失败返回False
        """
        output_file = output_file or FILE_OBJECT_NAME
        
        try:
            # 检测物体
            object_name = self.detect_closest_object(image_path)
            
            # 构建结果字典
            result = {
                "object_name": object_name
            }
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 保存到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
            
            logger.info(f"检测结果已保存到: {output_file}")
            logger.debug(f"检测结果: {result}")
            return True
            
        except Exception as e:
            logger.exception(f"保存检测结果异常: {e}")
            return False


def detect_object(image_path: str,
                 output_file: Optional[str] = None,
                 **kwargs) -> bool:
    """
    便捷函数：快速检测物体并保存结果
    
    参数:
        image_path: 图片路径
        output_file: 输出文件路径，默认使用config.py中的FILE_OBJECT_NAME
        **kwargs: 其他参数传递给ObjectDetection构造函数
    
    返回:
        bool: 成功返回True，失败返回False
    
    示例:
        >>> success = detect_object("photo.jpg")
        >>> if success:
        ...     print("检测完成")
    """
    detector = ObjectDetection(**kwargs)
    return detector.detect_and_save(image_path, output_file)


if __name__ == "__main__":
    # 测试代码
    import sys
    
    print("=" * 60)
    print("YOLO物体检测工具测试")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # 使用默认测试图片（如果存在）
        test_image = os.path.join(PROJECT_ROOT, "temp_data", "photo_20251121_094244.jpg")
        if os.path.exists(test_image):
            image_path = test_image
            print(f"使用默认测试图片: {image_path}")
        else:
            print("请提供图片路径作为参数")
            print("用法: python object_detection.py <image_path>")
            sys.exit(1)
    
    detector = ObjectDetection()
    
    print(f"\n正在检测图片: {image_path}")
    success = detector.detect_and_save(image_path)
    
    if success:
        print(f"\n✓ 成功！结果已保存到: {FILE_OBJECT_NAME}")
        # 读取并显示结果
        try:
            with open(FILE_OBJECT_NAME, 'r', encoding='utf-8') as f:
                result = json.load(f)
            print(f"检测结果: {result}")
        except Exception as e:
            print(f"读取结果失败: {e}")
    else:
        print("\n✗ 失败！")

