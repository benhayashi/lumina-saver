import os
import warnings
from typing import Optional, Tuple
from PIL import Image, ImageOps
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QByteArray

Image.MAX_IMAGE_PIXELS = None
warnings.simplefilter("ignore", Image.DecompressionBombWarning)

class MediaLoader:
    """Decodes modern image formats (HEIC, JXL, AVIF, WebP, 10-bit) into full-resolution Qt Pixmaps."""

    @staticmethod
    def load_image_pixmap(file_path: str) -> Optional[QPixmap]:
        """Loads an image file at full resolution, handles EXIF orientation, and returns a high-quality QPixmap."""
        try:
            # Register HEIF/AVIF plugins
            try:
                from pillow_heif import register_heif_opener
                register_heif_opener()
            except ImportError:
                pass

            with Image.open(file_path) as img:
                # Force loading full image data (prevents reading embedded EXIF thumbnail streams)
                img.load()

                # Auto-rotate based on EXIF orientation tag
                img = ImageOps.exif_transpose(img)

                # Convert to RGBA
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                data = img.tobytes("raw", "RGBA")
                qimage = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
                pixmap = QPixmap.fromImage(qimage)
                if not pixmap.isNull():
                    return pixmap

                # Fallback for ultra-large panoramas exceeding GPU texture limits:
                # Downsample to 8192 max dimension
                max_dim = 8192
                if img.width > max_dim or img.height > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                    data = img.tobytes("raw", "RGBA")
                    qimage = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
                    pixmap = QPixmap.fromImage(qimage)
                    if not pixmap.isNull():
                        return pixmap

        except Exception as e:
            print(f"[MediaLoader] Failed to load image {file_path}: {e}")
            # Fallback attempt using Qt's native image reader
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                return pixmap

        return None
