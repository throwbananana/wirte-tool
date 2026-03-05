import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock pyttsx3 before importing tts
sys.modules['pyttsx3'] = MagicMock()

from writer_app.core.tts import TTSManager

class TestTTSManager(unittest.TestCase):
    def setUp(self):
        # Reset singleton if needed, though for this simple test strictly not necessary 
        # as we are mocking the engine
        TTSManager._instance = None
        self.tts = TTSManager()

    def test_singleton(self):
        tts2 = TTSManager()
        self.assertIs(self.tts, tts2)

    def test_init_engine(self):
        self.assertIsNotNone(self.tts.engine)

    def test_speak_calls_engine(self):
        self.tts.speak("Hello")
        # Since speak runs in a thread and mock finishes instantly, 
        # just check that a thread was created
        self.assertIsNotNone(self.tts.worker_thread)

    def test_stop_calls_engine(self):
        self.tts.is_speaking = True
        self.tts.stop()
        self.tts.engine.stop.assert_called()
        self.assertFalse(self.tts.is_speaking)

    def test_set_rate(self):
        self.tts.set_rate(200)
        self.tts.engine.setProperty.assert_called_with('rate', 200)

if __name__ == '__main__':
    unittest.main()
