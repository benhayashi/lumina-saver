import json
import os
from pathlib import Path
from typing import List, Dict, Any

DEFAULT_CONFIG = {
    "media_directories": [
        "C:\\lumina" if os.name == "nt" else str(Path.home() / "lumina")
    ],
    "window_mode": "fullscreen",          # options: "fullscreen", "windowed"
    "multi_monitor_mode": "dual_independent", # options: "dual_independent", "primary_only", "span"
    "interlocked_multi_monitor": True,    # Interlocked arrow keys across multi-monitors
    "auto_reindex_minutes": 15,          # Background auto re-indexing interval in minutes (0 to disable)
    "show_progress_bar": True,
    "image_duration": 6.0,
    "transition_duration": 1.0,
    "transition_type": "kenburns",       # options: "crossfade", "kenburns", "fade", "none"
    "overlay_mode": "full",              # options: "full", "minimal", "off"
    "display_order": "random",           # options: "random", "sequential"
    "last_sequential_id": 0,             # Last played ID for sequential resume
    "min_resolution": "none",            # options: "none", "720p", "1080p", "4k"
    "orientation_filter": "all",         # options: "all", "landscape", "portrait"
    "mute_videos": False,
    "video_duration_mode": "full",       # options: "full", "photo_duration", "custom"
    "max_video_duration_seconds": 180.0,
    "include_subfolders": True,
    "image_extensions": [
        ".jpg", ".jpeg", ".jxl", ".heic", ".heif", ".avif", 
        ".png", ".webp", ".bmp", ".tiff", ".tif", ".cr2", ".nef", ".arw"
    ],
    "video_extensions": [
        ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm", ".m4v", ".flv"
    ],
    "enable_hardware_acceleration": True,
    "cache_db_path": str(Path.home() / ".lumina_saver" / "media_index.db")
}

class ConfigManager:
    """Manages application settings persisted in user appdata JSON."""

    def __init__(self, config_filename: str = "config.json"):
        self.config_dir = Path.home() / ".lumina_saver"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / config_filename
        self.data: Dict[str, Any] = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                    config = DEFAULT_CONFIG.copy()
                    config.update(user_data)
                    return config
            except Exception as e:
                print(f"[Config] Error reading {self.config_file}: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()

    def save_config(self) -> bool:
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            return True
        except Exception as e:
            print(f"[Config] Failed to save config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        self.data[key] = value
        self.save_config()

    @property
    def media_directories(self) -> List[str]:
        return self.data.get("media_directories", [])

    @property
    def image_duration(self) -> float:
        return float(self.data.get("image_duration", 6.0))

    @property
    def transition_type(self) -> str:
        return str(self.data.get("transition_type", "kenburns"))

    @property
    def overlay_mode(self) -> str:
        return str(self.data.get("overlay_mode", "full"))
