"""
AI线程池管理器 - 提供受控的异步任务执行

用法:
    from writer_app.core.thread_pool import get_ai_thread_pool

    pool = get_ai_thread_pool()

    # 提交任务
    pool.submit(
        task_id="outline_generation",
        fn=generate_outline,
        url, model, key, text,  # 参数
        on_success=lambda result: print(f"成功: {result}"),
        on_error=lambda e: print(f"失败: {e}"),
        on_complete=lambda: print("完成")
    )

    # 取消任务
    pool.cancel("outline_generation")

    # 关闭线程池
    pool.shutdown()
"""

from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Optional, Dict
import threading
import logging
import time

logger = logging.getLogger(__name__)


class AIThreadPool:
    """
    AI任务线程池。

    解决的问题:
    - 限制并发线程数量（防止资源耗尽）
    - 提供任务取消机制
    - 统一错误处理和回调
    - 支持 tkinter 主线程回调
    """

    _instance: Optional['AIThreadPool'] = None
    _lock = threading.Lock()

    def __new__(cls, max_workers: int = 3):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_workers: int = 3):
        if self._initialized:
            return

        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="ai_worker"
        )
        self._futures: Dict[str, Future] = {}
        self._task_info: Dict[str, dict] = {}
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0
        }
        self._initialized = True
        logger.info(f"AI线程池初始化完成，最大工作线程: {max_workers}")

    def submit(self, task_id: str, fn: Callable, *args,
               on_success: Optional[Callable[[Any], None]] = None,
               on_error: Optional[Callable[[Exception], None]] = None,
               on_complete: Optional[Callable[[], None]] = None,
               tk_root: Any = None) -> Optional[Future]:
        """
        提交任务到线程池。

        Args:
            task_id: 任务唯一标识（同ID的新任务会取消旧任务）
            fn: 要执行的函数
            *args: 函数参数
            on_success: 成功回调 (result) -> None
            on_error: 错误回调 (exception) -> None
            on_complete: 完成回调（无论成功失败都会调用）
            tk_root: Tkinter root（如果提供，回调将在主线程执行）

        Returns:
            Future 对象，如果任务被取消则返回 None
        """
        # 取消同ID的旧任务
        self.cancel(task_id)

        def wrapped():
            start_time = time.time()
            try:
                result = fn(*args)
                elapsed = time.time() - start_time
                logger.debug(f"任务 '{task_id}' 完成，耗时 {elapsed:.2f}s")

                self._stats["completed"] += 1

                if on_success:
                    if tk_root:
                        tk_root.after(0, lambda: on_success(result))
                    else:
                        on_success(result)

                return result

            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"任务 '{task_id}' 失败，耗时 {elapsed:.2f}s: {e}", exc_info=True)

                self._stats["failed"] += 1

                if on_error:
                    if tk_root:
                        tk_root.after(0, lambda: on_error(e))
                    else:
                        on_error(e)

                raise

            finally:
                if on_complete:
                    if tk_root:
                        tk_root.after(0, on_complete)
                    else:
                        on_complete()

                # 清理任务记录
                self._futures.pop(task_id, None)
                self._task_info.pop(task_id, None)

        try:
            future = self._executor.submit(wrapped)
            self._futures[task_id] = future
            self._task_info[task_id] = {
                "start_time": time.time(),
                "fn_name": fn.__name__ if hasattr(fn, '__name__') else str(fn)
            }
            self._stats["submitted"] += 1

            logger.debug(f"任务 '{task_id}' 已提交")
            return future

        except Exception as e:
            logger.error(f"提交任务 '{task_id}' 失败: {e}")
            return None

    def cancel(self, task_id: str) -> bool:
        """
        取消任务。

        Args:
            task_id: 任务标识

        Returns:
            是否成功取消
        """
        future = self._futures.pop(task_id, None)
        self._task_info.pop(task_id, None)

        if future and not future.done():
            cancelled = future.cancel()
            if cancelled:
                self._stats["cancelled"] += 1
                logger.debug(f"任务 '{task_id}' 已取消")
            return cancelled

        return False

    def cancel_all(self) -> int:
        """
        取消所有任务。

        Returns:
            取消的任务数量
        """
        count = 0
        for task_id in list(self._futures.keys()):
            if self.cancel(task_id):
                count += 1
        return count

    def is_running(self, task_id: str) -> bool:
        """检查任务是否正在运行。"""
        future = self._futures.get(task_id)
        return future is not None and not future.done()

    def get_active_count(self) -> int:
        """获取活跃任务数量。"""
        return sum(1 for f in self._futures.values() if not f.done())

    def get_stats(self) -> dict:
        """获取统计信息。"""
        return {
            **self._stats,
            "active": self.get_active_count(),
            "max_workers": self._max_workers
        }

    def get_task_info(self, task_id: str) -> Optional[dict]:
        """获取任务信息。"""
        info = self._task_info.get(task_id)
        if info:
            return {
                **info,
                "elapsed": time.time() - info["start_time"],
                "running": self.is_running(task_id)
            }
        return None

    def shutdown(self, wait: bool = True, cancel_pending: bool = True) -> None:
        """
        关闭线程池。

        Args:
            wait: 是否等待任务完成
            cancel_pending: 是否取消待处理任务
        """
        if cancel_pending:
            self.cancel_all()

        self._executor.shutdown(wait=wait)
        logger.info(f"AI线程池已关闭，统计: {self._stats}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown(wait=True)


# 全局单例访问函数
_thread_pool_instance: Optional[AIThreadPool] = None


def get_ai_thread_pool(max_workers: int = 3) -> AIThreadPool:
    """获取AI线程池单例。"""
    global _thread_pool_instance
    if _thread_pool_instance is None:
        _thread_pool_instance = AIThreadPool(max_workers=max_workers)
    return _thread_pool_instance


def shutdown_thread_pool(wait: bool = True) -> None:
    """关闭全局线程池。"""
    global _thread_pool_instance
    if _thread_pool_instance is not None:
        _thread_pool_instance.shutdown(wait=wait)
        _thread_pool_instance = None
    # Reset the class-level singleton as well; otherwise a shut down instance
    # can be returned and reject new submissions.
    AIThreadPool._instance = None
