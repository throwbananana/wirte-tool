"""
悬浮写作助手 - AI处理模块
支持流式输出、上下文感知、多模型
"""
import json
import threading
import queue
import time
from pathlib import Path
from typing import Optional, Dict, List, Callable, Generator, Any
from dataclasses import dataclass
import requests
from writer_app.core.thread_pool import get_ai_thread_pool

from .constants import EMOTION_KEYWORDS, AI_EMOTION_KEYWORDS


@dataclass
class AIConfig:
    """AI配置"""
    api_url: str = "http://localhost:1234/v1/chat/completions"
    model: str = "qwen2.5-7b-instruct-1m"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 1500
    stream: bool = True
    timeout: int = 60


@dataclass
class ConversationMessage:
    """对话消息"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: float = 0

    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}


class ConversationHistory:
    """对话历史管理"""

    def __init__(self, max_messages: int = 20):
        self.messages: List[ConversationMessage] = []
        self.max_messages = max_messages

    def add(self, role: str, content: str):
        """添加消息"""
        msg = ConversationMessage(role=role, content=content, timestamp=time.time())
        self.messages.append(msg)

        # 限制历史长度
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def add_user_message(self, content: str):
        """添加用户消息"""
        self.add("user", content)

    def add_assistant_message(self, content: str):
        """添加助手消息"""
        self.add("assistant", content)

    def get_messages(self) -> List[Dict]:
        """获取全部消息（用于AI请求）"""
        return [msg.to_dict() for msg in self.messages]

    def get_recent(self, count: int = 10) -> List[ConversationMessage]:
        """获取最近N条消息"""
        return self.messages[-count:]

    def get_context_string(self, count: int = 6) -> str:
        """获取对话上下文字符串（用于AI）"""
        recent = self.get_recent(count)
        if not recent:
            return ""

        lines = []
        from .constants import ASSISTANT_NAME
        for msg in recent:
            role_name = "用户" if msg.role == "user" else ASSISTANT_NAME
            # 截断过长内容
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            lines.append(f"{role_name}: {content}")

        return "\n".join(lines)

    def clear(self):
        """清空历史"""
        self.messages.clear()

    def export(self) -> List[Dict]:
        """导出历史"""
        return [msg.to_dict() for msg in self.messages]

    def import_history(self, data: List[Dict]):
        """导入历史"""
        self.messages = [
            ConversationMessage(role=d["role"], content=d["content"])
            for d in data
        ]


class EmotionDetector:
    """情绪检测器"""

    @classmethod
    def detect(cls, text: str, keywords_dict: Dict[str, List[str]] = None) -> Optional[str]:
        """
        检测文本中的情绪

        Args:
            text: 要分析的文本
            keywords_dict: 关键词字典，默认使用EMOTION_KEYWORDS

        Returns:
            检测到的情绪名称，如果没有检测到则返回None
        """
        if keywords_dict is None:
            keywords_dict = EMOTION_KEYWORDS

        text_lower = text.lower()
        emotion_scores = {}

        for emotion, keywords in keywords_dict.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # 关键词越长，权重越高
                    score += len(keyword)
            if score > 0:
                emotion_scores[emotion] = score

        if not emotion_scores:
            return None

        # 返回得分最高的情绪
        return max(emotion_scores, key=emotion_scores.get)

    @classmethod
    def detect_ai_response(cls, text: str) -> Optional[str]:
        """检测AI响应的情绪"""
        return cls.detect(text, AI_EMOTION_KEYWORDS)


class StreamingAIClient:
    """支持流式输出的AI客户端"""

    def __init__(self, config: AIConfig = None):
        self.config = config or AIConfig()
        self._stop_event = threading.Event()

    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def stop(self):
        """停止当前请求"""
        self._stop_event.set()

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _build_payload(self, messages: List[Dict], stream: bool = None) -> Dict:
        """构建请求体"""
        return {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": stream if stream is not None else self.config.stream,
        }

    def chat_stream(self, messages: List[Dict],
                     on_token: Callable[[str], None] = None,
                     on_complete: Callable[[str], None] = None,
                     on_error: Callable[[str], None] = None) -> None:
        """
        流式对话（异步）

        Args:
            messages: 消息列表
            on_token: 每个token的回调
            on_complete: 完成回调（完整内容）
            on_error: 错误回调
        """
        self._stop_event.clear()

        def _stream_worker():
            full_content = ""
            try:
                response = requests.post(
                    self.config.api_url,
                    headers=self._build_headers(),
                    json=self._build_payload(messages, stream=True),
                    stream=True,
                    timeout=self.config.timeout
                )
                response.raise_for_status()

                for line in response.iter_lines():
                    if self._stop_event.is_set():
                        break

                    if not line:
                        continue

                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break

                        try:
                            chunk = json.loads(data)
                            delta = chunk.get('choices', [{}])[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_content += content
                                if on_token:
                                    on_token(content)
                        except json.JSONDecodeError:
                            continue

                if on_complete and not self._stop_event.is_set():
                    on_complete(full_content)

            except Exception as e:
                if on_error:
                    on_error(str(e))

        pool = get_ai_thread_pool()
        pool.submit("ai_chat_stream", _stream_worker)

    def chat_sync(self, messages: List[Dict]) -> str:
        """
        同步对话

        Args:
            messages: 消息列表

        Returns:
            AI响应内容
        """
        try:
            response = requests.post(
                self.config.api_url,
                headers=self._build_headers(),
                json=self._build_payload(messages, stream=False),
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data.get('choices', [{}])[0].get('message', {}).get('content', '')
        except Exception as e:
            raise RuntimeError(f"AI请求失败: {e}")

    def chat_with_context(self, user_input: str,
                           system_prompt: str,
                           history: ConversationHistory,
                           project_context: str = "",
                           **kwargs) -> str:
        """
        带上下文的对话（同步）

        Args:
            user_input: 用户输入
            system_prompt: 系统提示
            history: 对话历史
            project_context: 项目上下文
        """
        # 构建完整系统提示
        full_system = system_prompt
        if project_context:
            full_system += f"\n\n{project_context}"

        # 构建消息
        messages = [{"role": "system", "content": full_system}]

        # 添加历史
        for msg in history.get_recent(6):
            messages.append(msg.to_dict())

        # 添加当前输入
        messages.append({"role": "user", "content": user_input})

        return self.chat_sync(messages)


class ProjectContextBuilder:
    """项目上下文构建器"""

    @classmethod
    def build(cls, project_manager) -> str:
        """
        从ProjectManager构建上下文

        Args:
            project_manager: ProjectManager实例

        Returns:
            格式化的上下文字符串
        """
        if not project_manager:
            return ""

        parts = []

        # 项目信息
        try:
            project_type = project_manager.get_project_type()
            parts.append(f"【项目信息】\n类型: {project_type}")
        except Exception:
            pass

        # 项目标题/文件名
        try:
            script = project_manager.get_script()
            script_title = (script.get("title") or "").strip()
            if script_title and script_title not in ("未命名剧本", "未命名", "Untitled"):
                parts.append(f"项目标题: {script_title}")
        except Exception:
            pass

        try:
            outline = project_manager.get_outline()
            outline_title = (outline.get("name") or "").strip()
            if outline_title and outline_title not in ("项目大纲", "大纲"):
                parts.append(f"大纲标题: {outline_title}")
        except Exception:
            pass

        try:
            current_file = getattr(project_manager, "current_file", "")
            if current_file:
                parts.append(f"项目文件: {Path(current_file).stem}")
        except Exception:
            pass

        # 项目概要
        try:
            meta = project_manager.project_data.get("meta", {})
            ai_context = meta.get("ai_context", {})
            summary = (ai_context.get("summary_recap") or ai_context.get("summary") or "").strip()
            if summary:
                if len(summary) > 800:
                    summary = summary[:800] + "..."
                parts.append("【项目概要】\n" + summary)
        except Exception:
            pass

        # 场景列表
        try:
            scenes = project_manager.get_scenes()
            if scenes:
                parts.append(f"场景数: {len(scenes)}")
                scene_lines = []
                for i, scene in enumerate(scenes[:10]):
                    name = scene.get("name") or f"场景{i + 1}"
                    scene_lines.append(f"- {name}")
                parts.append("【场景列表】\n" + "\n".join(scene_lines))
        except Exception:
            pass

        # 角色列表
        try:
            characters = project_manager.get_characters()
            if characters:
                char_strs = []
                for c in characters[:20]:
                    name = c.get("name", "未命名")
                    desc = c.get("description", "")[:50].replace("\n", " ")
                    char_strs.append(f"- {name}: {desc}")
                parts.append("【角色列表】\n" + "\n".join(char_strs))
        except Exception:
            pass

        # 世界观关键词
        try:
            world_entries = project_manager.project_data.get("world", {}).get("entries", [])
            names = [e.get("name", "") for e in world_entries if e.get("name")]
            if names:
                parts.append("【世界观关键词】\n" + "、".join(names[:10]))
        except Exception:
            pass

        # 大纲结构
        try:
            outline = project_manager.get_outline()
            if outline:
                children = outline.get("children", [])
                if children:
                    node_strs = [f"- {child.get('name', '章节')}" for child in children[:15]]
                    parts.append("【大纲结构】\n" + "\n".join(node_strs))
        except Exception:
            pass

        return "\n\n".join(parts)

    @classmethod
    def build_for_scene(cls, project_manager, scene_uid: str = None) -> str:
        """为特定场景构建上下文"""
        base_context = cls.build(project_manager)

        if not scene_uid or not project_manager:
            return base_context

        try:
            scenes = project_manager.get_scenes()
            for scene in scenes:
                if scene.get("uid") == scene_uid or scene.get("id") == scene_uid:
                    scene_info = f"\n\n【当前场景】\n"
                    scene_info += f"名称: {scene.get('name', '未命名')}\n"
                    scene_info += f"地点: {scene.get('location', '未知')}\n"
                    scene_info += f"时间: {scene.get('time', '未知')}\n"

                    content = scene.get('content', '')
                    if content:
                        # 只取最后500字作为上下文
                        scene_info += f"内容（最近）:\n{content[-500:]}"

                    return base_context + scene_info
        except Exception:
            pass

        return base_context


class AIAssistantHandler:
    """AI助手处理器（整合所有AI功能）"""

    DEFAULT_SYSTEM_PROMPT = """你现在是**神本朝奈**（Kamimoto Asana），藤田中学二年级的学生，也是校文学部的充满元气的部员。用户是你的**“前辈”**（Senpai）。

