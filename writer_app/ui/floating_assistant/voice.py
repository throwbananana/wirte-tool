"""
语音功能模块 (Voice Features Module)

提供：
- 语音识别输入 (Speech Recognition)
- 文本朗读 (Text-to-Speech)
- 语音命令识别
"""

import threading
import queue
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import time

# 尝试导入语音库
try:
    import speech_recognition as sr
    HAS_SPEECH_RECOGNITION = True
except ImportError:
    HAS_SPEECH_RECOGNITION = False

try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False


class VoiceInputState(Enum):
    """语音输入状态"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class VoiceRecognitionResult:
    """语音识别结果"""
    text: str
    confidence: float = 0.0
    language: str = "zh-CN"
    is_command: bool = False
    command_type: Optional[str] = None


class SpeechRecognizer:
    """语音识别器"""

    # 支持的语言
    LANGUAGES = {
        "zh-CN": "中文（简体）",
        "zh-TW": "中文（繁体）",
        "en-US": "英语（美国）",
        "ja-JP": "日语",
        "ko-KR": "韩语",
    }

    # 语音命令关键词
    COMMANDS = {
        "起名": "name_generator",
        "取名": "name_generator",
        "名字": "name_generator",
        "骰子": "dice",
        "掷骰子": "dice",
        "提示卡": "prompt_card",
        "灵感": "prompt_card",
        "计时": "timer",
        "开始计时": "timer",
        "停止": "stop",
        "暂停": "pause",
        "继续": "continue",
        "帮助": "help",
        "字数": "word_count",
        "统计": "word_count",
    }

    def __init__(self, language: str = "zh-CN"):
        self.language = language
        self._recognizer: Optional[sr.Recognizer] = None
        self._microphone: Optional[sr.Microphone] = None
        self._is_available = False
        self._state = VoiceInputState.IDLE
        self._callback: Optional[Callable[[VoiceRecognitionResult], None]] = None
        self._error_callback: Optional[Callable[[str], None]] = None
        self._listening_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._init_recognizer()

    def _init_recognizer(self):
        """初始化识别器"""
        if not HAS_SPEECH_RECOGNITION:
            self._is_available = False
            return

        try:
            self._recognizer = sr.Recognizer()
            # 调整能量阈值以适应环境噪音
            self._recognizer.energy_threshold = 4000
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 0.8  # 停顿时间

            # 测试麦克风
            self._microphone = sr.Microphone()
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)

            self._is_available = True
        except Exception as e:
            self._is_available = False
            print(f"语音识别初始化失败: {e}")

    @property
    def is_available(self) -> bool:
        """检查语音识别是否可用"""
        return self._is_available

    @property
    def state(self) -> VoiceInputState:
        """获取当前状态"""
        return self._state

    def set_callbacks(self,
                      on_result: Callable[[VoiceRecognitionResult], None] = None,
                      on_error: Callable[[str], None] = None):
        """设置回调函数"""
        self._callback = on_result
        self._error_callback = on_error

    def start_listening(self, continuous: bool = False):
        """开始监听语音"""
        if not self._is_available:
            if self._error_callback:
                self._error_callback("语音识别不可用，请检查麦克风和依赖库")
            return

        if self._state == VoiceInputState.LISTENING:
            return

        self._stop_event.clear()
        self._state = VoiceInputState.LISTENING

        if continuous:
            self._listening_thread = threading.Thread(
                target=self._continuous_listen,
                daemon=True
            )
        else:
            self._listening_thread = threading.Thread(
                target=self._single_listen,
                daemon=True
            )

        self._listening_thread.start()

    def stop_listening(self):
        """停止监听"""
        self._stop_event.set()
        self._state = VoiceInputState.IDLE

    def _single_listen(self):
        """单次监听"""
        try:
            with self._microphone as source:
                audio = self._recognizer.listen(source, timeout=5, phrase_time_limit=10)

            self._state = VoiceInputState.PROCESSING
            self._process_audio(audio)

        except sr.WaitTimeoutError:
            self._state = VoiceInputState.IDLE
            if self._error_callback:
                self._error_callback("没有检测到语音输入")
        except Exception as e:
            self._state = VoiceInputState.ERROR
            if self._error_callback:
                self._error_callback(f"语音识别错误: {str(e)}")

        self._state = VoiceInputState.IDLE

    def _continuous_listen(self):
        """连续监听"""
        while not self._stop_event.is_set():
            try:
                with self._microphone as source:
                    audio = self._recognizer.listen(source, timeout=2, phrase_time_limit=5)

                self._state = VoiceInputState.PROCESSING
                self._process_audio(audio)
                self._state = VoiceInputState.LISTENING

            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                if self._error_callback and not self._stop_event.is_set():
                    self._error_callback(f"语音识别错误: {str(e)}")
                time.sleep(0.5)

        self._state = VoiceInputState.IDLE

    def _process_audio(self, audio):
        """处理音频并识别"""
        try:
            # 使用Google语音识别
            text = self._recognizer.recognize_google(
                audio,
                language=self.language
            )

            # 检查是否是命令
            is_command = False
            command_type = None
            for keyword, cmd in self.COMMANDS.items():
                if keyword in text:
                    is_command = True
                    command_type = cmd
                    break

            result = VoiceRecognitionResult(
                text=text,
                language=self.language,
                is_command=is_command,
                command_type=command_type
            )

            if self._callback:
                self._callback(result)

        except sr.UnknownValueError:
            if self._error_callback:
                self._error_callback("无法识别语音内容")
        except sr.RequestError as e:
            if self._error_callback:
                self._error_callback(f"语音服务请求失败: {str(e)}")

    def set_language(self, language: str):
        """设置识别语言"""
        if language in self.LANGUAGES:
            self.language = language


class TextToSpeech:
    """文本转语音"""

    # 支持的语音
    VOICES = {
        "chinese": {"name": "中文女声", "lang": "zh"},
        "english": {"name": "英文女声", "lang": "en"},
    }

    def __init__(self):
        self._engine: Optional[pyttsx3.Engine] = None
        self._is_available = False
        self._is_speaking = False
        self._speech_queue: queue.Queue = queue.Queue()
        self._speech_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 语音设置
        self._rate = 180  # 语速 (words per minute)
        self._volume = 0.9  # 音量 (0.0-1.0)
        self._voice_id = None

        self._init_engine()

    def _init_engine(self):
        """初始化TTS引擎"""
        if not HAS_TTS:
            self._is_available = False
            return

        try:
            self._engine = pyttsx3.init()

            # 设置语速和音量
            self._engine.setProperty('rate', self._rate)
            self._engine.setProperty('volume', self._volume)

            # 获取可用语音
            voices = self._engine.getProperty('voices')
            if voices:
                # 尝试找到中文语音
                for voice in voices:
                    if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                        self._voice_id = voice.id
                        break
                    elif 'huihui' in voice.name.lower():  # Windows中文语音
                        self._voice_id = voice.id
                        break

                if self._voice_id:
                    self._engine.setProperty('voice', self._voice_id)

            self._is_available = True

            # 启动语音队列处理线程
            self._speech_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._speech_thread.start()

        except Exception as e:
            self._is_available = False
            print(f"TTS初始化失败: {e}")

    @property
    def is_available(self) -> bool:
        """检查TTS是否可用"""
        return self._is_available

    @property
    def is_speaking(self) -> bool:
        """检查是否正在朗读"""
        return self._is_speaking

    def speak(self, text: str, priority: bool = False):
        """朗读文本"""
        if not self._is_available:
            return

        if priority:
            # 优先队列，清空当前队列
            self.stop()
            with self._speech_queue.mutex:
                self._speech_queue.queue.clear()

        self._speech_queue.put(text)

    def stop(self):
        """停止朗读"""
        if self._engine and self._is_speaking:
            self._engine.stop()
            self._is_speaking = False

    def _process_queue(self):
        """处理语音队列"""
        while True:
            try:
                text = self._speech_queue.get(timeout=1)
                self._is_speaking = True

                # 分段朗读（避免长文本问题）
                segments = self._split_text(text)
                for segment in segments:
                    if not self._is_speaking:
                        break
                    self._engine.say(segment)
                    self._engine.runAndWait()

                self._is_speaking = False
                self._speech_queue.task_done()

            except queue.Empty:
                continue
            except Exception:
                self._is_speaking = False

    def _split_text(self, text: str, max_length: int = 200) -> List[str]:
        """分割长文本"""
        if len(text) <= max_length:
            return [text]

        segments = []
        # 按句子分割
        sentences = text.replace('。', '。\n').replace('！', '！\n').replace('？', '？\n').split('\n')

        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) <= max_length:
                current += sentence
            else:
                if current:
                    segments.append(current)
                current = sentence

        if current:
            segments.append(current)

        return segments

    def set_rate(self, rate: int):
        """设置语速 (50-300)"""
        self._rate = max(50, min(300, rate))
        if self._engine:
            self._engine.setProperty('rate', self._rate)

    def set_volume(self, volume: float):
        """设置音量 (0.0-1.0)"""
        self._volume = max(0.0, min(1.0, volume))
        if self._engine:
            self._engine.setProperty('volume', self._volume)

    def get_available_voices(self) -> List[Dict[str, str]]:
        """获取可用语音列表"""
        if not self._engine:
            return []

        voices = self._engine.getProperty('voices')
        return [{"id": v.id, "name": v.name} for v in voices]

    def set_voice(self, voice_id: str):
        """设置语音"""
        if self._engine:
            self._voice_id = voice_id
            self._engine.setProperty('voice', voice_id)


class VoiceAssistant:
    """语音助手 - 整合语音识别和TTS"""

    def __init__(self, on_voice_input: Callable[[str], None] = None,
                 on_command: Callable[[str], None] = None):
        self.recognizer = SpeechRecognizer()
        self.tts = TextToSpeech()

        self._on_voice_input = on_voice_input
        self._on_command = on_command

        # 设置识别回调
        self.recognizer.set_callbacks(
            on_result=self._on_recognition_result,
            on_error=self._on_recognition_error
        )

        # 状态
        self._listening_mode = False
        self._auto_speak_response = True

    @property
    def is_available(self) -> bool:
        """检查语音功能是否可用"""
        return self.recognizer.is_available or self.tts.is_available

    @property
    def has_recognition(self) -> bool:
        """是否有语音识别"""
        return self.recognizer.is_available

    @property
    def has_tts(self) -> bool:
        """是否有TTS"""
        return self.tts.is_available

    def _on_recognition_result(self, result: VoiceRecognitionResult):
        """处理识别结果"""
        if result.is_command and self._on_command:
            self._on_command(result.command_type)
        elif self._on_voice_input:
            self._on_voice_input(result.text)

    def _on_recognition_error(self, error: str):
        """处理识别错误"""
        if self._auto_speak_response:
            self.tts.speak(error)

    def start_voice_input(self, continuous: bool = False):
        """开始语音输入"""
        self._listening_mode = True
        self.recognizer.start_listening(continuous)

    def stop_voice_input(self):
        """停止语音输入"""
        self._listening_mode = False
        self.recognizer.stop_listening()

    def speak_response(self, text: str):
        """朗读响应"""
        if self._auto_speak_response:
            self.tts.speak(text)

    def set_auto_speak(self, enabled: bool):
        """设置是否自动朗读响应"""
        self._auto_speak_response = enabled

    def read_text(self, text: str):
        """朗读指定文本"""
        self.tts.speak(text)

    def stop_reading(self):
        """停止朗读"""
        self.tts.stop()

    def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            "recognition_available": self.recognizer.is_available,
            "tts_available": self.tts.is_available,
            "listening": self._listening_mode,
            "speaking": self.tts.is_speaking,
            "language": self.recognizer.language,
        }


# 工具函数
def check_voice_dependencies() -> Dict[str, bool]:
    """检查语音依赖"""
    return {
        "speech_recognition": HAS_SPEECH_RECOGNITION,
        "pyttsx3": HAS_TTS,
    }


def get_installation_guide() -> str:
    """获取安装指南"""
    guide = "语音功能依赖安装指南：\n\n"

    if not HAS_SPEECH_RECOGNITION:
        guide += "1. 语音识别 (SpeechRecognition):\n"
        guide += "   pip install SpeechRecognition\n"
        guide += "   pip install pyaudio\n\n"
        guide += "   Windows用户可能需要:\n"
        guide += "   pip install pipwin\n"
        guide += "   pipwin install pyaudio\n\n"

    if not HAS_TTS:
        guide += "2. 文本转语音 (pyttsx3):\n"
        guide += "   pip install pyttsx3\n\n"

    if HAS_SPEECH_RECOGNITION and HAS_TTS:
        guide = "所有语音依赖已安装完成！"

    return guide
