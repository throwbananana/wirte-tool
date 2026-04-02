# Writer Tool 全面修复与重构计划

## 概述

本计划解决系统中发现的 120+ 个问题，按优先级分阶段实施。

---

## 第一阶段：架构重构（高优先级）

### 1.1 拆分 main.py (1763行 → 多个模块)

**问题**: `WriterTool` 类有 97 个方法，违反单一职责原则

**解决方案**: 创建以下新模块：

```
writer_app/
├── app.py                    # 新主入口，精简版 WriterTool
├── core/
│   ├── controller_registry.py # 控制器注册和管理
│   ├── app_state.py          # 应用状态管理
│   └── exceptions.py         # 自定义异常类
```

**新建 `controller_registry.py`**:
```python
class ControllerRegistry:
    """统一管理所有控制器的注册、刷新和销毁"""

    def __init__(self):
        self._controllers = {}
        self._refresh_groups = {}  # 按事件类型分组

    def register(self, key: str, controller, refresh_groups: list = None):
        """注册控制器"""
        self._controllers[key] = controller
        for group in (refresh_groups or ["all"]):
            self._refresh_groups.setdefault(group, []).append(key)

    def refresh_group(self, group: str):
        """刷新特定组的控制器"""
        for key in self._refresh_groups.get(group, []):
            if key in self._controllers:
                self._controllers[key].refresh()

    def refresh_all(self):
        """刷新所有控制器"""
        for controller in self._controllers.values():
            controller.refresh()

    def get(self, key: str):
        """获取控制器"""
        return self._controllers.get(key)

    def has(self, key: str) -> bool:
        """检查控制器是否存在"""
        return key in self._controllers
```

**重构后的事件处理**（替代76个hasattr检查）:
```python
# 之前
if hasattr(self, "script_controller"): self.script_controller.refresh()
if hasattr(self, "timeline_controller"): self.timeline_controller.refresh()
# ... 重复20次

# 之后
self.registry.refresh_group("scene")  # 一行代码刷新所有场景相关控制器
```

### 1.2 统一通知机制

**问题**: 同时使用 `ProjectManager.add_listener()` 和 `EventBus`

**解决方案**: 全部迁移到 EventBus，废弃旧的 listener 模式

```python
# 修改 ProjectManager.mark_modified()
def mark_modified(self, event_type="all"):
    self.modified = True
    # 移除: self.notify_listeners(event_type)
    # 改为通过 EventBus 发布
    get_event_bus().publish(Events.PROJECT_MODIFIED, event_type=event_type)
```

---

## 第二阶段：线程安全修复（高优先级）

### 2.1 创建线程池管理器

**问题**: AIController 无限制创建守护线程

**新建 `core/thread_pool.py`**:
```python
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Optional
import threading
import logging

logger = logging.getLogger(__name__)

class AIThreadPool:
    """AI任务线程池，限制并发数量并提供取消机制"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_workers: int = 3):
        if self._initialized:
            return
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ai_worker")
        self._futures: dict[str, Future] = {}
        self._initialized = True

    def submit(self, task_id: str, fn: Callable, *args,
               on_success: Callable = None,
               on_error: Callable = None,
               on_complete: Callable = None) -> Future:
        """提交任务到线程池"""

        # 取消同ID的旧任务
        self.cancel(task_id)

        def wrapped():
            try:
                result = fn(*args)
                if on_success:
                    on_success(result)
                return result
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}", exc_info=True)
                if on_error:
                    on_error(e)
                raise
            finally:
                if on_complete:
                    on_complete()
                self._futures.pop(task_id, None)

        future = self._executor.submit(wrapped)
        self._futures[task_id] = future
        return future

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        future = self._futures.pop(task_id, None)
        if future and not future.done():
            return future.cancel()
        return False

    def cancel_all(self):
        """取消所有任务"""
        for task_id in list(self._futures.keys()):
            self.cancel(task_id)

    def shutdown(self, wait: bool = True):
        """关闭线程池"""
        self._executor.shutdown(wait=wait)

def get_ai_thread_pool() -> AIThreadPool:
    return AIThreadPool()
```

