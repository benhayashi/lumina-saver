import os
import json
import tempfile
import unittest
from pathlib import Path
from lumina_saver.config import ConfigManager, DEFAULT_CONFIG

class TestConfigManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = self.temp_dir.name

    def tearDown(self):
        if self.original_home is not None:
            os.environ["HOME"] = self.original_home
        self.temp_dir.cleanup()

    def test_default_config_created(self):
        cfg = ConfigManager()
        self.assertEqual(cfg.get("window_mode"), "fullscreen")
        self.assertEqual(cfg.get("image_duration"), 6.0)
        self.assertEqual(cfg.image_duration, 6.0)
        self.assertEqual(cfg.transition_type, "kenburns")
        self.assertEqual(cfg.overlay_mode, "full")
        self.assertTrue(len(cfg.media_directories) > 0)

    def test_save_and_reload(self):
        cfg = ConfigManager()
        cfg.set("image_duration", 12.5)
        cfg.set("window_mode", "windowed")
        cfg.set("media_directories", ["/custom/photos"])

        # Reload from disk
        cfg2 = ConfigManager()
        self.assertEqual(cfg2.get("image_duration"), 12.5)
        self.assertEqual(cfg2.get("window_mode"), "windowed")
        self.assertEqual(cfg2.media_directories, ["/custom/photos"])

    def test_corrupt_config_fallback(self):
        config_file = Path(self.temp_dir.name) / ".lumina_saver" / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            f.write("{invalid_json: true")

        cfg = ConfigManager()
        self.assertEqual(cfg.get("window_mode"), "fullscreen")

if __name__ == "__main__":
    unittest.main()
