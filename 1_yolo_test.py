#!/usr/bin/env python3
"""
YOLO物体识别测试
用于测试物体识别流程
"""
import sys
import os
import time
import json
import threading
import logging
from datetime import datetime
from config import *
from comm.mqtt_client import MqttHandler
from utils import execute_response

# --- 全局同步事件 ---
response_received_event = threading.Event()

# --- 日志设置 ---
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

def log_system(message):
    """辅助函数：同时打印到控制台和写入日志文件。"""
    print(message)
    logging.info(message)

# --- 文件处理辅助函数 ---

def ensure_temp_data_dir():
    """确保临时数据目录和必要文件存在。"""
    if not os.path.exists(TEMP_DATA_DIR):
        os.makedirs(TEMP_DATA_DIR)
    if not os.path.exists(FILE_CONVERSATION_ID):
        with open(FILE_CONVERSATION_ID, 'w', encoding='utf-8') as f:
            f.write("")
    # 确保 words_data.json 存在
    if not os.path.exists(FILE_WORDS_DATA):
        default_words = {
            "verb": None, "noun": None, "adjective": None,
            "exclamation": None, "discourse_marker": None, "adverb": None
        }
        with open(FILE_WORDS_DATA, 'w', encoding='utf-8') as f:
            json.dump(default_words, f, ensure_ascii=False, indent=4)

def get_conversation_id():
    """从本地文件读取 conversation_id。"""
    try:
        if os.path.exists(FILE_CONVERSATION_ID):
            with open(FILE_CONVERSATION_ID, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception as e:
        log_system(f"[Error] 无法读取 conversation_id: {e}")
    return ""

def save_conversation_id(conv_id):
    """保存 conversation_id 到本地文件。"""
    try:
        with open(FILE_CONVERSATION_ID, 'w', encoding='utf-8') as f:
            f.write(str(conv_id))
        logging.info(f"Conversation ID 已更新: {conv_id}")
    except Exception as e:
        log_system(f"[Error] 无法保存 conversation_id: {e}")

def read_json_file(filepath):
    """读取 JSON 文件并返回字典。如果失败返回 None。"""
    try:
        if not os.path.exists(filepath):
            log_system(f"[Error] 文件未找到: {filepath}")
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError:
        log_system(f"[Error] 文件 {filepath} JSON 格式无效")
        return None
    except Exception as e:
        log_system(f"[Error] 读取 {filepath} 时出错: {e}")
        return None

# --- MQTT 消息处理器 ---

def on_server_message(topic, payload):
    """
    当从服务器收到消息时的回调函数。
    """
    try:
        logging.info(f"收到 MQTT 消息，主题 {topic}: {payload}")
        data = json.loads(payload)
        
        # 1. 检查是否是停止对话的响应
        if topic == TOPIC_USER_STOP_RESPONSE:
            summary = data.get("conversation_summary", "未提供总结。")
            log_system(f"\n[System] 对话结束。总结: {summary}")
            response_received_event.set()
            return

        # 2. 正常交互响应
        # 提取并更新 conversation_id（如果存在）
        new_conv_id = data.get("conversation_id")
        if new_conv_id:
            save_conversation_id(new_conv_id)
            
        # 3. 调用硬件执行
        success = execute_response(data)
        if success:
            log_system("[System] 硬件执行成功完成。")
        else:
            log_system("[System] 硬件执行遇到问题。")
            
    except json.JSONDecodeError:
        log_system(f"[Error] 无法解码来自主题 {topic} 的 JSON 负载")
    except Exception as e:
        log_system(f"[Error] 处理服务器消息时出错: {e}")
    finally:
        # 只要处理完消息（如果是预期的流程），就释放等待锁
        response_received_event.set()

# --- 动画效果 ---

def wait_for_response(timeout=30):
    """
    阻塞并打印加载动画，直到 response_received_event 被设置或超时。
    """
    start_time = time.time()
    response_received_event.clear()
    
    print("等待回复 ", end="", flush=True)
    dot_count = 0
    
    while not response_received_event.is_set():
        if time.time() - start_time > timeout:
            print("\n[Timeout] 服务器响应超时。")
            return
            
        time.sleep(0.5)
        print(".", end="", flush=True)
        dot_count += 1
        if dot_count >= 6:
            # 退格符用于重置点号 (简单的视觉黑魔法)
            print("\b" * 6 + "      " + "\b" * 6, end="", flush=True)
            dot_count = 0
            
    print("\n") # 响应后的换行

# --- 主逻辑 ---

def main():
    """YOLO物体识别测试主函数"""
    ensure_temp_data_dir()
    
    # 初始化 MQTT
    mqtt = MqttHandler(MQTT_BROKER, MQTT_PORT, DEVICE_ID)
    
    # 订阅主题
    subscriptions = [
        TOPIC_AGENT_RESPONSE_OBJECT,
        TOPIC_AGENT_RESPONSE_USER,
        TOPIC_USER_STOP_RESPONSE
    ]
    
    mqtt.start(subscriptions=subscriptions, callback=on_server_message)
    logging.info(f"YOLO测试已启动。设备 ID: {DEVICE_ID}")
    
    # 短暂等待连接
    time.sleep(1)
    
    print("\n=== YOLO物体识别测试 ===")
    print(f"Device ID: {DEVICE_ID}")
    
    try:
        print("\n[Action] 触发物体识别...")
        
        obj_data = read_json_file(FILE_OBJECT_NAME)
        if obj_data is None:
            print("[Error] 无法读取物体数据。")
            return
        
        object_name = obj_data.get("object_name")
        
        payload = {
            "device_id": DEVICE_ID,
            "timestamp": time.time(),
            "object_name": object_name,
            "conversation_id": get_conversation_id() or 0 # 处理空字符串或 null
        }
        
        # 确保 conversation_id 尽可能为 int，如果是新的则为 0
        try:
            payload["conversation_id"] = int(payload["conversation_id"])
        except:
            payload["conversation_id"] = 0

        mqtt.publish(TOPIC_OBJECT_DETECTED, json.dumps(payload))
        logging.info(f"已发布到 {TOPIC_OBJECT_DETECTED}: {payload}")
        
        wait_for_response()
        
        print("\n✓ YOLO物体识别测试完成")
        
    except KeyboardInterrupt:
        print("\n检测到中断，正在退出...")
    except Exception as e:
        print(f"\n[Error] 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mqtt.stop()
        print("程序已结束。")

if __name__ == "__main__":
    main()