### 2.2 重构 AIController 使用线程池

```python
# ai_controller.py 修改
from writer_app.core.thread_pool import get_ai_thread_pool

class AIController:
    def __init__(self, main_app):
        self.app = main_app
        self.pool = get_ai_thread_pool()

    def generate_outline(self, script_text):
        url, model, key = self.get_api_config()
        if not url or not model:
            self.app.messagebox.showwarning("提示", "请配置AI接口")
            return

        self.app._set_ai_generation_state(True, "生成思维导图...")

        # 使用线程池替代裸线程
        self.pool.submit(
            task_id="outline_generation",
            fn=self._run_outline_generation,
            args=(url, model, key, script_text),
            on_success=lambda result: self.root.after(0, lambda: self._apply_result(result)),
            on_error=lambda e: self.root.after(0, lambda: self._show_error(e)),
            on_complete=lambda: self.root.after(0, lambda: self._set_state(False))
        )
```

---

## 第三阶段：错误处理改进（中优先级）

### 3.1 创建自定义异常类

**新建 `core/exceptions.py`**:
```python
class WriterToolError(Exception):
    """基础异常类"""
    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        self.cause = cause

class ProjectLoadError(WriterToolError):
    """项目加载错误"""
    pass

class ProjectSaveError(WriterToolError):
    """项目保存错误"""
    pass

class AIServiceError(WriterToolError):
    """AI服务错误"""
    def __init__(self, message: str, cause: Exception = None, retryable: bool = False):
        super().__init__(message, cause)
        self.retryable = retryable

class ValidationError(WriterToolError):
    """数据验证错误"""
    def __init__(self, message: str, field: str = None):
        super().__init__(message)
        self.field = field

class CommandExecutionError(WriterToolError):
    """命令执行错误"""
    pass
```

### 3.2 改进 models.py 错误处理

```python
# models.py 修改
from writer_app.core.exceptions import ProjectLoadError, ProjectSaveError

def load_project(self, file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            self.project_data = json.load(f)
    except FileNotFoundError:
        raise ProjectLoadError(f"文件不存在: {file_path}")
    except json.JSONDecodeError as e:
        raise ProjectLoadError(f"无效的项目文件格式: {e}", cause=e)
    except PermissionError as e:
        raise ProjectLoadError(f"没有读取权限: {file_path}", cause=e)
    except Exception as e:
        raise ProjectLoadError(f"加载失败: {e}", cause=e)

    # 迁移和验证...
```

### 3.3 AIClient 添加重试逻辑

```python
# ai_client.py 修改
from writer_app.core.exceptions import AIServiceError

def call_lm_studio_with_prompts(self, api_url, model, api_key, system_prompt, user_prompt,
                                  temperature=0.7, max_tokens=2000,
                                  timeout=60, retries=2):
    """带重试的API调用"""
    last_error = None

    for attempt in range(retries + 1):
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            # ... 处理响应
            return content

        except requests.Timeout as e:
            last_error = AIServiceError("API请求超时", cause=e, retryable=True)
        except requests.ConnectionError as e:
            last_error = AIServiceError("无法连接到AI服务", cause=e, retryable=True)
        except requests.HTTPError as e:
            if e.response.status_code >= 500:
                last_error = AIServiceError(f"服务器错误: {e.response.status_code}", cause=e, retryable=True)
            else:
                raise AIServiceError(f"请求失败: {e.response.status_code}", cause=e, retryable=False)

        if attempt < retries:
            time.sleep(1 * (attempt + 1))  # 指数退避

    raise last_error
```

---

## 第四阶段：性能优化（中优先级）

### 4.1 递归改迭代（防止栈溢出）

```python
# models.py 修改
def find_node_by_uid(self, root, target_uid):
    """迭代版本，防止深层大纲栈溢出"""
    if root is None:
        return None

    stack = [root]
    while stack:
        node = stack.pop()
        if node.get("uid") == target_uid:
            return node
        stack.extend(node.get("children", []))

    return None

def find_parent_of_node_by_uid(self, root, target_node_uid):
    """迭代版本"""
    if root is None:
        return None

    stack = [(root, None)]  # (node, parent)
    while stack:
        node, parent = stack.pop()
        if node.get("uid") == target_node_uid:
            return parent
        for child in node.get("children", []):
            stack.append((child, node))

    return None
```

