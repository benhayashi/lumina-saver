import os
import sys
import unittest
from lumina_saver.sleep_inhibitor import SleepInhibitor
from lumina_saver.config import ConfigManager

class TestSleepInhibitor(unittest.TestCase):

    def setUp(self):
        self.inhibitor = SleepInhibitor(app_name="LuminaSaverTest", reason="Running unit tests")

    def tearDown(self):
        self.inhibitor.release()

    def test_default_state(self):
        self.assertFalse(self.inhibitor.is_inhibited)
        self.assertEqual(self.inhibitor.app_name, "LuminaSaverTest")
        self.assertEqual(len(self.inhibitor._child_processes), 0)

    def test_inhibit_and_release_lifecycle(self):
        success = self.inhibitor.inhibit()
        # On Linux/Windows/macOS with standard tools, inhibit should succeed
        if sys.platform.startswith("linux") or sys.platform.startswith("win") or sys.platform == "darwin":
            self.assertTrue(success)
            self.assertTrue(self.inhibitor.is_inhibited)

        # Calling inhibit again should be idempotent
        self.assertTrue(self.inhibitor.inhibit())

        # Release should terminate processes and reset is_inhibited
        self.inhibitor.release()
        self.assertFalse(self.inhibitor.is_inhibited)
        self.assertEqual(len(self.inhibitor._child_processes), 0)

        # Calling release again should be idempotent
        self.inhibitor.release()
        self.assertFalse(self.inhibitor.is_inhibited)

    def test_heartbeat_ping(self):
        # Should not raise exception even if not inhibited
        self.inhibitor.heartbeat_ping()
        self.inhibitor.inhibit()
        self.inhibitor.heartbeat_ping()
        self.inhibitor.release()

    def test_config_default_prevent_sleep(self):
        config = ConfigManager()
        self.assertIn("prevent_display_sleep", config.data)
        self.assertTrue(config.get("prevent_display_sleep", False))

if __name__ == "__main__":
    unittest.main()
