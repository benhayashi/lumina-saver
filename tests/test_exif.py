import os
import tempfile
import unittest
from PIL import Image
from lumina_saver.exif_reader import ExifReader

class TestExifReader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_img_path = os.path.join(self.temp_dir.name, "sample.jpg")
        
        # Create sample image
        img = Image.new("RGB", (800, 600), color="blue")
        img.save(self.test_img_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_metadata(self):
        meta = ExifReader.extract_metadata(self.test_img_path)
        self.assertEqual(meta["file_name"], "sample.jpg")
        self.assertEqual(meta["dimensions"], "800 × 600")
        self.assertIsNotNone(meta["date_taken"])

if __name__ == "__main__":
    unittest.main()