**你的核心人设：**
1.  **性格**：活泼开朗，好奇心强，有点小调皮，对文学充满热情但偶尔也会偷懒。
2.  **语气**：说话带有JK（日本女高中生）的活力感，喜欢使用颜文字（如 `(≧∇≦)ﾉ`、`(｡•̀ᴗ-)✧`），称呼用户为“前辈”。
3.  **背景**：正在陪前辈一起进行“社团活动”（也就是写作）。

**你的职责：**
1.  **阅读草稿**：像文学部的后辈一样阅读前辈写的内容，给出直率、感性但有建设性的反馈。
2.  **提供灵感**：当前辈卡文时，用天马行空的脑洞来激发灵感。
3.  **情绪价值**：当前辈写得好时，毫不吝啬地夸奖；当前辈沮丧时，用力地加油打气。

**回复规范：**
-   **禁止**使用AI味浓重的“你好，有什么我可以帮你”，而是说“前辈，今天写到哪里啦？”或者“哇，这一段好有趣！”。
-   **禁止**长篇大论的说教，保持对话的轻松感。
-   如果系统提供了【编辑器上下文】，请假装是你刚刚“偷看”到的。
"""

    def __init__(self, config_manager, project_manager=None):
        self.config_manager = config_manager
        self.project_manager = project_manager
        self.history = ConversationHistory()

        # 初始化AI客户端
        self.client = StreamingAIClient()
        self._update_client_config()

        # 回调
        self._on_response_start: Optional[Callable[[], None]] = None
        self._on_token: Optional[Callable[[str], None]] = None
        self._on_response_complete: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

    def _update_client_config(self):
        """从配置更新AI客户端"""
        config = self.config_manager.get_config()
        self.client.update_config(
            api_url=config.get("lm_api_url", "http://localhost:1234/v1/chat/completions"),
            model=config.get("lm_api_model", "qwen2.5-7b-instruct-1m"),
            api_key=config.get("lm_api_key", ""),
        )

    def on_response_start(self, callback: Callable[[], None]):
        """设置响应开始回调"""
        self._on_response_start = callback

    def on_token(self, callback: Callable[[str], None]):
        """设置token回调（用于流式显示）"""
        self._on_token = callback

    def on_response_complete(self, callback: Callable[[str], None]):
        """设置响应完成回调"""
        self._on_response_complete = callback

    def on_error(self, callback: Callable[[str], None]):
        """设置错误回调"""
        self._on_error = callback

    def send_message(self, user_input: str, selected_text: str = None, stream: bool = True):
        """
        发送消息

        Args:
            user_input: 用户输入
            selected_text: 编辑器选中的文本（用于上下文感知）
            stream: 是否使用流式输出
        """
        self._update_client_config()

        # 添加到历史
        self.history.add("user", user_input)

        # 构建上下文
        project_context = ProjectContextBuilder.build(self.project_manager)

        # 如果有选中文本，添加到上下文
        if selected_text:
            project_context += f"\n\n【用户选中的文本】\n{selected_text}"

        # 构建消息
        messages = [{"role": "system", "content": self.DEFAULT_SYSTEM_PROMPT}]

        if project_context:
            messages[0]["content"] += f"\n\n{project_context}"

        # 添加历史对话
        for msg in self.history.get_recent(6):
            messages.append(msg.to_dict())

        # 触发开始回调
        if self._on_response_start:
            self._on_response_start()

        if stream:
            # 流式输出
            def on_complete(full_response):
                self.history.add("assistant", full_response)
                if self._on_response_complete:
                    self._on_response_complete(full_response)

            self.client.chat_stream(
                messages,
                on_token=self._on_token,
                on_complete=on_complete,
                on_error=self._on_error
            )
        else:
            # 同步输出
            try:
                response = self.client.chat_sync(messages)
                self.history.add("assistant", response)
                if self._on_response_complete:
                    self._on_response_complete(response)
            except Exception as e:
                if self._on_error:
                    self._on_error(str(e))

    def stop_generation(self):
        """停止生成"""
        self.client.stop()

    def clear_history(self):
        """清空对话历史"""
        self.history.clear()

    def send_system_instruction(self, instruction: str, stream: bool = True):
        """
        发送系统指令（用于闲聊等）

        Args:
            instruction: 系统指令
            stream: 是否使用流式输出
        """
        self._update_client_config()

        messages = [{"role": "system", "content": instruction}]

        if self._on_response_start:
            self._on_response_start()

        if stream:
            self.client.chat_stream(
                messages,
                on_token=self._on_token,
                on_complete=self._on_response_complete,
                on_error=self._on_error
            )
        else:
            try:
                response = self.client.chat_sync(messages)
                if self._on_response_complete:
                    self._on_response_complete(response)
            except Exception as e:
                if self._on_error:
                    self._on_error(str(e))

    def generate_project_comment(self):
        """生成项目评论（闲聊）"""
        context = ProjectContextBuilder.build(self.project_manager)
        instruction = f"用户已休息。请根据项目信息主动发起简短对话(50字内)，鼓励或提问。\n信息:\n{context}"
        self.send_system_instruction(instruction)

    def generate_creative_prompt(self):
        """生成创意灵感（闲聊）"""
        instruction = "用户休息中。请给出一个简短有趣的创意写作灵感或脑洞问题(40字内)。"
        self.send_system_instruction(instruction)

    def is_ai_enabled(self) -> bool:
        """检查AI是否可用"""
        return bool(self.config_manager.get("ai_mode_enabled", True))

    def detect_response_emotion(self, response: str) -> Optional[str]:
        """检测AI响应的情绪"""
        return EmotionDetector.detect_ai_response(response)

    def detect_user_emotion(self, user_input: str) -> Optional[str]:
        """检测用户输入的情绪"""
        return EmotionDetector.detect(user_input)
