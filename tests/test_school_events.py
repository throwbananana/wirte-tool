import unittest
from unittest.mock import MagicMock
from writer_app.ui.floating_assistant.school_events import SchoolEventManager, SchoolEvent, SchoolEventChoice
from writer_app.ui.floating_assistant.pet_system import PetSystem, PetData

class TestSchoolEvents(unittest.TestCase):

    def setUp(self):
        # Mock PetSystem
        self.mock_pet_system = MagicMock(spec=PetSystem)
        self.mock_pet_system.data = PetData()
        self.mock_pet_system.data.affection = 0
        self.mock_pet_system.unlock_achievement.return_value = False # Default: achievement not newly unlocked

        self.manager = SchoolEventManager(self.mock_pet_system)

    def test_init_events(self):
        """Test that events are initialized correctly."""
        self.assertTrue(len(self.manager.events) > 0)
        # Check for specific new events
        event_ids = [e.id for e in self.manager.events]
        self.assertIn("library_encounter", event_ids)
        self.assertIn("lit_club_anthology", event_ids)
        self.assertIn("strict_librarian", event_ids)

    def test_get_random_event_low_affection(self):
        """Test getting an event with low affection."""
        self.mock_pet_system.data.affection = 0
        event = self.manager.get_random_event()
        self.assertIsNotNone(event)
        # Events with min_affection > 0 should not be selected
        # e.g. rooftop_lunch needs 20
        # This is probabilistic, but we can check if the returned event is valid
        self.assertLessEqual(event.min_affection, 0)

    def test_get_random_event_high_affection(self):
        """Test getting an event with high affection."""
        self.mock_pet_system.data.affection = 100
        # Should be able to get any event, including those with min_affection
        # We can't guarantee a specific one, but it shouldn't crash
        event = self.manager.get_random_event()
        self.assertIsNotNone(event)

    def test_process_choice_success(self):
        """Test processing a valid choice."""
        # Manually set an active event for testing
        event = self.manager.events[0]
        self.manager.active_event = event
        
        choice_index = 0
        choice = event.choices[choice_index]
        
        result = self.manager.process_choice(choice_index)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], choice.outcome_text)
        self.mock_pet_system.add_affection.assert_called_with(choice.affection_change)
        self.mock_pet_system.update_mood.assert_called_with(choice.mood_change)

    def test_process_choice_insufficient_affection(self):
        """Test processing a choice with insufficient affection."""
        # Find an event with a high requirement choice
        # rainy_day_drama choice 0 needs 50
        event = next(e for e in self.manager.events if e.id == "rainy_day_drama")
        self.manager.active_event = event
        self.mock_pet_system.data.affection = 0 

        # Find the index of the high requirement choice
        choice_index = next(i for i, c in enumerate(event.choices) if c.required_affection > 0)
        
        result = self.manager.process_choice(choice_index)
        
        self.assertFalse(result["success"])
        self.assertIn("好感度不足", result["message"])
        self.mock_pet_system.add_affection.assert_not_called()

    def test_process_choice_achievement(self):
        """Test choice that unlocks achievement."""
        # rooftop_lunch choice 0 unlocks "shared_lunch"
        event = next(e for e in self.manager.events if e.id == "rooftop_lunch")
        self.manager.active_event = event
        
        # Mock unlock success
        self.mock_pet_system.unlock_achievement.return_value = True

        result = self.manager.process_choice(0)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["achievement"], "shared_lunch")
        self.mock_pet_system.unlock_achievement.assert_called_with("shared_lunch")

if __name__ == '__main__':
    unittest.main()
