import os
import sys
import subprocess
import time
from typing import Dict, Any, Optional
from PySide6.QtWidgets import QMainWindow, QWidget, QLabel, QStackedLayout, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPoint, QEvent, QUrl
from PySide6.QtGui import QPixmap, QKeySequence, QColor, QPalette
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from lumina_saver.config import ConfigManager
from lumina_saver.indexer import MediaIndexer
from lumina_saver.media_loader import MediaLoader
from lumina_saver.exif_reader import ExifReader
from lumina_saver.ui_overlay import UIOverlay
from lumina_saver.transitions import TransitionManager

from lumina_saver.ff_player import PyAVVideoPlayer

class PlayerWindow(QMainWindow):
    """Main media display window for photo & video slideshow with multi-monitor & windowed support."""

    def __init__(self, config: ConfigManager, indexer: MediaIndexer, is_screensaver: bool = False, target_screen=None, sleep_inhibitor=None):
        super().__init__()
        self.config = config
        self.indexer = indexer
        self.is_screensaver = is_screensaver
        self.target_screen = target_screen
        self.sleep_inhibitor = sleep_inhibitor

        self.current_media: Optional[Dict[str, Any]] = None
        self.is_paused = False
        self.mouse_pos: Optional[QPoint] = None
        self.mpv_player = None
        self.qt_player = None
        self.audio_output = None
        self.qvideo_widget = None
        self.multi_controller = None

        self._init_window()
        self._init_video_player()
        self._init_timers()

    def _init_window(self):
        self.setWindowTitle("LuminaSaver Slideshow")
        self.setStyleSheet("background-color: #000000;")

        if self.target_screen:
            self.setScreen(self.target_screen)

        # Central widget with stacked layout for smooth image transitions
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout = QStackedLayout(self.central_widget)
        self.layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        # Layer 0 & Layer 1 Image Labels for Crossfading & FFmpeg frame display
        self.img_label1 = QLabel(self)
        self.img_label1.setAlignment(Qt.AlignCenter)
        self.img_label1.setStyleSheet("background-color: black;")

        self.img_label2 = QLabel(self)
        self.img_label2.setAlignment(Qt.AlignCenter)
        self.img_label2.setStyleSheet("background-color: black;")
        self.img_label2.hide()

        self.layout.addWidget(self.img_label1)
        self.layout.addWidget(self.img_label2)
        self.active_label_idx = 0

        # Dedicated QVideoWidget for QtMultimedia (direct member of stacked layout)
        self.qvideo_widget = QVideoWidget(self)
        self.qvideo_widget.setStyleSheet("background-color: black;")
        self.qvideo_widget.hide()
        self.layout.addWidget(self.qvideo_widget)

        # HUD Overlay Widget
        self.overlay = UIOverlay(self)
        self.overlay.raise_()
        self.overlay.apply_overlay_mode(show_progress_bar=self.config.get("show_progress_bar", True))

        win_mode = self.config.get("window_mode", "fullscreen")
        if self.is_screensaver or win_mode == "fullscreen":
            self.setCursor(Qt.BlankCursor)
            if self.target_screen:
                geo = self.target_screen.geometry()
                self.setGeometry(geo)
                self.showFullScreen()
            else:
                self.showFullScreen()
        else:  # Windowed mode
            self.setCursor(Qt.ArrowCursor)
            self.resize(1280, 720)
            if self.target_screen:
                geo = self.target_screen.geometry()
                self.move(geo.x() + 50, geo.y() + 50)
            self.show()

    def _init_video_player(self):
        """Initializes MPV engine, QtMultimedia QMediaPlayer, or PyAV FFmpeg fallback."""
        import ctypes
        import ctypes.util

        # Initialize PyAV FFmpeg software decoder (Guaranteed fallback)
        self.ff_player = PyAVVideoPlayer(target_label=self.img_label1, parent=self)
        self.ff_player.finished.connect(self.next_media)

        has_libmpv_dll = False
        try:
            if sys.platform == "win32":
                ctypes.cdll.LoadLibrary("mpv-1.dll")
                has_libmpv_dll = True
            else:
                lib = ctypes.util.find_library("mpv")
                has_libmpv_dll = (lib is not None)
        except Exception:
            has_libmpv_dll = False

        if has_libmpv_dll:
            try:
                import mpv
                wid = int(self.qvideo_widget.winId())
                self.mpv_player = mpv.MPV(
                    wid=str(wid),
                    vo="gpu",
                    hwdec="auto",
                    keep_open="yes",
                    idle="yes"
                )
                print("[Player] libmpv engine active with hardware decoding.")
                return
            except Exception as e:
                print(f"[Player] mpv init failed despite DLL: {e}")

        # QtMultimedia QMediaPlayer engine
        try:
            self.audio_output = QAudioOutput(self)
            self.qt_player = QMediaPlayer(self)
            self.qt_player.setVideoOutput(self.qvideo_widget)
            self.qt_player.setAudioOutput(self.audio_output)
            self.qt_player.mediaStatusChanged.connect(self._on_qt_media_status_changed)
            self.qt_player.durationChanged.connect(self._on_qt_duration_changed)
            self.qt_player.errorOccurred.connect(self._on_qt_media_error)
            print("[Player] QtMultimedia QMediaPlayer engine active (H.264 & HEVC ready).")
        except Exception as e:
            print(f"[Player] QtMultimedia video engine error: {e}")

    def _init_timers(self):
        # Timer for slide advance
        self.slide_timer = QTimer(self)
        self.slide_timer.timeout.connect(self.next_media)

        # Timer for progress bar UI update
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(50)
        self.progress_timer.timeout.connect(self._update_progress_bar)

        self.slide_start_time = time.time()
        self.current_duration = self.config.image_duration

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "overlay") and self.overlay:
            self.overlay.setGeometry(self.rect())
        
        # Dynamically rescale active photo if window geometry changes
        if hasattr(self, "current_raw_pixmap") and self.current_raw_pixmap and not self.current_raw_pixmap.isNull():
            active_label = self.img_label2 if self.active_label_idx == 1 else self.img_label1
            size = self.central_widget.size()
            if size.width() > 0 and size.height() > 0:
                scaled_pixmap = self.current_raw_pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                active_label.setPixmap(scaled_pixmap)

    def start(self):
        """Start media slideshow loop asynchronously after window geometry is fully settled."""
        QTimer.singleShot(100, self.next_media)

    def next_media(self):
        min_res = self.config.get("min_resolution", "none")
        orient = self.config.get("orientation_filter", "all")
        order = self.config.get("display_order", "random")
        last_id = self.config.get("last_sequential_id", 0)

        media = self.indexer.get_next_media(
            min_res=min_res,
            orientation=orient,
            display_order=order,
            last_id=last_id
        )
        if media:
            if order == "sequential" and "id" in media:
                self.config.set("last_sequential_id", media["id"])
            self.display_media(media)

    def previous_media(self):
        media = self.indexer.get_previous_media()
        if media:
            self.display_media(media)

    def skip_folder(self):
        current_folder = self.current_media.get("folder_path") if self.current_media else None
        min_res = self.config.get("min_resolution", "none")
        orient = self.config.get("orientation_filter", "all")
        order = self.config.get("display_order", "random")
        last_id = self.config.get("last_sequential_id", 0)

        media = self.indexer.get_next_media(
            min_res=min_res,
            orientation=orient,
            display_order=order,
            last_id=last_id,
            skip_folder=current_folder
        )
        if media:
            self.display_media(media)

    def display_media(self, media: Dict[str, Any]):
        self.current_media = media
        file_path = media["file_path"]
        media_type = media["media_type"]

        if self.sleep_inhibitor:
            self.sleep_inhibitor.heartbeat_ping()

        if media_type == "image":
            self._display_image(file_path)
        elif media_type == "video":
            self._display_video(file_path)

    def _display_image(self, file_path: str):
        # Stop all video engines if playing
        if self.mpv_player:
            try:
                self.mpv_player.stop()
            except Exception:
                pass
        if self.qt_player:
            try:
                self.qt_player.stop()
            except Exception:
                pass
        if self.ff_player:
            self.ff_player.stop()

        pixmap = MediaLoader.load_image_pixmap(file_path)
        
        if not pixmap:
            print(f"[Player] Could not render image {file_path}. Skipping...")
            if self.indexer.history_stack and self.indexer.history_index >= 0:
                self.indexer.history_stack.pop(self.indexer.history_index)
                self.indexer.history_index -= 1
            QTimer.singleShot(50, self.next_media)
            return

        w, h = pixmap.width(), pixmap.height()

        # Update SQLite with true rendered dimensions
        if self.current_media and self.current_media.get("id"):
            media_id = self.current_media["id"]
            self.indexer.update_media_dimensions(media_id, w, h)
            self.current_media["width"] = w
            self.current_media["height"] = h

        # Strict post-load orientation gate
        orient = self.config.get("orientation_filter", "all")
        if orient == "landscape" and h > w:
            print(f"[Player] Discarding portrait image in landscape-only mode: {file_path} ({w}x{h})")
            if self.indexer.history_stack and self.indexer.history_index >= 0:
                self.indexer.history_stack.pop(self.indexer.history_index)
                self.indexer.history_index -= 1
            QTimer.singleShot(0, self.next_media)
            return
        elif orient == "portrait" and w >= h:
            print(f"[Player] Discarding landscape image in portrait-only mode: {file_path} ({w}x{h})")
            if self.indexer.history_stack and self.indexer.history_index >= 0:
                self.indexer.history_stack.pop(self.indexer.history_index)
                self.indexer.history_index -= 1
            QTimer.singleShot(0, self.next_media)
            return

        # Strict post-load resolution gate
        min_res = self.config.get("min_resolution", "none")
        max_d = max(w, h)
        if (min_res == "720p" and max_d < 1280) or \
           (min_res == "1080p" and max_d < 1920) or \
           (min_res == "4k" and max_d < 3840):
            print(f"[Player] Discarding low-resolution image ({w}x{h}) for min_res {min_res}: {file_path}")
            if self.indexer.history_stack and self.indexer.history_index >= 0:
                self.indexer.history_stack.pop(self.indexer.history_index)
                self.indexer.history_index -= 1
            QTimer.singleShot(0, self.next_media)
            return

        is_first_photo = not hasattr(self, "current_raw_pixmap") or self.current_raw_pixmap is None
        self.current_raw_pixmap = pixmap
        self.current_duration = self.config.image_duration

        # Update overlay metadata
        meta = ExifReader.extract_metadata(file_path)
        total_count = self.current_media.get("total_count") or self.indexer.get_total_count(min_res, orient)
        current_idx = self.current_media.get("display_index", self.indexer.history_index + 1)
        self.overlay.update_metadata(meta, current_idx, total_count)

        # Dual label crossfade
        target_idx = 1 if self.active_label_idx == 0 else 0
        current_label = self.img_label1 if self.active_label_idx == 0 else self.img_label2
        next_label = self.img_label2 if self.active_label_idx == 0 else self.img_label1

        self.qvideo_widget.hide()

        container_size = self.central_widget.size()
        if container_size.width() <= 0 or container_size.height() <= 0:
            container_size = self.size()

        scaled_pixmap = pixmap.scaled(container_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        next_label.setPixmap(scaled_pixmap)

        trans_type = self.config.get("transition_type", "kenburns")
        trans_duration = int(float(self.config.get("transition_duration", 1.0)) * 1000)

        if is_first_photo or trans_type == "none" or trans_duration <= 0:
            current_label.hide()
            next_label.show()
            next_label.raise_()
        else:
            TransitionManager.apply_crossfade(current_label, next_label, duration_ms=trans_duration)

        self.active_label_idx = target_idx

        self.slide_start_time = time.time()
        if not self.is_paused:
            self.slide_timer.start(int(self.current_duration * 1000))
            self.progress_timer.start()

    def _display_video(self, file_path: str):
        if self.ff_player:
            self.ff_player.stop()

        # Hide image display labels
        self.img_label1.hide()
        self.img_label2.hide()

        duration_mode = self.config.get("video_duration_mode", "full")
        if duration_mode == "photo_duration":
            self.current_duration = float(self.config.image_duration)
        elif duration_mode == "custom":
            self.current_duration = float(self.config.get("max_video_duration_seconds", 180))
        else:  # "full"
            self.current_duration = 3600.0  # Let video end naturally

        # Update overlay metadata
        min_res = self.config.get("min_resolution", "none")
        orient = self.config.get("orientation_filter", "all")
        meta = ExifReader.extract_metadata(file_path)
        total_count = self.current_media.get("total_count") or self.indexer.get_total_count(min_res, orient)
        current_idx = self.current_media.get("display_index", self.indexer.history_index + 1)
        self.overlay.update_metadata(meta, current_idx, total_count)

        self.slide_start_time = time.time()
        if not self.is_paused:
            self.slide_timer.start(int(self.current_duration * 1000))
            self.progress_timer.start()

        mute = self.config.get("mute_videos", False)

        if self.mpv_player:
            self.qvideo_widget.show()
            self.qvideo_widget.raise_()
            try:
                self.mpv_player.mute = mute
                self.mpv_player.play(file_path)
                return
            except Exception as e:
                print(f"[Player] Failed to play video via mpv: {e}")

        if self.qt_player:
            self.qvideo_widget.show()
            self.qvideo_widget.raise_()
            try:
                self.audio_output.setVolume(0.0 if mute else 1.0)
                self.qt_player.stop()
                self.qt_player.setSource(QUrl.fromLocalFile(file_path))
                self.qt_player.play()
                print(f"[Player] Playing video via QtMultimedia: {os.path.basename(file_path)}")
                return
            except Exception as e:
                print(f"[Player] QMediaPlayer error playing {file_path}: {e}")

        # PyAV FFmpeg Fallback
        if self.ff_player:
            self.qvideo_widget.hide()
            self.img_label2.hide()
            self.img_label1.show()
            self.img_label1.raise_()
            print(f"[Player] Falling back to FFmpeg PyAV player for {os.path.basename(file_path)}")
            success = self.ff_player.load_and_play(file_path)
            if not success:
                self.next_media()

    def _on_qt_duration_changed(self, duration_ms: int):
        if duration_ms > 0:
            dur_sec = duration_ms / 1000.0
            max_sec = float(self.config.get("max_video_duration_seconds", 180))
            self.current_duration = min(dur_sec, max_sec)
            print(f"[Player] Video duration detected: {dur_sec:.1f}s")
            if not self.is_paused:
                self.slide_timer.start(int(self.current_duration * 1000))

    def _on_qt_media_status_changed(self, status):
        from PySide6.QtMultimedia import QMediaPlayer
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            print("[Player] Video finished playing. Advancing to next media.")
            self.next_media()

    def _on_qt_media_error(self, error, error_string):
        print(f"[Player] QtMultimedia video error ({error}): {error_string}. Switching to FFmpeg engine.")
        if self.current_media and self.ff_player:
            self.layout.setCurrentWidget(self.img_label1)
            self.ff_player.load_and_play(self.current_media["file_path"])
        else:
            QTimer.singleShot(500, self.next_media)

    def _update_progress_bar(self):
        if self.is_paused or self.current_duration <= 0:
            return

        elapsed = time.time() - self.slide_start_time
        pct = min(100, int((elapsed / self.current_duration) * 100))
        self.overlay.progress_bar.setValue(pct)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.overlay.set_paused(self.is_paused)

        if self.is_paused:
            self.slide_timer.stop()
            self.progress_timer.stop()
            if self.mpv_player:
                self.mpv_player.pause = True
            if self.qt_player:
                self.qt_player.pause()
            if self.ff_player:
                self.ff_player.pause()
        else:
            remaining = max(500, int((self.current_duration - (time.time() - self.slide_start_time)) * 1000))
            self.slide_timer.start(remaining)
            self.progress_timer.start()
            if self.mpv_player:
                self.mpv_player.pause = False
            if self.qt_player:
                self.qt_player.play()
            if self.ff_player:
                self.ff_player.resume()

    def open_current_file_location(self):
        if not self.current_media:
            return
        path = self.current_media["file_path"]
        if os.path.exists(path):
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(path)])

    def keyPressEvent(self, event):
        if hasattr(self, "multi_controller") and self.multi_controller:
            if self.multi_controller.handle_key_event(event, self):
                return

        key = event.key()

        if key in (Qt.Key_Escape, Qt.Key_Q):
            self.close()
        elif key == Qt.Key_Space:
            self.toggle_pause()
        elif key in (Qt.Key_Right, Qt.Key_N):
            self.next_media()
        elif key in (Qt.Key_Left, Qt.Key_P):
            self.previous_media()
        elif key == Qt.Key_Up:
            self.skip_folder()
        elif key == Qt.Key_Down:
            for _ in range(10):
                self.indexer.get_next_media()
            self.next_media()
        elif key == Qt.Key_O:
            self.overlay.cycle_overlay_mode()
        elif key == Qt.Key_F:
            self.open_current_file_location()
        else:
            super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_screensaver:
            if self.mouse_pos is None:
                self.mouse_pos = event.globalPosition().toPoint()
            else:
                diff = (event.globalPosition().toPoint() - self.mouse_pos).manhattanLength()
                if diff > 15:  # Sensitive movement threshold
                    self.close()
        super().mouseMoveEvent(event)

    def closeEvent(self, event):
        if self.sleep_inhibitor:
            try:
                self.sleep_inhibitor.release()
            except Exception:
                pass
        if self.mpv_player:
            try:
                self.mpv_player.terminate()
            except Exception:
                pass
        super().closeEvent(event)
