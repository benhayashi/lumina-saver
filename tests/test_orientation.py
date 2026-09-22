import os
import tempfile
import unittest
from PIL import Image
import piexif

from lumina_saver.exif_reader import ExifReader
from lumina_saver.indexer import MediaIndexer

class TestOrientationFiltering(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.media_dir = os.path.join(self.temp_dir.name, "Photos")
        os.makedirs(self.media_dir, exist_ok=True)
        self.db_path = os.path.join(self.temp_dir.name, "test.db")

        # 1. Plain Landscape: 800x600
        self.landscape_path = os.path.join(self.media_dir, "plain_landscape.jpg")
        img_l = Image.new("RGB", (800, 600), color="blue")
        img_l.save(self.landscape_path)

        # 2. Plain Portrait: 600x800
        self.portrait_path = os.path.join(self.media_dir, "plain_portrait.jpg")
        img_p = Image.new("RGB", (600, 800), color="red")
        img_p.save(self.portrait_path)

        # 3. Raw Landscape (800x600) with EXIF orientation 6 (Rotate 90 CW) -> Rendered Portrait (600x800)
        self.exif_portrait_path = os.path.join(self.media_dir, "exif_portrait.jpg")
        img_ep = Image.new("RGB", (800, 600), color="green")
        exif_dict = {"0th": {piexif.ImageIFD.Orientation: 6}}
        exif_bytes = piexif.dump(exif_dict)
        img_ep.save(self.exif_portrait_path, exif=exif_bytes)

        # 4. Raw Portrait (600x800) with EXIF orientation 6 (Rotate 90 CW) -> Rendered Landscape (800x600)
        self.exif_landscape_path = os.path.join(self.media_dir, "exif_landscape.jpg")
        img_el = Image.new("RGB", (600, 800), color="yellow")
        exif_dict_el = {"0th": {piexif.ImageIFD.Orientation: 6}}
        exif_bytes_el = piexif.dump(exif_dict_el)
        img_el.save(self.exif_landscape_path, exif=exif_bytes_el)

        self.indexer = MediaIndexer(
            db_path=self.db_path,
            media_dirs=[self.media_dir],
            image_exts=[".jpg"],
            video_exts=[".mp4"]
        )

    def tearDown(self):
        self.indexer.close()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_exif_reader_dimensions(self):
        # Plain landscape
        w, h = ExifReader.get_image_dimensions(self.landscape_path)
        self.assertEqual((w, h), (800, 600))

        # Plain portrait
        w, h = ExifReader.get_image_dimensions(self.portrait_path)
        self.assertEqual((w, h), (600, 800))

        # EXIF rotated to portrait
        w, h = ExifReader.get_image_dimensions(self.exif_portrait_path)
        self.assertEqual((w, h), (600, 800))

        # EXIF rotated to landscape
        w, h = ExifReader.get_image_dimensions(self.exif_landscape_path)
        self.assertEqual((w, h), (800, 600))

    def test_landscape_only_filtering(self):
        # Scan files without inspecting dimensions upfront (fast scan, width=0)
        self.indexer.scan_directories()

        # Query next media 20 times in landscape mode
        # Must NEVER return plain_portrait.jpg or exif_portrait.jpg
        for _ in range(20):
            media = self.indexer.get_next_media(orientation="landscape")
            self.assertIsNotNone(media)
            fname = media["file_name"]
            self.assertIn(fname, ["plain_landscape.jpg", "exif_landscape.jpg"],
                          f"Portrait photo '{fname}' was unexpectedly returned in landscape-only mode!")

    def test_portrait_only_filtering(self):
        self.indexer.scan_directories()

        # Query next media 20 times in portrait mode
        # Must NEVER return plain_landscape.jpg or exif_landscape.jpg
        for _ in range(20):
            media = self.indexer.get_next_media(orientation="portrait")
            self.assertIsNotNone(media)
            fname = media["file_name"]
            self.assertIn(fname, ["plain_portrait.jpg", "exif_portrait.jpg"],
                          f"Landscape photo '{fname}' was unexpectedly returned in portrait-only mode!")

    def test_populate_unindexed_dimensions(self):
        self.indexer.scan_directories()
        
        # Verify initially width is 0
        with self.indexer.get_connection() as conn:
            rows = conn.execute("SELECT file_name, width, height FROM media_files").fetchall()
            for r in rows:
                self.assertEqual(r["width"], 0)

        # Run background population
        count = self.indexer.populate_unindexed_dimensions(batch_size=10)
        self.assertEqual(count, 4)

        # Verify dimensions in SQLite are now accurate and EXIF-aware
        with self.indexer.get_connection() as conn:
            data = {r["file_name"]: (r["width"], r["height"]) for r in conn.execute("SELECT file_name, width, height FROM media_files").fetchall()}
            self.assertEqual(data["plain_landscape.jpg"], (800, 600))
            self.assertEqual(data["plain_portrait.jpg"], (600, 800))
            self.assertEqual(data["exif_portrait.jpg"], (600, 800))
            self.assertEqual(data["exif_landscape.jpg"], (800, 600))

if __name__ == "__main__":
    unittest.main()
