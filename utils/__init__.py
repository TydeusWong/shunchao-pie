"""
工具模块
提供各种非硬件直接相关的工具类
"""

from .text_to_speech import TextToSpeech, synthesize_text
from .flashcard import FlashCardMaker, create_flashcard
from .speech_recognition import SpeechRecognition, recognize_audio

__all__ = [
    'TextToSpeech',
    'synthesize_text',
    'FlashCardMaker',
    'create_flashcard',
    'SpeechRecognition',
    'recognize_audio',
]
