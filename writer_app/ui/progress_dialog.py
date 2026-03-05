"""
进度对话框模块 - 用于显示长时间操作的进度
"""
import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Optional, Callable, Any


class ProgressDialog(tk.Toplevel):
    """
    进度对话框 - 支持确定性和不确定性进度显示

    使用示例:
        # 确定性进度
        dialog = ProgressDialog(parent, "导出中", "正在导出文件...")
        dialog.set_progress(50)  # 设置进度为50%
        dialog.set_message("正在处理第 5/10 个文件...")
        dialog.close()

        # 不确定性进度（持续动画）
        dialog = ProgressDialog(parent, "处理中", "请稍候...", indeterminate=True)
        dialog.start_indeterminate()
        # ... 执行操作 ...
        dialog.close()

        # 使用 run_with_progress 自动管理
        def long_task(update_progress):
            for i in range(100):
                time.sleep(0.1)
                update_progress(i + 1, f"处理中 {i+1}/100")
            return "完成"

        result = ProgressDialog.run_with_progress(parent, "处理中", long_task)
    """

    def __init__(self, parent, title: str = "处理中",
                 message: str = "请稍候...",
                 indeterminate: bool = False,
                 cancellable: bool = False,
                 on_cancel: Optional[Callable] = None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)

        self.indeterminate = indeterminate
        self.cancellable = cancellable
        self.on_cancel = on_cancel
        self.cancelled = False
        self._closed = False

        self.setup_ui(message)

        # 禁止关闭按钮（除非可取消）
        if not cancellable:
            self.protocol("WM_DELETE_WINDOW", lambda: None)
        else:
            self.protocol("WM_DELETE_WINDOW", self._do_cancel)

        # 居中显示
        self.update_idletasks()
        width = 400
        height = 150 if cancellable else 120
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.resizable(False, False)
        self.grab_set()

    def setup_ui(self, message: str):
        """创建UI元素"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 消息标签
        self.message_var = tk.StringVar(value=message)
        self.message_label = ttk.Label(main_frame, textvariable=self.message_var,
                                        wraplength=360)
        self.message_label.pack(fill=tk.X, pady=(0, 10))

        # 进度条
        if self.indeterminate:
            self.progressbar = ttk.Progressbar(main_frame, mode='indeterminate',
                                                length=360)
        else:
            self.progress_var = tk.DoubleVar(value=0)
            self.progressbar = ttk.Progressbar(main_frame, mode='determinate',
                                                variable=self.progress_var,
                                                maximum=100, length=360)
        self.progressbar.pack(fill=tk.X, pady=(0, 10))

        # 进度文本（仅确定性模式）
        if not self.indeterminate:
            self.percent_var = tk.StringVar(value="0%")
            self.percent_label = ttk.Label(main_frame, textvariable=self.percent_var)
            self.percent_label.pack()

        # 取消按钮
        if self.cancellable:
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill=tk.X, pady=(10, 0))
            self.cancel_btn = ttk.Button(btn_frame, text="取消", command=self._do_cancel)
            self.cancel_btn.pack()

    def set_message(self, message: str):
        """更新消息文本"""
        if not self._closed:
            self.message_var.set(message)
            self.update_idletasks()

    def set_progress(self, value: float, message: Optional[str] = None):
        """
        设置进度值 (0-100)

        Args:
            value: 进度值，0-100
            message: 可选的消息更新
        """
        if self._closed or self.indeterminate:
            return

        value = max(0, min(100, value))
        self.progress_var.set(value)
        self.percent_var.set(f"{int(value)}%")

        if message:
            self.message_var.set(message)

        self.update_idletasks()

    def start_indeterminate(self):
        """开始不确定性进度动画"""
        if not self._closed and self.indeterminate:
            self.progressbar.start(10)

    def stop_indeterminate(self):
        """停止不确定性进度动画"""
        if not self._closed and self.indeterminate:
            self.progressbar.stop()

    def _do_cancel(self):
        """处理取消操作"""
        self.cancelled = True
        if self.on_cancel:
            self.on_cancel()
        self.close()

    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self.cancelled

    def close(self):
        """关闭对话框"""
        if self._closed:
            return
        self._closed = True

        if self.indeterminate:
            self.progressbar.stop()

        self.grab_release()
        self.destroy()

    @staticmethod
    def run_with_progress(parent, title: str, task: Callable,
                          message: str = "处理中...",
                          indeterminate: bool = False,
                          cancellable: bool = False) -> Any:
        """
        在进度对话框中运行任务

        Args:
            parent: 父窗口
            title: 对话框标题
            task: 任务函数，签名为 task(update_progress) 或 task()
                  update_progress(value, message) 用于更新进度
            message: 初始消息
            indeterminate: 是否使用不确定性模式
            cancellable: 是否可取消

        Returns:
            任务返回值，如果取消则返回None
        """
        result = [None]
        error = [None]
        dialog = ProgressDialog(parent, title, message, indeterminate, cancellable)

        if indeterminate:
            dialog.start_indeterminate()

        def update_progress(value: float, msg: Optional[str] = None):
            if not dialog._closed and dialog.winfo_exists():
                dialog.after(0, lambda: dialog.set_progress(value, msg) if dialog.winfo_exists() else None)

        def run_task():
            try:
                # 检查任务是否接受参数
                import inspect
                sig = inspect.signature(task)
                if len(sig.parameters) > 0:
                    result[0] = task(update_progress)
                else:
                    result[0] = task()
            except Exception as e:
                error[0] = e
            finally:
                if not dialog._closed and dialog.winfo_exists():
                    dialog.after(0, lambda: dialog.close() if dialog.winfo_exists() else None)

        # 在后台线程运行任务
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        # 等待对话框关闭
        parent.wait_window(dialog)

        if error[0]:
            raise error[0]

        if dialog.cancelled:
            return None

        return result[0]


class BatchProgressDialog(tk.Toplevel):
    """
    批量操作进度对话框 - 显示多个步骤的进度

    使用示例:
        dialog = BatchProgressDialog(parent, "批量导出", ["导出场景", "导出角色", "导出设定"])
        dialog.start_step(0, "正在导出场景...")
        dialog.update_step_progress(0, 50)
        dialog.complete_step(0)
        dialog.start_step(1, "正在导出角色...")
        # ...
        dialog.close()
    """

    def __init__(self, parent, title: str, steps: list,
                 cancellable: bool = False,
                 on_cancel: Optional[Callable] = None):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)

        self.steps = steps
        self.cancellable = cancellable
        self.on_cancel = on_cancel
        self.cancelled = False
        self._closed = False

        self.step_vars = []
        self.step_progress = []
        self.step_status = []

        self.setup_ui()

        if not cancellable:
            self.protocol("WM_DELETE_WINDOW", lambda: None)
        else:
            self.protocol("WM_DELETE_WINDOW", self._do_cancel)

        # 居中显示
        self.update_idletasks()
        width = 450
        height = 100 + len(steps) * 50
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.resizable(False, False)
        self.grab_set()

    def setup_ui(self):
        """创建UI元素"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 总进度
        self.total_var = tk.StringVar(value=f"总进度: 0/{len(self.steps)}")
        ttk.Label(main_frame, textvariable=self.total_var,
                  font=('', 10, 'bold')).pack(anchor=tk.W)

        self.total_progress = tk.DoubleVar(value=0)
        ttk.Progressbar(main_frame, variable=self.total_progress,
                        maximum=100, length=400).pack(fill=tk.X, pady=(5, 15))

        # 各步骤进度
        for i, step in enumerate(self.steps):
            step_frame = ttk.Frame(main_frame)
            step_frame.pack(fill=tk.X, pady=3)

            # 状态图标
            status_var = tk.StringVar(value="○")
            status_label = ttk.Label(step_frame, textvariable=status_var, width=2)
            status_label.pack(side=tk.LEFT)
            self.step_status.append(status_var)

            # 步骤名称和消息
            msg_var = tk.StringVar(value=step)
            ttk.Label(step_frame, textvariable=msg_var, width=25,
                      anchor=tk.W).pack(side=tk.LEFT)
            self.step_vars.append(msg_var)

            # 步骤进度条
            prog_var = tk.DoubleVar(value=0)
            ttk.Progressbar(step_frame, variable=prog_var,
                            maximum=100, length=150).pack(side=tk.LEFT, padx=5)
            self.step_progress.append(prog_var)

        # 取消按钮
        if self.cancellable:
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill=tk.X, pady=(15, 0))
            ttk.Button(btn_frame, text="取消", command=self._do_cancel).pack()

    def start_step(self, index: int, message: Optional[str] = None):
        """开始一个步骤"""
        if self._closed or index >= len(self.steps):
            return

        self.step_status[index].set("●")
        if message:
            self.step_vars[index].set(message)
        self.update_idletasks()

    def update_step_progress(self, index: int, value: float, message: Optional[str] = None):
        """更新步骤进度"""
        if self._closed or index >= len(self.steps):
            return

        self.step_progress[index].set(max(0, min(100, value)))
        if message:
            self.step_vars[index].set(message)
        self._update_total()
        self.update_idletasks()

    def complete_step(self, index: int, message: Optional[str] = None):
        """完成一个步骤"""
        if self._closed or index >= len(self.steps):
            return

        self.step_status[index].set("✓")
        self.step_progress[index].set(100)
        if message:
            self.step_vars[index].set(message)
        self._update_total()
        self.update_idletasks()

    def fail_step(self, index: int, message: Optional[str] = None):
        """标记步骤失败"""
        if self._closed or index >= len(self.steps):
            return

        self.step_status[index].set("✗")
        if message:
            self.step_vars[index].set(message)
        self.update_idletasks()

    def _update_total(self):
        """更新总进度"""
        completed = sum(1 for v in self.step_progress if v.get() >= 100)
        self.total_var.set(f"总进度: {completed}/{len(self.steps)}")

        avg = sum(v.get() for v in self.step_progress) / len(self.steps)
        self.total_progress.set(avg)

    def _do_cancel(self):
        """处理取消"""
        self.cancelled = True
        if self.on_cancel:
            self.on_cancel()
        self.close()

    def is_cancelled(self) -> bool:
        return self.cancelled

    def close(self):
        """关闭对话框"""
        if self._closed:
            return
        self._closed = True
        self.grab_release()
        self.destroy()
