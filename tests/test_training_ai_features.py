import unittest
from writer_app.core.training import TrainingManager
from writer_app.controllers.training_controller import TrainingController
from unittest.mock import MagicMock

class TestTrainingAIFeatures(unittest.TestCase):
    def setUp(self):
        self.manager = TrainingManager()
        
        # Mock dependencies for Controller test
        self.mock_view = MagicMock()
        self.mock_pm = MagicMock()
        self.mock_tm = MagicMock()
        self.mock_ai = MagicMock()
        self.mock_cfg = MagicMock()
        self.mock_cfg.is_ai_enabled.return_value = True
        self.mock_tm.add_listener = MagicMock()
        
        self.controller = TrainingController(
            self.mock_view, self.mock_pm, self.mock_tm, self.mock_ai, self.mock_cfg
        )

    def test_get_word_generation_prompt(self):
        topic = "Cyberpunk"
        level = "Level 3"
        prompt = self.manager.get_word_generation_prompt(topic, level, count=5)
        
        self.assertIn("Cyberpunk", prompt)
        self.assertIn("Level 3", prompt)
        self.assertIn("JSON", prompt)

    def test_handle_keywords_generation_updates_prompt(self):
        url = "http://test"
        model = "test-model"
        key = "key"
        topic = "Fantasy"
        level = "Level 1"

        self.controller._get_ai_config = MagicMock(return_value=(url, model, key))
        self.controller.current_exercise_data = {}

        self.mock_ai.call_lm_studio_with_prompts.return_value = '["Dragon", "Magic"]'
        self.mock_ai.extract_json_from_text.return_value = ["Dragon", "Magic"]

        def run_submit(task_id, func, *args, success_callback=None, error_callback=None, **_kwargs):
            try:
                result = func(*args)
            except Exception as exc:
                if error_callback:
                    error_callback(exc)
                return None
            if success_callback:
                success_callback(result)
            return None

        self.controller._submit_ai_task = run_submit

        self.controller._active_prompt_request_id = 1
        self.controller._handle_keywords_generation(topic, level, "", is_challenge=False, request_id=1)

        self.mock_ai.call_lm_studio_with_prompts.assert_called_once()
        self.mock_ai.extract_json_from_text.assert_called_once()
        self.assertEqual(self.controller.current_exercise_data.get("words"), ["Dragon", "Magic"])
        self.mock_view.update_prompt_display.assert_called_once_with("关键词（AI生成）：Dragon, Magic")

if __name__ == '__main__':
    unittest.main()
