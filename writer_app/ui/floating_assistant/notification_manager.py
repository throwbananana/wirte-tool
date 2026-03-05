"""
悬浮助手通知管理器 (Notification Manager)
负责消息队列、优先级排序、合并通知与防刷屏节流
"""
import time
import threading
from dataclasses import dataclass, field
from queue import PriorityQueue
from typing import Dict, Optional, Callable

@dataclass(order=True)
class Notification:
    priority: int
    content: str = field(compare=False)
    tag: str = field(compare=False, default="system")
    timestamp: float = field(compare=False, default_factory=time.time)
    group_id: Optional[str] = field(compare=False, default=None)  # 用于合并同类消息

class NotificationManager:
    # 优先级常量 (数字越小优先级越高)
    PRIORITY_HIGH = 10
    PRIORITY_MEDIUM = 50
    PRIORITY_LOW = 100

    def __init__(self, display_callback: Callable[[str, str], None]):
        """
        Args:
            display_callback: 显示消息的回调函数 (tag, content) -> None
        """
        self.display_callback = display_callback
        self.queue = PriorityQueue()
        self.is_displaying = False
        self.merge_window = 2.0  # 合并窗口期（秒）
        self.display_interval = 3.0  # 消息显示间隔（秒）
        
        # 缓存待合并的消息 {group_id: [count, timestamp, first_content]}
        self.pending_merges: Dict[str, Dict] = {}
        
        self._start_worker()

    def notify(self, content: str, tag: str = "system", priority: int = PRIORITY_MEDIUM, group_id: str = None):
        """
        添加通知
        
        Args:
            content: 消息内容
            tag: 消息标签 (system, achievement, etc.)
            priority: 优先级
            group_id: 分组ID，用于合并同类消息 (e.g., "add_character")
        """
        if group_id:
            self._handle_merge(content, tag, priority, group_id)
        else:
            self.queue.put(Notification(priority, content, tag))

    def _handle_merge(self, content: str, tag: str, priority: int, group_id: str):
        """处理消息合并"""
        now = time.time()
        if group_id in self.pending_merges:
            data = self.pending_merges[group_id]
            # 如果在窗口期内
            if now - data['timestamp'] < self.merge_window:
                data['count'] += 1
                data['timestamp'] = now  # 延长窗口
                return
            else:
                # 窗口过期，先结算旧的
                self._flush_merge(group_id)
        
        # 新建合并记录
        self.pending_merges[group_id] = {
            'count': 1,
            'timestamp': now,
            'content': content,
            'tag': tag,
            'priority': priority
        }
        
        # 启动延迟检查
        threading.Timer(self.merge_window + 0.1, lambda: self._check_merge_flush(group_id)).start()

    def _check_merge_flush(self, group_id: str):
        """检查是否可以结算合并消息"""
        if group_id not in self.pending_merges:
            return
            
        data = self.pending_merges[group_id]
        if time.time() - data['timestamp'] >= self.merge_window:
            self._flush_merge(group_id)

    def _flush_merge(self, group_id: str):
        """结算合并消息并加入队列"""
        if group_id not in self.pending_merges:
            return
            
        data = self.pending_merges.pop(group_id)
        count = data['count']
        content = data['content']
        
        final_content = content
        if count > 1:
            # 简单的合并文案，实际可根据业务定制
            final_content = f"{content} (x{count})"
            
        self.queue.put(Notification(data['priority'], final_content, data['tag']))

    def _start_worker(self):
        """启动处理线程"""
        def worker():
            while True:
                try:
                    if self.is_displaying:
                        time.sleep(0.5)
                        continue
                        
                    # 阻塞获取，直到有消息
                    # 注意：PriorityQueue是线程安全的
                    notification = self.queue.get()
                    
                    self.is_displaying = True
                    # 在主线程执行回调 (这就要求display_callback内部处理线程安全，通常用root.after)
                    self.display_callback(notification.tag, notification.content)
                    
                    # 显示间隔
                    time.sleep(self.display_interval)
                    self.is_displaying = False
                    self.queue.task_done()
                    
                except Exception as e:
                    print(f"Notification error: {e}")
                    self.is_displaying = False
                    
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
