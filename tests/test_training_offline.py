import unittest
from writer_app.core.training import TrainingManager, LocalTrainingScorer
from writer_app.core.analysis import TextMetrics

class TestTrainingOffline(unittest.TestCase):
    def setUp(self):
        self.manager = TrainingManager()

    def test_text_metrics(self):
        text = "Hello world. 你好世界。"
        self.assertEqual(TextMetrics.count_words(text), 6) # 2 English words + 4 Chinese chars
        self.assertEqual(TextMetrics.count_sentences(text), 2)
        
    def test_offline_scoring(self):
        exercise_data = {"words": ["Cat"]}
        content = "The cat is here. It is nice."
        score_report = LocalTrainingScorer.evaluate("keywords", exercise_data, content)
        
        self.assertIn("scores", score_report)
        self.assertIn("feedback", score_report)
        self.assertIn("=== 离线分析报告 ===", score_report["feedback"])
        self.assertGreaterEqual(score_report["scores"].get("total", 0), 0)

    def test_offline_starter(self):
        starter = self.manager.get_offline_starter("show_dont_tell")
        self.assertTrue(len(starter) > 0)
        self.assertIsInstance(starter, str)

if __name__ == '__main__':
    unittest.main()
