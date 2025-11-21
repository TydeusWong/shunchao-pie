#!/usr/bin/env python3
"""
EP1831T 显示屏驱动工具
适用于 360x360 圆形LCD屏幕
高独立性、低耦合、高鲁棒性设计
"""
import spidev
import RPi.GPIO as GPIO
import time
import os
import sys
import logging
from typing import Optional, Union
from PIL import Image

# 导入配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    SCREEN_RST_PIN,
    SCREEN_DC_PIN,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_SPI_SPEED,
    DEBUG_LOG
)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if DEBUG_LOG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EP1831TDriver:
    """
    EP1831T 显示屏驱动类
    支持RGB666格式，360x360像素
    """
    
    def __init__(self,
                 rst_pin: Optional[int] = None,
                 dc_pin: Optional[int] = None,
                 width: Optional[int] = None,
                 height: Optional[int] = None,
                 spi_speed: Optional[int] = None,
                 spi_bus: int = 0,
                 spi_device: int = 0):
        """
        初始化EP1831T显示屏驱动
        
        参数:
            rst_pin: 复位引脚（BCM编号），默认使用config.py中的配置
            dc_pin: 数据/命令引脚（BCM编号），默认使用config.py中的配置
            width: 屏幕宽度，默认使用config.py中的配置
            height: 屏幕高度，默认使用config.py中的配置
            spi_speed: SPI速率（Hz），默认使用config.py中的配置
            spi_bus: SPI总线号，默认0
            spi_device: SPI设备号，默认0
        """
        self.rst_pin = rst_pin or SCREEN_RST_PIN
        self.dc_pin = dc_pin or SCREEN_DC_PIN
        self.width = width or SCREEN_WIDTH
        self.height = height or SCREEN_HEIGHT
        self.spi_speed = spi_speed or SCREEN_SPI_SPEED
        
        self.spi = None
        self._initialized = False
        
        try:
            self._init_gpio()
            self._init_spi(spi_bus, spi_device)
            logger.info("EP1831T 初始化中...")
            self.reset()
            self.init_display()
            self._initialized = True
            logger.info("EP1831T 初始化完成")
        except Exception as e:
            logger.exception(f"EP1831T 初始化失败: {e}")
            self.cleanup()
            raise
    
    def _init_gpio(self):
        """初始化GPIO"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.rst_pin, GPIO.OUT)
            GPIO.setup(self.dc_pin, GPIO.OUT)
            logger.debug(f"GPIO初始化完成: RST={self.rst_pin}, DC={self.dc_pin}")
        except Exception as e:
            logger.exception(f"GPIO初始化失败: {e}")
            raise
    
    def _init_spi(self, bus: int, device: int):
        """初始化SPI"""
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(bus, device)
            self.spi.max_speed_hz = self.spi_speed
            self.spi.mode = 0
            logger.debug(f"SPI初始化完成: bus={bus}, device={device}, speed={self.spi_speed}Hz")
        except Exception as e:
            logger.exception(f"SPI初始化失败: {e}")
            raise
    
    def reset(self):
        """复位显示屏"""
        try:
            GPIO.output(self.rst_pin, GPIO.HIGH)
            time.sleep(0.01)
            GPIO.output(self.rst_pin, GPIO.LOW)
            time.sleep(0.01)
            GPIO.output(self.rst_pin, GPIO.HIGH)
            time.sleep(0.12)
            logger.debug("显示屏复位完成")
        except Exception as e:
            logger.exception(f"复位失败: {e}")
            raise
    
    def write_cmd(self, cmd: int):
        """写入命令"""
        try:
            GPIO.output(self.dc_pin, GPIO.LOW)
            self.spi.writebytes([cmd])
        except Exception as e:
            logger.exception(f"写入命令失败: {e}")
            raise
    
    def write_data(self, data: Union[int, list]):
        """写入数据"""
        try:
            GPIO.output(self.dc_pin, GPIO.HIGH)
            if isinstance(data, int):
                self.spi.writebytes([data])
            else:
                self.spi.writebytes(data)
        except Exception as e:
            logger.exception(f"写入数据失败: {e}")
            raise
    
    def write_data_array(self, data: list):
        """写入数据数组（分块传输）"""
        try:
            GPIO.output(self.dc_pin, GPIO.HIGH)
            chunk_size = 4096
            for i in range(0, len(data), chunk_size):
                self.spi.writebytes(data[i:i+chunk_size])
        except Exception as e:
            logger.exception(f"写入数据数组失败: {e}")
            raise
    
    def init_display(self):
        """初始化显示屏（发送初始化命令序列）"""
        try:
            # 初始化命令序列
            init_commands = [
                (0xF0, 0x28), (0xF2, 0x28),
                (0x73, 0xF0), (0x7C, 0xD1), (0x83, 0xE0), (0x84, 0x61), (0xF2, 0x82),
                (0xF0, 0x00), (0xF0, 0x01), (0xF1, 0x01),
                (0xB0, 0x56), (0xB1, 0x4D), (0xB2, 0x24), (0xB4, 0x87),
                (0xB5, 0x44), (0xB6, 0x8B), (0xB7, 0x40), (0xB8, 0x86),
                (0xBA, 0x00), (0xBB, 0x08), (0xBC, 0x08), (0xBD, 0x00),
                (0xC0, 0x80), (0xC1, 0x10), (0xC2, 0x37), (0xC3, 0x80),
                (0xC4, 0x10), (0xC5, 0x37), (0xC6, 0xA9), (0xC7, 0x41),
                (0xC8, 0x01), (0xC9, 0xA9), (0xCA, 0x41), (0xCB, 0x01),
                (0xD0, 0x91), (0xD1, 0x68), (0xD2, 0x68),
                (0xF5, [0x00, 0xA5]),
                (0xDD, 0x4F), (0xDE, 0x4F),
                (0xF1, 0x10), (0xF0, 0x00), (0xF0, 0x02),
                (0xE0, [0xF0, 0x0A, 0x10, 0x09, 0x09, 0x36, 0x35, 0x33, 0x4A, 0x29, 0x15, 0x15, 0x2E, 0x34]),
                (0xE1, [0xF0, 0x0A, 0x0F, 0x08, 0x08, 0x05, 0x34, 0x33, 0x4A, 0x39, 0x15, 0x15, 0x2D, 0x33]),
                (0xF0, 0x10), (0xF3, 0x10),
                (0xE0, 0x07), (0xE1, 0x00), (0xE2, 0x00), (0xE3, 0x00),
                (0xE4, 0xE0), (0xE5, 0x06), (0xE6, 0x21), (0xE7, 0x01),
                (0xE8, 0x05), (0xE9, 0x02), (0xEA, 0xDA), (0xEB, 0x00),
                (0xEC, 0x00), (0xED, 0x0F), (0xEE, 0x00), (0xEF, 0x00),
                (0xF8, 0x00), (0xF9, 0x00), (0xFA, 0x00), (0xFB, 0x00),
                (0xFC, 0x00), (0xFD, 0x00), (0xFE, 0x00), (0xFF, 0x00),
                (0x60, 0x40), (0x61, 0x04), (0x62, 0x00), (0x63, 0x42),
                (0x64, 0xD9), (0x65, 0x00), (0x66, 0x00), (0x67, 0x00),
                (0x68, 0x00), (0x69, 0x00), (0x6A, 0x00), (0x6B, 0x00),
                (0x70, 0x40), (0x71, 0x03), (0x72, 0x00), (0x73, 0x42),
                (0x74, 0xD8), (0x75, 0x00), (0x76, 0x00), (0x77, 0x00),
                (0x78, 0x00), (0x79, 0x00), (0x7A, 0x00), (0x7B, 0x00),
            ]
            
            # 发送初始化命令
            for cmd, data in init_commands:
                self.write_cmd(cmd)
                if isinstance(data, list):
                    self.write_data(data)
                else:
                    self.write_data(data)
            
            # 时序配置
            timing_configs = [
                (0x80, [0x48, 0x00, 0x06, 0x02, 0xD6, 0x04, 0x00, 0x00]),
                (0x88, [0x48, 0x00, 0x08, 0x02, 0xD8, 0x04, 0x00, 0x00]),
                (0x90, [0x48, 0x00, 0x0A, 0x02, 0xDA, 0x04, 0x00, 0x00]),
                (0x98, [0x48, 0x00, 0x0C, 0x02, 0xDC, 0x04, 0x00, 0x00]),
                (0xA0, [0x48, 0x00, 0x05, 0x02, 0xD5, 0x04, 0x00, 0x00]),
                (0xA8, [0x48, 0x00, 0x07, 0x02, 0xD7, 0x04, 0x00, 0x00]),
                (0xB0, [0x48, 0x00, 0x09, 0x02, 0xD9, 0x04, 0x00, 0x00]),
                (0xB8, [0x48, 0x00, 0x0B, 0x02, 0xDB, 0x04, 0x00, 0x00]),
            ]
            
            for base_addr, values in timing_configs:
                for i, val in enumerate(values):
                    self.write_cmd(base_addr + i)
                    self.write_data(val)
            
            # 源配置
            source_configs = [
                (0xC0, [0x10, 0x47, 0x56, 0x65, 0x74, 0x88, 0x99, 0x01, 0xBB, 0xAA]),
                (0xD0, [0x10, 0x47, 0x56, 0x65, 0x74, 0x88, 0x99, 0x01, 0xBB, 0xAA]),
            ]
            
            for base_addr, values in source_configs:
                for i, val in enumerate(values):
                    self.write_cmd(base_addr + i)
                    self.write_data(val)
            
            # 完成初始化序列
            self.write_cmd(0xF3)
            self.write_data(0x01)
            self.write_cmd(0xF0)
            self.write_data(0x00)
            
            # 设置颜色格式为RGB666
            self.write_cmd(0x3A)
            self.write_data(0x66)
            
            # 开启显示
            self.write_cmd(0x21)  # 反转显示
            self.write_cmd(0x11)  # 退出睡眠
            time.sleep(0.12)
            self.write_cmd(0x29)  # 开启显示
            
            logger.info("显示屏初始化完成")
            
        except Exception as e:
            logger.exception(f"初始化显示屏失败: {e}")
            raise
    
    def set_window(self, x0: int, y0: int, x1: int, y1: int):
        """
        设置显示窗口
        
        参数:
            x0, y0: 窗口左上角坐标
            x1, y1: 窗口右下角坐标
        """
        try:
            self.write_cmd(0x2A)
            self.write_data([
                (x0 >> 8) & 0xFF, x0 & 0xFF,
                (x1 >> 8) & 0xFF, x1 & 0xFF
            ])
            
            self.write_cmd(0x2B)
            self.write_data([
                (y0 >> 8) & 0xFF, y0 & 0xFF,
                (y1 >> 8) & 0xFF, y1 & 0xFF
            ])
            
            self.write_cmd(0x2C)  # 开始写入数据
        except Exception as e:
            logger.exception(f"设置窗口失败: {e}")
            raise
    
    def display_image(self, image: Union[str, Image.Image]):
        """
        显示图片
        
        参数:
            image: 图片路径（str）或PIL.Image对象，必须是360x360尺寸
        """
        if not self._initialized:
            raise RuntimeError("显示屏未初始化，请先调用初始化方法")
        
        try:
            # 加载图片
            if isinstance(image, str):
                if not os.path.exists(image):
                    raise FileNotFoundError(f"图片文件不存在: {image}")
                img = Image.open(image)
                logger.debug(f"加载图片: {image}")
            else:
                img = image
            
            # 检查尺寸
            if img.size != (self.width, self.height):
                logger.warning(f"图片尺寸不匹配: {img.size}, 期望: ({self.width}, {self.height})")
                img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
                logger.info(f"图片已缩放至: ({self.width}, {self.height})")
            
            # 转换为RGB模式
            if img.mode != 'RGB':
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                else:
                    img = img.convert('RGB')
            
            # 转换为RGB888数据（每像素3字节）
            logger.debug("转换图片数据为RGB888格式...")
            pixels = img.load()
            image_data = []
            
            for y in range(self.height):
                for x in range(self.width):
                    r, g, b = pixels[x, y]
                    image_data.extend([r, g, b])
            
            logger.debug(f"图片数据大小: {len(image_data)} 字节")
            
            # 发送到显示屏
            self.set_window(0, 0, self.width - 1, self.height - 1)
            self.write_data_array(image_data)
            
            logger.info("图片显示完成")
            
        except Exception as e:
            logger.exception(f"显示图片失败: {e}")
            raise
    
    def fill_color(self, r: int, g: int, b: int):
        """
        填充纯色
        
        参数:
            r, g, b: RGB颜色值（0-255）
        """
        try:
            self.set_window(0, 0, self.width - 1, self.height - 1)
            
            row_data = [r, g, b] * self.width
            
            for y in range(self.height):
                self.write_data_array(row_data)
            
            logger.info(f"填充颜色完成: RGB({r}, {g}, {b})")
            
        except Exception as e:
            logger.exception(f"填充颜色失败: {e}")
            raise
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.spi:
                self.spi.close()
                self.spi = None
            GPIO.cleanup()
            self._initialized = False
            logger.info("资源已清理")
        except Exception as e:
            logger.warning(f"清理资源时出错: {e}")


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("EP1831T 显示屏驱动测试")
    print("=" * 60)
    
    driver = None
    try:
        driver = EP1831TDriver()
        
        # 测试1: 填充纯色
        print("\n测试1: 填充红色")
        driver.fill_color(255, 0, 0)
        input("看到红色了吗? 按回车继续...")
        
        print("\n测试2: 填充绿色")
        driver.fill_color(0, 255, 0)
        input("看到绿色了吗? 按回车继续...")
        
        print("\n测试3: 填充蓝色")
        driver.fill_color(0, 0, 255)
        input("看到蓝色了吗? 按回车继续...")
        
        # 测试4: 显示图片
        print("\n测试4: 显示图片")
        test_image = input("请输入图片路径（留空跳过）: ").strip()
        if test_image and os.path.exists(test_image):
            driver.display_image(test_image)
            print("图片已显示")
        else:
            print("跳过图片显示测试")
        
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.cleanup()

