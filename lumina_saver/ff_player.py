import os
import time
from typing import Optional
import av
from PySide6.QtCore import QObject, QTimer, Signal, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel

class PyAVVideoPlayer(QObject):
    """FFmpeg-backed software video decoder and renderer using PyAV."""
    
    frame_ready = Signal(QPixmap)
    finished = Signal()

    def __init__(self, target_label: QLabel, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.target_label = target_label
        self.container: Optional[av.Container] = None
        self.stream_generator = None
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._fetch_next_frame)
        self.is_playing = False
        self.fps = 30.0

    def load_and_play(self, file_path: str) -> bool:
        self.stop()
        try:
            self.container = av.open(file_path)
            video_stream = self.container.streams.video[0]
            
            # Extract FPS
            if video_stream.average_rate:
                self.fps = float(video_stream.average_rate)
            elif video_stream.base_rate:
                self.fps = float(video_stream.base_rate)
            else:
                self.fps = 30.0
                
            self.fps = max(10.0, min(120.0, self.fps))
            interval_ms = int(1000.0 / self.fps)

            # Generator for video frames
            self.stream_generator = self.container.decode(video=0)
            
            self.is_playing = True
            self.timer.start(interval_ms)
            print(f"[PyAVPlayer] Playing {os.path.basename(file_path)} at {self.fps:.1f} FPS via FFmpeg")
            return True

        except Exception as e:
            print(f"[PyAVPlayer] Error opening video {file_path}: {e}")
            self.stop()
            return False

    def _fetch_next_frame(self):
        if not self.is_playing or not self.stream_generator:
            return

        try:
            frame = next(self.stream_generator)
            # Convert AVFrame to RGB numpy array/bytes
            img_rgb = frame.to_rgb()
            data = img_rgb.to_ndarray()
            
            h, w, c = data.shape
            bytes_per_line = c * w
            
            qimg = QImage(data.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            
            # Scale to fit label container
            size = self.target_label.size()
            if size.width() > 0 and size.height() > 0:
                scaled_pixmap = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.target_label.setPixmap(scaled_pixmap)
            else:
                self.target_label.setPixmap(pixmap)

        except StopIteration:
            # Video reached End Of Stream
            print("[PyAVPlayer] Reached end of video stream.")
            self.stop()
            self.finished.emit()
        except Exception as e:
            print(f"[PyAVPlayer] Frame decode error: {e}")
            self.stop()
            self.finished.emit()

    def pause(self):
        if self.is_playing:
            self.timer.stop()

    def resume(self):
        if self.is_playing and not self.timer.isActive():
            interval_ms = int(1000.0 / self.fps)
            self.timer.start(interval_ms)

    def stop(self):
        self.timer.stop()
        self.is_playing = False
        self.stream_generator = None
        if self.container:
            try:
                self.container.close()
            except Exception:
                pass
            self.container = None
