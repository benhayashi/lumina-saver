import os
import tempfile
import unittest
from lumina_saver.indexer import MediaIndexer

class TestMediaIndexer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_file = os.path.join(self.temp_dir.name, "test_media.db")
        
        # Create mock media files
        self.photos_dir = os.path.join(self.temp_dir.name, "Photos")
        os.makedirs(self.photos_dir, exist_ok=True)

        for i in range(10):
            with open(os.path.join(self.photos_dir, f"photo_{i}.jpg"), "w") as f:
                f.write("mock content")

        for i in range(3):
            with open(os.path.join(self.photos_dir, f"video_{i}.mp4"), "w") as f:
                f.write("mock video content")

        self.indexer = MediaIndexer(
            db_path=self.db_file,
            media_dirs=[self.photos_dir],
            image_exts=[".jpg"],
            video_exts=[".mp4"]
        )

    def tearDown(self):
        self.indexer.close()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_scan_and_index(self):
        total = self.indexer.scan_directories()
        self.assertEqual(total, 13)

    def test_next_and_previous_navigation(self):
        self.indexer.scan_directories()
        
        first = self.indexer.get_next_media()
        self.assertIsNotNone(first)
        
        second = self.indexer.get_next_media()
        self.assertIsNotNone(second)

        prev = self.indexer.get_previous_media()
        self.assertEqual(prev["file_path"], first["file_path"])

if __name__ == "__main__":
    unittest.main()
