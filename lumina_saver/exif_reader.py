import os
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ExifTags

class ExifReader:
    """Extracts EXIF metadata from modern photo formats (JPEG, HEIC, JXL, AVIF, RAW)."""

    @staticmethod
    def extract_metadata(file_path: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "file_name": os.path.basename(file_path),
            "folder_name": os.path.basename(os.path.dirname(file_path)),
            "full_path": file_path,
            "date_taken": None,
            "camera": None,
            "exposure": None,
            "dimensions": None,
        }

        try:
            # Register HEIF / AVIF plugins if available
            try:
                from pillow_heif import register_heif_opener
                register_heif_opener()
            except ImportError:
                pass

            with Image.open(file_path) as img:
                info["dimensions"] = f"{img.width} × {img.height}"
                exif_data = img.getexif()

                if exif_data:
                    raw_tags = {}
                    for tag_id, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        raw_tags[tag_name] = value

                    # Extract Camera Make & Model
                    make = str(raw_tags.get("Make", "")).strip()
                    model = str(raw_tags.get("Model", "")).strip()
                    if model:
                        info["camera"] = f"{make} {model}".replace(make, make).strip()
                    elif make:
                        info["camera"] = make

                    # Extract Date Taken
                    date_str = raw_tags.get("DateTimeOriginal") or raw_tags.get("DateTime")
                    if date_str and isinstance(date_str, str):
                        try:
                            # Format "YYYY:MM:DD HH:MM:SS" -> "YYYY-MM-DD HH:MM"
                            parts = date_str.split(" ")
                            if len(parts) >= 2:
                                ymd = parts[0].replace(":", "-")
                                hm = ":".join(parts[1].split(":")[:2])
                                info["date_taken"] = f"{ymd} {hm}"
                        except Exception:
                            info["date_taken"] = str(date_str)

                    # Extract Exposure settings (ISO, FNumber, ExposureTime)
                    iso = raw_tags.get("ISOSpeedRatings") or raw_tags.get("ISO")
                    fnumber = raw_tags.get("FNumber")
                    shutter = raw_tags.get("ExposureTime")

                    exp_parts = []
                    if shutter:
                        exp_parts.append(f"1/{int(1.0 / shutter)}s" if shutter < 1 else f"{shutter}s")
                    if fnumber:
                        exp_parts.append(f"f/{float(fnumber):.1f}")
                    if iso:
                        exp_parts.append(f"ISO {iso}")

                    if exp_parts:
                        info["exposure"] = " | ".join(exp_parts)

        except Exception:
            # Fallback if image opening fails (e.g. video files or proprietary raw)
            pass

        # Fallback for Date Taken if EXIF missing
        if not info["date_taken"]:
            try:
                mtime = os.path.getmtime(file_path)
                import datetime
                info["date_taken"] = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        return info
