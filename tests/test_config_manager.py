import unittest
import json
import os
import shutil
from pathlib import Path
from writer_app.core.config import ConfigManager

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        # Use a temporary directory for testing
        self.test_dir = Path("tests/temp_config")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Patch the config dir path in the class instance for testing
        # Since ConfigManager determines path in __init__, we might need to subclass or patch
        
        # Subclassing for testability to override the config path
        class TestableConfigManager(ConfigManager):
            def __init__(self, test_path):
                self.config_dir = test_path
                self.config_file = self.config_dir / "config.json"
                self.config_data = self._load_default_config()
                self._ensure_config_dir()
                self.load()

        self.ConfigManagerClass = TestableConfigManager

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_default_config(self):
        config = self.ConfigManagerClass(self.test_dir)
        self.assertEqual(config.get("lm_api_model"), "local-model")
        self.assertEqual(config.get("window_geometry"), "1400x900")

    def test_save_and_load(self):
        config = self.ConfigManagerClass(self.test_dir)
        config.set("lm_api_model", "test-model-v1")
        config.set("lm_api_key", "secret-key")
        config.save()

        # Create a new instance to verify loading
        new_config = self.ConfigManagerClass(self.test_dir)
        self.assertEqual(new_config.get("lm_api_model"), "test-model-v1")
        self.assertEqual(new_config.get("lm_api_key"), "secret-key")
        self.assertEqual(new_config.get("window_geometry"), "1400x900") # Default preserved

    def test_partial_update(self):
        # Create a file with only one setting
        with open(self.test_dir / "config.json", "w") as f:
            json.dump({"lm_api_url": "http://custom-url"}, f)
        
        config = self.ConfigManagerClass(self.test_dir)
        self.assertEqual(config.get("lm_api_url"), "http://custom-url")
        self.assertEqual(config.get("lm_api_model"), "local-model") # Should still have default

if __name__ == '__main__':
    unittest.main()
