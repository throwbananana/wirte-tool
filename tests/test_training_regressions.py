import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from writer_app.controllers.training_controller import TrainingController
from writer_app.core.thread_pool import shutdown_thread_pool
from writer_app.core.training_challenges import ChallengeManager, DEFAULT_CHALLENGES


class _DummyVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _TrainingViewStub:
    def __init__(self, mode_key="keywords"):
        self._mode_key = mode_key
        self.mode_var = _DummyVar("")
        self.level_var = _DummyVar("")
        self.topic_var = _DummyVar("")
        self.tag_var = _DummyVar("")
        self.generate_btn = SimpleNamespace(config=lambda **_kwargs: None)
        self.last_prompt = ""
        self.feedback_text = ""
        self.content = "他推开门，雨声落在身后。"

    def set_controller(self, _controller):
        return None

    def apply_theme(self):
        return None

    def refresh(self):
        return None

    def set_ai_mode_enabled(self, _enabled: bool):
        return None

    def get_selected_mode_key(self):
        return self._mode_key

    def set_selected_mode_key(self, mode_key: str):
        self._mode_key = mode_key

    def update_prompt_display(self, text: str):
        self.last_prompt = text

    def show_feedback(self, text: str):
        self.feedback_text = text

    def set_analyzing(self, _state: bool):
        return None

    def get_content(self):
        return self.content

    def after(self, _ms: int, callback):
        callback()


class TestTrainingRegressions(unittest.TestCase):
    def setUp(self):
        # Ensure the global thread pool is in a clean state for each test.
        shutdown_thread_pool(wait=True)

        self.view = _TrainingViewStub()
        self.project_manager = MagicMock()
        self.theme_manager = MagicMock()
        self.theme_manager.add_listener = MagicMock()
        self.theme_manager.remove_listener = MagicMock()
        self.ai_client = MagicMock()
        self.config_manager = MagicMock()
        self.config_manager.is_ai_enabled.return_value = False

        self.controller = TrainingController(
            self.view,
            self.project_manager,
            self.theme_manager,
            self.ai_client,
            self.config_manager,
        )

    def tearDown(self):
        shutdown_thread_pool(wait=True)

    def test_mode_change_clears_stale_exercise_state(self):
        self.controller.pool.cancel = MagicMock()

        self.controller.current_exercise_data = {"words": ["猫", "雨"]}
        self.controller.active_challenge_id = "c_desc_01"
        self.controller.challenge_prompt_text = "challenge"
        self.controller._active_prompt_request_id = 7

        self.view.set_selected_mode_key("brainstorm")
        self.controller.on_mode_changed()

        self.assertEqual(self.controller.current_mode, "brainstorm")
        self.assertEqual(self.controller.current_exercise_data, {})
        self.assertIsNone(self.controller.active_challenge_id)
        self.assertIsNone(self.controller.challenge_prompt_text)
        self.assertNotEqual(self.controller._active_prompt_request_id, 7)

        self.controller.pool.cancel.assert_any_call("setup_generation")
        self.controller.pool.cancel.assert_any_call("keyword_generation")

    def test_load_challenge_not_cleared_by_programmatic_mode_change(self):
        challenge = {
            "id": "c_desc_01",
            "mode": "keywords",
            "level": "级别1（具象词汇）",
            "topic": "日常物品",
            "title": "测试挑战",
            "description": "测试描述",
            "min_score": 20,
            "unlocked": True,
            "completed": False,
        }

        # Simulate a combobox callback firing during programmatic selection.
        def _select_mode_by_key(mode_key: str):
            self.view.set_selected_mode_key(mode_key)
            self.controller.on_mode_changed()

        self.view.select_mode_by_key = _select_mode_by_key
        self.controller.generate_prompt = MagicMock()

        self.controller.challenge_manager = MagicMock()
        self.controller.challenge_manager.get_challenge.return_value = challenge

        self.controller.load_challenge("c_desc_01")

        self.assertEqual(self.controller.active_challenge_id, "c_desc_01")
        self.assertEqual(self.controller.current_mode, "keywords")
        self.assertEqual(self.controller.current_exercise_data.get("challenge_id"), "c_desc_01")
        self.assertFalse(self.controller._loading_challenge)
        self.controller.generate_prompt.assert_called_once_with(is_challenge=True)

    def test_challenge_required_style_not_overridden(self):
        challenge = {
            "id": "c_style_01",
            "mode": "style",
            "rubric_mode": "style",
            "level": "级别2（动作/抽象）",
            "topic": "等待火车",
            "required_style": "海明威风格（极简主义、冰山理论）",
            "allow_random_style": False,
            "title": "固定风格",
            "description": "测试固定风格",
            "min_score": 20,
            "unlocked": True,
            "completed": False,
        }
        self.view.set_selected_mode_key("style")
        self.view.level_var.set(challenge["level"])
        self.view.topic_var.set(challenge["topic"])
        self.controller.active_challenge_id = "c_style_01"
        self.controller.challenge_prompt_text = "challenge"
        self.controller.challenge_manager = MagicMock()
        self.controller.challenge_manager.get_challenge.return_value = challenge
        self.controller.manager.get_random_style = MagicMock(return_value="随机风格")

        self.controller.generate_prompt(is_challenge=True)

        self.assertIn("海明威风格", self.view.last_prompt)
        self.assertNotIn("随机风格", self.view.last_prompt)
        self.controller.manager.get_random_style.assert_not_called()

    def test_ai_score_parse_failure_is_retryable_not_zero_score(self):
        self.config_manager.is_ai_enabled.return_value = True
        self.controller.active_challenge_id = "c_desc_01"
        self.controller.current_mode = "show_dont_tell"
        self.controller.current_exercise_data = {
            "mode": "show_dont_tell",
            "rubric_mode": "show_dont_tell",
            "level": "级别1（具象词汇）",
        }
        self.controller.challenge_manager = MagicMock()
        self.controller.history_manager.add_session = MagicMock()
        self.controller.gamification_manager = MagicMock()
        self.ai_client.extract_json_from_text.return_value = None

        self.controller._on_analysis_done("这是一段非 JSON 文本")

        self.assertIn("评分结果解析失败", self.view.feedback_text)
        self.controller.challenge_manager.complete_challenge.assert_not_called()
        self.controller.history_manager.add_session.assert_not_called()
        self.controller.gamification_manager.record_words.assert_not_called()


