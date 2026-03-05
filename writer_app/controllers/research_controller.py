import requests
import re
from typing import List, Tuple, Callable
from tkinter import messagebox
from writer_app.core.event_bus import get_event_bus, Events
from writer_app.core.thread_pool import get_ai_thread_pool


class ResearchController:
    def __init__(self, view, project_manager, execute_command=None):
        self.view = view
        self.project_manager = project_manager
        self.execute_command = execute_command

        # Lifecycle tracking (手动实现，因为不继承 BaseController)
        self._destroyed = False
        self._event_subscriptions: List[Tuple[str, Callable]] = []

        self.view.set_controller(self)
        self._subscribe_events()

    def _subscribe_event(self, event_type: str, handler: Callable) -> None:
        """订阅事件并追踪以便清理"""
        bus = get_event_bus()
        bus.subscribe(event_type, handler)
        self._event_subscriptions.append((event_type, handler))

    def cleanup(self) -> None:
        """清理所有追踪的资源"""
        self._destroyed = True

        # 取消订阅 EventBus
        bus = get_event_bus()
        for event_type, handler in self._event_subscriptions:
            try:
                bus.unsubscribe(event_type, handler)
            except Exception:
                pass
        self._event_subscriptions.clear()

    def _subscribe_events(self):
        """订阅事件总线以自动刷新（使用追踪方法以便清理）"""
        self._subscribe_event(Events.PROJECT_LOADED, self._on_project_loaded)

    def _on_project_loaded(self, event_type=None, **kwargs):
        """响应项目加载事件"""
        self.refresh()

    def fetch_url(self, url):
        """Fetch content from URL using thread pool."""
        if not url.startswith("http"):
            url = "http://" + url

        self.view.update_status("正在获取内容...", True)

        def _task():
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding

            html = response.text
            title = self._extract_title(html)
            text = self._extract_text(html)
            return (title, text, url)

        def on_success(result):
            title, text, source_url = result
            self.view.on_fetch_success(title, text, source_url)

        def on_error(e):
            self.view.on_fetch_error(str(e))

        pool = get_ai_thread_pool()
        pool.submit(
            task_id="research_fetch_url",
            fn=_task,
            on_success=on_success,
            on_error=on_error,
            tk_root=self.view.root
        )

    def _extract_title(self, html):
        match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return "New Research"

    def _extract_text(self, html):
        """Basic HTML to Text converter without BS4."""
        # Remove script and style
        text = re.sub(r'<(script|style).*?>.*?</\1>', '', html, flags=re.IGNORECASE | re.DOTALL)
        # Remove comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        # Replace breaks with newlines
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        # Remove all other tags
        text = re.sub(r'<[^>]+>', '', text)
        # Fix entities (basic)
        text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')
        # Cleanup whitespace
        lines = [line.strip() for line in text.splitlines()]
        text = '\n'.join(line for line in lines if line)
        return text

    def add_item(self, title, content, url, tags):
        self.project_manager.add_research_item(title, content, url, tags)
        self.view.refresh_list()

    def update_item(self, uid, data):
        self.project_manager.update_research_item(uid, data)
        self.view.refresh_list()

    def delete_item(self, uid):
        if messagebox.askyesno("确认删除", "确定要删除这条资料吗？"):
            self.project_manager.delete_research_item(uid)
            self.view.refresh_list()

    def add_to_wiki(self, item):
        """Convert research item to wiki entry."""
        name = item.get("title", "New Entry")
        content = f"来源: {item.get('source_url', '')}\n\n{item.get('content', '')}"
        
        # Check duplicate
        entries = self.project_manager.get_world_entries()
        if any(e["name"] == name for e in entries):
            messagebox.showwarning("提示", f"词条 '{name}' 已存在")
            return

        from writer_app.core.commands import AddWikiEntryCommand
        if self.execute_command:
            cmd = AddWikiEntryCommand(
                self.project_manager,
                {"name": name, "category": "资料", "content": content},
                f"从资料库添加: {name}"
            )
            self.execute_command(cmd)
            messagebox.showinfo("成功", f"已添加词条: {name}")
        else:
            # Fallback
            entries.append({"name": name, "category": "资料", "content": content})
            self.project_manager.mark_modified()
            messagebox.showinfo("成功", f"已添加词条: {name}")

    def refresh(self):
        self.view.refresh_list()
