import os
import sys
import tempfile
import unittest
from PIL import Image

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap
from lumina_saver.media_loader import MediaLoader

class TestMediaLoader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.img_path = os.path.join(self.temp_dir.name, "test_image.png")
        img = Image.new("RGB", (640, 480), color="red")
        img.save(self.img_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_valid_image(self):
        pixmap = MediaLoader.load_image_pixmap(self.img_path)
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.width(), 640)
        self.assertEqual(pixmap.height(), 480)

    def test_load_nonexistent_file(self):
        pixmap = MediaLoader.load_image_pixmap(os.path.join(self.temp_dir.name, "nonexistent.png"))
        self.assertIsNone(pixmap)

    def test_load_corrupt_file(self):
        corrupt_path = os.path.join(self.temp_dir.name, "corrupt.png")
        with open(corrupt_path, "w") as f:
            f.write("not an image")
        pixmap = MediaLoader.load_image_pixmap(corrupt_path)
        self.assertIsNone(pixmap)

if __name__ == "__main__":
    unittest.main()