class TestChallengeMigration(unittest.TestCase):
    def test_challenge_file_migrates_to_defaults_while_preserving_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            existing = [
                {
                    "id": "c_desc_01",
                    "category": "Descriptive Mastery",
                    "title": "Stage 1: The Still Life",
                    "description": "Old text",
                    "mode": "show_dont_tell",
                    "topic": "An old coffee mug",
                    "level": "Level 1 (Concrete)",
                    "min_score": 21,
                    "next_challenge": "c_desc_02",
                    "unlocked": True,
                    "completed": True,
                },
                {
                    "id": "custom_01",
                    "category": "Custom",
                    "title": "Custom Challenge",
                    "description": "Keep me",
                    "mode": "keywords",
                    "topic": "Custom Topic",
                    "level": "Level 2",
                    "min_score": 10,
                    "next_challenge": None,
                    "unlocked": True,
                    "completed": False,
                },
            ]
            (data_dir / "training_challenges.json").write_text(
                json.dumps(existing, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            manager = ChallengeManager(data_dir)

            default_by_id = {c["id"]: c for c in DEFAULT_CHALLENGES}
            migrated = {c["id"]: c for c in manager.get_all_challenges()}

            # Defaults are present with localized labels.
            self.assertIn("c_desc_01", migrated)
            self.assertEqual(migrated["c_desc_01"]["level"], default_by_id["c_desc_01"]["level"])
            self.assertEqual(migrated["c_desc_01"]["category"], default_by_id["c_desc_01"]["category"])

            # Progress and tuned difficulty are preserved.
            self.assertTrue(migrated["c_desc_01"]["unlocked"])
            self.assertTrue(migrated["c_desc_01"]["completed"])
            self.assertEqual(migrated["c_desc_01"]["min_score"], 21)

            # Custom entries are retained.
            self.assertIn("custom_01", migrated)

    def test_dialogue_challenges_use_dialogue_rubrics(self):
        by_id = {c["id"]: c for c in DEFAULT_CHALLENGES}

        self.assertEqual(by_id["c_dial_02"]["mode"], "dialogue_subtext")
        self.assertEqual(by_id["c_dial_02"]["rubric_mode"], "dialogue_subtext")
        self.assertEqual(by_id["c_dial_01"]["mode"], "character_voice")


if __name__ == "__main__":
    unittest.main()
