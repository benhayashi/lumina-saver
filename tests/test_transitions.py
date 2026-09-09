import unittest
from PySide6.QtCore import QPoint, QRect
from lumina_saver.transitions import TransitionManager

class TestTransitions(unittest.TestCase):

    def test_calculate_kenburns_transform(self):
        pixmap_size = QPoint(1920, 1080)
        container_size = QPoint(1280, 720)
        rect_start, rect_end = TransitionManager.calculate_kenburns_transform(pixmap_size, container_size, 0.5)

        self.assertIsInstance(rect_start, QRect)
        self.assertIsInstance(rect_end, QRect)
        self.assertGreater(rect_start.width(), 0)
        self.assertGreater(rect_start.height(), 0)
        self.assertGreater(rect_end.width(), 0)
        self.assertGreater(rect_end.height(), 0)

    def test_zero_dimensions_graceful_handling(self):
        pixmap_size = QPoint(0, 0)
        container_size = QPoint(100, 100)
        rect_start, rect_end = TransitionManager.calculate_kenburns_transform(pixmap_size, container_size, 0.0)
        self.assertEqual(rect_start.width(), 100)
        self.assertEqual(rect_start.height(), 100)

if __name__ == "__main__":
    unittest.main()