### 4.2 精细化刷新（替代全量刷新）

使用 ControllerRegistry 的分组刷新：

```python
# main.py 中的事件处理简化
def _setup_event_subscriptions(self):
    bus = get_event_bus()

    # 场景事件 -> 只刷新场景相关控制器
    bus.subscribe_multiple([
        Events.SCENE_ADDED, Events.SCENE_UPDATED, Events.SCENE_DELETED
    ], lambda evt, **kw: self.registry.refresh_group("scene"))

    # 角色事件 -> 只刷新角色相关控制器
    bus.subscribe_multiple([
        Events.CHARACTER_ADDED, Events.CHARACTER_UPDATED, Events.CHARACTER_DELETED
    ], lambda evt, **kw: self.registry.refresh_group("character"))

    # 移除旧的 on_project_data_changed 全量刷新
```

### 4.3 优化保存操作

```python
# models.py 修改 - 避免双重序列化
def save_project(self, file_path=None):
    path = file_path or self.current_file
    if not path:
        raise ProjectSaveError("未指定保存路径")

    try:
        # 直接序列化到文件，避免 json.loads(json.dumps(...))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.project_data, f, ensure_ascii=False, indent=2)

        self.current_file = path
        self.modified = False
        get_event_bus().publish(Events.PROJECT_SAVED, path=path)
    except Exception as e:
        raise ProjectSaveError(f"保存失败: {e}", cause=e)
```

---

## 第五阶段：代码质量改进（中优先级）

### 5.1 添加数据验证层

**新建 `core/validators.py`**:
```python
from typing import List, Optional, Dict, Any
from writer_app.core.exceptions import ValidationError

class Validator:
    """数据验证基类"""

    @staticmethod
    def required(value, field_name: str):
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"{field_name} 不能为空", field=field_name)
        return value

    @staticmethod
    def max_length(value: str, max_len: int, field_name: str):
        if value and len(value) > max_len:
            raise ValidationError(f"{field_name} 长度不能超过 {max_len}", field=field_name)
        return value

class CharacterValidator(Validator):
    """角色数据验证"""

    @classmethod
    def validate(cls, data: dict) -> dict:
        cls.required(data.get("name"), "角色名称")
        cls.max_length(data.get("name", ""), 100, "角色名称")
        return data

class SceneValidator(Validator):
    """场景数据验证"""

    @classmethod
    def validate(cls, data: dict) -> dict:
        cls.required(data.get("name"), "场景名称")
        return data

class OutlineNodeValidator(Validator):
    """大纲节点验证"""

    @classmethod
    def validate(cls, data: dict) -> dict:
        cls.required(data.get("name"), "节点名称")
        # 确保有 uid
        if not data.get("uid"):
            import uuid
            data["uid"] = uuid.uuid4().hex
        return data
```

### 5.2 Command 类添加验证

```python
# commands.py 修改
class AddCharacterCommand(Command):
    def __init__(self, project_manager, char_data, description="添加角色"):
        super().__init__(description)
        self.project_manager = project_manager
        # 验证数据
        self.char_data = CharacterValidator.validate(json.loads(json.dumps(char_data)))
        self.added_index = -1

    def execute(self):
        # 检查重复
        existing = self.project_manager.get_characters()
        if any(c.get("name") == self.char_data.get("name") for c in existing):
            raise ValidationError(f"角色 '{self.char_data.get('name')}' 已存在")

        # ... 执行添加
```

---

## 第六阶段：资源管理修复（中优先级）

### 6.1 图片资源清理

