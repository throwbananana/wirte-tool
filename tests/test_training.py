import unittest
from writer_app.core.training import TrainingManager

class TestTrainingManager(unittest.TestCase):
    def setUp(self):
        self.manager = TrainingManager()

    def test_get_words(self):
        levels = self.manager.get_levels()
        self.assertIn("级别1（具象词汇）", levels)
        
        words = self.manager.get_words("级别1（具象词汇）", count=3)
        self.assertTrue(len(words) >= 1)
        for word in words[:3]:
            self.assertIsInstance(word, str)

    def test_get_ai_prompt(self):
        level = "级别1（具象词汇）"
        words = ["猫", "门", "雨"]
        content = "猫坐在门边，雨声不断。"
        
        exercise_data = {"level": level, "words": words}
        prompt = self.manager.get_analysis_prompt("keywords", exercise_data, content)
        
        self.assertIn("评分", prompt)
        self.assertIn("score_1", prompt)
        self.assertIn(content, prompt)
        self.assertIn("JSON", prompt)

if __name__ == '__main__':
    unittest.main()
