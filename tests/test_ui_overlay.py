import os
import sys
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from lumina_saver.ui_overlay import UIOverlay

class TestUIOverlay(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.overlay = UIOverlay()

    def test_initial_state(self):
        self.assertEqual(self.overlay.overlay_mode, "full")
        self.assertFalse(self.overlay.is_paused)

    def test_cycle_overlay_mode(self):
        self.assertEqual(self.overlay.cycle_overlay_mode(), "minimal")
        self.assertEqual(self.overlay.cycle_overlay_mode(), "off")
        self.assertEqual(self.overlay.cycle_overlay_mode(), "full")

    def test_update_metadata(self):
        meta = {
            "folder_name": "Vacation2026",
            "file_name": "sunset.jpg",
            "date_taken": "2026-07-04 19:30",
            "camera": "Sony A7 IV",
            "exposure": "1/250s | f/2.8 | ISO 100",
            "dimensions": "7000 × 4667",
        }
        self.overlay.update_metadata(meta, current_index=5, total_count=100)
        self.assertIn("Vacation2026", self.overlay.lbl_folder.text())
        self.assertEqual(self.overlay.lbl_filename.text(), "sunset.jpg")
        self.assertIn("5 / 100", self.overlay.lbl_counter.text())
        self.assertIn("2026-07-04", self.overlay.lbl_date.text())

    def test_pause_toggle(self):
        self.overlay.set_paused(True)
        self.assertTrue(self.overlay.is_paused)
        self.assertFalse(self.overlay.paused_card.isHidden())

        self.overlay.set_paused(False)
        self.assertFalse(self.overlay.is_paused)
        self.assertTrue(self.overlay.paused_card.isHidden())

    def test_show_temporary_message(self):
        self.overlay.show_temporary_message("Focused: Screen 2")
        self.assertEqual(self.overlay.lbl_toast.text(), "Focused: Screen 2")
        self.assertFalse(self.overlay.toast_card.isHidden())

if __name__ == "__main__":
    unittest.main()
