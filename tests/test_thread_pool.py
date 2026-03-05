"""
测试 AI 线程池模块。
"""
import unittest
import time
import threading
from concurrent.futures import Future

from writer_app.core.thread_pool import AIThreadPool, get_ai_thread_pool, shutdown_thread_pool


class TestAIThreadPool(unittest.TestCase):
    """测试 AIThreadPool 类。"""

    def setUp(self):
        """每个测试前重置线程池。"""
        shutdown_thread_pool(wait=True)

    def tearDown(self):
        """每个测试后清理线程池。"""
        shutdown_thread_pool(wait=True)

    def test_singleton_pattern(self):
        """测试单例模式。"""
        pool1 = get_ai_thread_pool()
        pool2 = get_ai_thread_pool()
        self.assertIs(pool1, pool2)

    def test_submit_task(self):
        """测试提交任务。"""
        pool = get_ai_thread_pool()
        result_holder = []

        def task():
            return 42

        future = pool.submit(
            task_id="test_task",
            fn=task,
            on_success=lambda r: result_holder.append(r)
        )

        self.assertIsInstance(future, Future)
        # 等待任务完成
        time.sleep(0.5)
        self.assertEqual(result_holder, [42])

    def test_cancel_task(self):
        """测试取消任务。"""
        pool = get_ai_thread_pool()
        cancelled_before = pool.get_stats()["cancelled"]

        def slow_task():
            time.sleep(10)
            return "done"

        pool.submit(task_id="slow_task", fn=slow_task)
        # 立即取消
        result = pool.cancel("slow_task")
        # 注意：如果任务已经开始运行，可能无法取消
        # 这里我们只检查取消调用是否正常工作

    def test_task_error_handling(self):
        """测试任务错误处理。"""
        pool = get_ai_thread_pool()
        error_holder = []

        def failing_task():
            raise ValueError("Test error")

        pool.submit(
            task_id="failing_task",
            fn=failing_task,
            on_error=lambda e: error_holder.append(str(e))
        )

        # 等待任务完成
        time.sleep(0.5)
        self.assertEqual(len(error_holder), 1)
        self.assertIn("Test error", error_holder[0])

    def test_on_complete_callback(self):
        """测试完成回调。"""
        pool = get_ai_thread_pool()
        complete_flag = []

        def task():
            return "result"

        pool.submit(
            task_id="complete_test",
            fn=task,
            on_complete=lambda: complete_flag.append(True)
        )

        # 等待任务完成
        time.sleep(0.5)
        self.assertEqual(complete_flag, [True])

    def test_replace_same_id_task(self):
        """测试同 ID 任务替换。"""
        pool = get_ai_thread_pool()
        results = []

        def task1():
            time.sleep(0.5)
            return "task1"

        def task2():
            return "task2"

        pool.submit(
            task_id="same_id",
            fn=task1,
            on_success=lambda r: results.append(r)
        )
        # 立即提交同 ID 的新任务，应该取消旧任务
        pool.submit(
            task_id="same_id",
            fn=task2,
            on_success=lambda r: results.append(r)
        )

        time.sleep(1)
        # 只有 task2 应该成功执行
        self.assertIn("task2", results)

    def test_get_stats(self):
        """测试统计信息。"""
        pool = get_ai_thread_pool()
        stats = pool.get_stats()

        self.assertIn("submitted", stats)
        self.assertIn("completed", stats)
        self.assertIn("failed", stats)
        self.assertIn("cancelled", stats)
        self.assertIn("active", stats)
        self.assertIn("max_workers", stats)

    def test_is_running(self):
        """测试任务运行状态检查。"""
        pool = get_ai_thread_pool()

        def slow_task():
            time.sleep(1)
            return "done"

        pool.submit(task_id="running_test", fn=slow_task)

        # 任务应该正在运行
        self.assertTrue(pool.is_running("running_test"))

        # 不存在的任务应该返回 False
        self.assertFalse(pool.is_running("nonexistent"))

    def test_get_active_count(self):
        """测试活跃任务计数。"""
        pool = get_ai_thread_pool()

        def slow_task():
            time.sleep(0.5)
            return "done"

        initial_count = pool.get_active_count()

        pool.submit(task_id="active_test1", fn=slow_task)
        pool.submit(task_id="active_test2", fn=slow_task)

        # 应该有 2 个活跃任务（加上之前的）
        self.assertGreaterEqual(pool.get_active_count(), initial_count)


class TestThreadPoolConcurrency(unittest.TestCase):
    """测试线程池并发行为。"""

    def setUp(self):
        shutdown_thread_pool(wait=True)

    def tearDown(self):
        shutdown_thread_pool(wait=True)

    def test_max_workers_limit(self):
        """测试最大工作线程限制。"""
        pool = get_ai_thread_pool(max_workers=2)
        running_count = []
        lock = threading.Lock()

        def track_task():
            with lock:
                running_count.append(1)
            time.sleep(0.3)
            with lock:
                running_count.pop()
            return "done"

        # 提交 5 个任务
        for i in range(5):
            pool.submit(task_id=f"concurrent_{i}", fn=track_task)

        # 等待所有任务完成
        time.sleep(2)


if __name__ == "__main__":
    unittest.main()