```python
# wiki_controller.py 修改
class WikiController(BaseController):
    def __init__(self, ...):
        super().__init__(...)
        self._image_cache = {}  # 缓存图片引用
        self._max_cache_size = 50

    def _load_image(self, path: str):
        """带缓存的图片加载"""
        if path in self._image_cache:
            return self._image_cache[path]

        # LRU 清理
        if len(self._image_cache) >= self._max_cache_size:
            oldest = next(iter(self._image_cache))
            del self._image_cache[oldest]

        img = Image.open(path)
        self._image_cache[path] = img
        return img

    def cleanup(self):
        """清理资源"""
        self._image_cache.clear()
```

### 6.2 音频资源管理

```python
# main.py 修改
def on_closing(self):
    """应用关闭时清理资源"""
    # 停止音频
    if hasattr(self, "ambiance_player"):
        self.ambiance_player.stop()

    # 停止备份
    if hasattr(self, "backup_manager"):
        self.backup_manager.stop()

    # 关闭线程池
    get_ai_thread_pool().shutdown(wait=False)

    # 保存配置
    self._save_config()

    self.root.destroy()
```

---

## 第七阶段：测试补充（低优先级）

### 7.1 新增测试文件

```
tests/
├── test_controller_registry.py  # 控制器注册测试
├── test_thread_pool.py          # 线程池测试
├── test_validators.py           # 验证器测试
├── test_exceptions.py           # 异常类测试
└── test_integration.py          # 集成测试
```

### 7.2 示例测试

```python
# tests/test_controller_registry.py
import unittest
from writer_app.core.controller_registry import ControllerRegistry

class MockController:
    def __init__(self):
        self.refresh_count = 0
    def refresh(self):
        self.refresh_count += 1

class TestControllerRegistry(unittest.TestCase):
    def test_register_and_refresh(self):
        registry = ControllerRegistry()
        ctrl1 = MockController()
        ctrl2 = MockController()

        registry.register("script", ctrl1, refresh_groups=["scene", "character"])
        registry.register("timeline", ctrl2, refresh_groups=["scene"])

        registry.refresh_group("scene")

        self.assertEqual(ctrl1.refresh_count, 1)
        self.assertEqual(ctrl2.refresh_count, 1)

    def test_refresh_all(self):
        registry = ControllerRegistry()
        ctrl = MockController()
        registry.register("test", ctrl)

        registry.refresh_all()

        self.assertEqual(ctrl.refresh_count, 1)
```

---

## 实施顺序

| 阶段 | 内容 | 预计文件数 | 风险等级 |
|------|------|-----------|---------|
| 1 | 架构重构 | 5 | 高 |
| 2 | 线程安全 | 2 | 中 |
| 3 | 错误处理 | 3 | 低 |
| 4 | 性能优化 | 2 | 低 |
| 5 | 代码质量 | 2 | 低 |
| 6 | 资源管理 | 2 | 低 |
| 7 | 测试补充 | 5 | 无 |

---

## 新增/修改文件清单

### 新建文件
1. `writer_app/core/controller_registry.py` - 控制器注册管理
2. `writer_app/core/thread_pool.py` - AI线程池
3. `writer_app/core/exceptions.py` - 自定义异常
4. `writer_app/core/validators.py` - 数据验证器
5. `tests/test_controller_registry.py`
6. `tests/test_thread_pool.py`
7. `tests/test_validators.py`

### 修改文件
1. `writer_app/main.py` - 重构使用 ControllerRegistry
2. `writer_app/core/models.py` - 错误处理 + 迭代算法
3. `writer_app/controllers/ai_controller.py` - 使用线程池
4. `writer_app/utils/ai_client.py` - 重试逻辑
5. `writer_app/core/commands.py` - 添加验证
6. `writer_app/controllers/wiki_controller.py` - 资源清理

---

## 向后兼容性

- 保留 `ProjectManager.add_listener()` 方法但标记为 deprecated
- 保留 `on_project_data_changed()` 方法但内部改为调用 EventBus
- 新旧代码可以并行运行，逐步迁移

---

## 回滚策略

每个阶段完成后创建 git tag:
- `refactor/phase-1-architecture`
- `refactor/phase-2-threading`
- `refactor/phase-3-error-handling`
- ...

如遇问题可快速回滚到上一个稳定版本。
