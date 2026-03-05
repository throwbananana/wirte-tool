"""
测试safe_after工具函数

测试内容：
- widget销毁后的安全回调
- job追踪和取消
- 辅助类AfterJobTracker
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import tkinter as tk


class TestSafeAfterFunction(unittest.TestCase):
    """测试safe_after工具函数"""

    def test_safe_after_returns_none_when_widget_destroyed(self):
        """测试当widget已销毁时safe_after返回None"""
        from writer_app.utils.tk_utils import safe_after

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = False

        callback = Mock()
        result = safe_after(mock_widget, 100, callback)

        self.assertIsNone(result)
        mock_widget.after.assert_not_called()

    def test_safe_after_schedules_when_widget_exists(self):
        """测试当widget存在时safe_after正确调度"""
        from writer_app.utils.tk_utils import safe_after

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = True
        mock_widget.after.return_value = "job_123"

        callback = Mock()
        result = safe_after(mock_widget, 100, callback)

        self.assertIsNotNone(result)
        mock_widget.after.assert_called_once()

    def test_safe_after_with_job_tracker(self):
        """测试safe_after使用job追踪器"""
        from writer_app.utils.tk_utils import safe_after

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = True
        mock_widget.after.return_value = "job_456"

        job_tracker = {}
        callback = Mock()

        result = safe_after(mock_widget, 100, callback, job_tracker=job_tracker, job_id="my_job")

        self.assertEqual(result, "job_456")
        self.assertIn("my_job", job_tracker)
        self.assertEqual(job_tracker["my_job"], "job_456")


class TestCancelAfter(unittest.TestCase):
    """测试cancel_after工具函数"""

    def test_cancel_after_cancels_job(self):
        """测试cancel_after正确取消任务"""
        from writer_app.utils.tk_utils import cancel_after

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = True

        job_tracker = {"my_job": "job_789"}

        result = cancel_after(mock_widget, job_tracker, "my_job")

        self.assertTrue(result)
        mock_widget.after_cancel.assert_called_once_with("job_789")
        self.assertNotIn("my_job", job_tracker)

    def test_cancel_after_returns_false_for_missing_job(self):
        """测试cancel_after对不存在的任务返回False"""
        from writer_app.utils.tk_utils import cancel_after

        mock_widget = Mock()
        job_tracker = {}

        result = cancel_after(mock_widget, job_tracker, "nonexistent_job")

        self.assertFalse(result)
        mock_widget.after_cancel.assert_not_called()


class TestCancelAllAfter(unittest.TestCase):
    """测试cancel_all_after工具函数"""

    def test_cancel_all_after_cancels_all_jobs(self):
        """测试cancel_all_after取消所有任务"""
        from writer_app.utils.tk_utils import cancel_all_after

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = True

        job_tracker = {
            "job1": "id_1",
            "job2": "id_2",
            "job3": "id_3"
        }

        count = cancel_all_after(mock_widget, job_tracker)

        self.assertEqual(count, 3)
        self.assertEqual(len(job_tracker), 0)
        self.assertEqual(mock_widget.after_cancel.call_count, 3)


class TestAfterJobTracker(unittest.TestCase):
    """测试AfterJobTracker辅助类"""

    def test_schedule_job(self):
        """测试调度任务"""
        from writer_app.utils.tk_utils import AfterJobTracker

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = True
        mock_widget.after.return_value = "job_id"

        tracker = AfterJobTracker(mock_widget)
        callback = Mock()

        result = tracker.schedule("test_job", 100, callback)

        self.assertEqual(result, "job_id")
        self.assertIn("test_job", tracker._jobs)

    def test_cancel_job(self):
        """测试取消任务"""
        from writer_app.utils.tk_utils import AfterJobTracker

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = True
        mock_widget.after.return_value = "job_id"

        tracker = AfterJobTracker(mock_widget)
        callback = Mock()

        tracker.schedule("test_job", 100, callback)
        result = tracker.cancel("test_job")

        self.assertTrue(result)
        self.assertNotIn("test_job", tracker._jobs)

    def test_cancel_all(self):
        """测试取消所有任务"""
        from writer_app.utils.tk_utils import AfterJobTracker

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = True
        mock_widget.after.side_effect = ["id1", "id2", "id3"]

        tracker = AfterJobTracker(mock_widget)

        tracker.schedule("job1", 100, Mock())
        tracker.schedule("job2", 100, Mock())
        tracker.schedule("job3", 100, Mock())

        count = tracker.cancel_all()

        self.assertEqual(count, 3)
        self.assertEqual(len(tracker._jobs), 0)


class TestSafeDestroy(unittest.TestCase):
    """测试safe_destroy工具函数"""

    def test_safe_destroy_destroys_when_exists(self):
        """测试当widget存在时safe_destroy销毁它"""
        from writer_app.utils.tk_utils import safe_destroy

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = True

        result = safe_destroy(mock_widget)

        self.assertTrue(result)
        mock_widget.destroy.assert_called_once()

    def test_safe_destroy_returns_false_when_destroyed(self):
        """测试当widget已销毁时safe_destroy返回False"""
        from writer_app.utils.tk_utils import safe_destroy

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = False

        result = safe_destroy(mock_widget)

        self.assertFalse(result)
        mock_widget.destroy.assert_not_called()


class TestSafeConfigure(unittest.TestCase):
    """测试safe_configure工具函数"""

    def test_safe_configure_when_exists(self):
        """测试当widget存在时safe_configure正确配置"""
        from writer_app.utils.tk_utils import safe_configure

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = True

        result = safe_configure(mock_widget, bg="white", fg="black")

        self.assertTrue(result)
        mock_widget.configure.assert_called_once_with(bg="white", fg="black")

    def test_safe_configure_returns_false_when_destroyed(self):
        """测试当widget已销毁时safe_configure返回False"""
        from writer_app.utils.tk_utils import safe_configure

        mock_widget = Mock()
        mock_widget.winfo_exists.return_value = False

        result = safe_configure(mock_widget, bg="white")

        self.assertFalse(result)
        mock_widget.configure.assert_not_called()


if __name__ == '__main__':
    unittest.main()
