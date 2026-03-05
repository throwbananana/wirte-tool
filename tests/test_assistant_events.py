import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from writer_app.ui.floating_assistant.event_system import AssistantEventSystem, AssistantState
from writer_app.ui.floating_assistant.pet_system import PetSystem, PetData

class TestAssistantEventSystem(unittest.TestCase):

    def setUp(self):
        self.mock_assistant = MagicMock()
        self.mock_pet_system = MagicMock(spec=PetSystem)
        self.mock_pet_system.data = PetData()
        self.mock_project_manager = MagicMock()
        
        # Default behavior for project type
        self.mock_project_manager.get_project_type.return_value = "General"
        
        self.event_system = AssistantEventSystem(
            self.mock_assistant,
            self.mock_pet_system,
            self.mock_project_manager
        )

    def test_record_module_usage_milestone(self):
        """测试模块使用记录及里程碑触发"""
        # 初始计数为 0
        self.assertEqual(len(self.event_system._module_usage), 0)
        
        # 模拟使用 4 个不同模块以触发第一个里程碑 (threshold: 4)
        modules = ["outline", "script", "characters", "wiki"]
        for mod in modules:
            self.event_system.record_module_usage(mod)
            
        self.assertEqual(len(self.event_system._module_usage), 4)
        
        # 检查是否触发了里程碑通知
        # MODULE_MILESTONES[0] id is "module_newbie"
        self.assertIn("module_newbie", self.event_system._unlocked_events)
        self.mock_assistant.notification_manager.notify.assert_called()

    def test_record_project_type_milestone(self):
        """测试项目类型记录及里程碑触发"""
        # 模拟创作 2 种不同项目类型以触发第一个里程碑 (threshold: 2)
        self.event_system._record_project_type("General")
        self.event_system._record_project_type("Suspense")
        
        self.assertEqual(len(self.event_system._created_types), 2)
        self.assertIn("type_explorer", self.event_system._unlocked_events)

    def test_record_themes(self):
        """测试主题标签记录"""
        # 模拟项目管理器返回标签
        self.mock_project_manager.get_scenes.return_value = [{"tags": ["Action", "Suspense"]}]
        self.mock_project_manager.get_outline.return_value = None
        self.mock_project_manager.get_ideas.return_value = []
        self.mock_project_manager.get_research_items.return_value = []
        
        self.event_system._record_themes()
        
        self.assertIn("Action", self.event_system._created_themes)
        self.assertIn("Suspense", self.event_system._created_themes)

    def test_check_time_events(self):
        """测试时间事件触发"""
        # 模拟时间检测器返回早晨
        self.mock_assistant.time_detector.get_time_state.return_value = AssistantState.MORNING
        
        self.event_system.check_time_events()
        
        # 应该触发 time_early_bird (early_bird 成就)
        self.assertIn("time_early_bird", self.event_system._unlocked_events)

    def test_handle_achievement_unlocked(self):
        """测试成就解锁后的相册奖励"""
        # 模拟解锁 early_bird 成就
        achievement_id = "early_bird"
        
        # 模拟项目类型
        self.mock_project_manager.get_project_type.return_value = "General"
        
        self.event_system.handle_achievement_unlocked(achievement_id)
        
        # 应该调用 _add_event_photo
        self.mock_assistant._add_event_photo.assert_called()
        # 检查参数 (General -> AssistantState.MORNING for early_bird in ACHIEVEMENT_PHOTO_REWARDS)
        args, kwargs = self.mock_assistant._add_event_photo.call_args
        self.assertEqual(args[0], AssistantState.MORNING)

    def test_handle_project_event_dispatch(self):
        """测试项目事件分发"""
        with patch.object(self.event_system, 'record_module_usage') as mock_record:
            self.event_system.handle_project_event("scene_added")
            mock_record.assert_called_with("script")
            
        with patch.object(self.event_system, 'record_creation_activity') as mock_creation:
            self.event_system.handle_project_event("scene_added")
            mock_creation.assert_called_with("scene_added")

if __name__ == '__main__':
    unittest.main()
