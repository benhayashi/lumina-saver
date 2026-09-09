import os
from typing import Dict, Any, Optional
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar, QFrame
from PySide6.QtCore import Qt, QTimer, Property, QPropertyAnimation
from PySide6.QtGui import QFont, QColor, QPalette

class GlassCard(QFrame):
    """Modern translucent glassmorphism container frame."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(18, 22, 30, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 10px 16px;
            }
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', 'Roboto', 'Inter', sans-serif;
            }
        """)

class UIOverlay(QWidget):
    """HUD overlay rendering metadata cards, progress indicator, and keyboard guide."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.overlay_mode = "full"  # "full", "minimal", "off"
        self.is_paused = False

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 20)

        # Top Bar (Folder/Filename + Index Count)
        top_layout = QHBoxLayout()
        
        # Left Top Card (Path & Name)
        self.top_left_card = GlassCard(self)
        top_left_box = QVBoxLayout(self.top_left_card)
        top_left_box.setContentsMargins(6, 4, 6, 4)
        top_left_box.setSpacing(2)

        self.lbl_folder = QLabel("📁 /", self.top_left_card)
        font_folder = QFont("Segoe UI", 12, QFont.Weight.Medium)
        self.lbl_folder.setFont(font_folder)
        self.lbl_folder.setStyleSheet("color: rgba(255, 255, 255, 0.75);")

        self.lbl_filename = QLabel("Filename.jpg", self.top_left_card)
        font_filename = QFont("Segoe UI", 15, QFont.Weight.Bold)
        self.lbl_filename.setFont(font_filename)

        top_left_box.addWidget(self.lbl_folder)
        top_left_box.addWidget(self.lbl_filename)

        # Right Top Card (Index counter)
        self.top_right_card = GlassCard(self)
        top_right_box = QHBoxLayout(self.top_right_card)
        top_right_box.setContentsMargins(6, 4, 6, 4)

        self.lbl_counter = QLabel("0 / 0", self.top_right_card)
        self.lbl_counter.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.lbl_counter.setStyleSheet("color: #60A5FA;")  # Modern sky blue accent
        top_right_box.addWidget(self.lbl_counter)

        top_layout.addWidget(self.top_left_card, alignment=Qt.AlignLeft | Qt.AlignTop)
        top_layout.addStretch()
        top_layout.addWidget(self.top_right_card, alignment=Qt.AlignRight | Qt.AlignTop)

        main_layout.addLayout(top_layout)
        main_layout.addStretch()

        # Center Paused Indicator
        self.paused_card = GlassCard(self)
        paused_box = QHBoxLayout(self.paused_card)
        self.lbl_paused = QLabel("⏸ PAUSED", self.paused_card)
        self.lbl_paused.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.lbl_paused.setStyleSheet("color: #FBBF24;")
        paused_box.addWidget(self.lbl_paused)
        self.paused_card.hide()

        main_layout.addWidget(self.paused_card, alignment=Qt.AlignCenter)
        main_layout.addStretch()

        # Bottom Bar (EXIF Metadata + Progress Bar)
        bottom_layout = QVBoxLayout()
        
        self.bottom_card = GlassCard(self)
        bottom_card_box = QVBoxLayout(self.bottom_card)
        bottom_card_box.setContentsMargins(6, 6, 6, 6)
        bottom_card_box.setSpacing(4)

        self.lbl_date = QLabel("📅 --", self.bottom_card)
        self.lbl_date.setFont(QFont("Segoe UI", 12))
        
        self.lbl_exif = QLabel("📷 --", self.bottom_card)
        self.lbl_exif.setFont(QFont("Segoe UI", 11))
        self.lbl_exif.setStyleSheet("color: rgba(255, 255, 255, 0.85);")

        bottom_card_box.addWidget(self.lbl_date)
        bottom_card_box.addWidget(self.lbl_exif)

        # Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 2px;
            }
        """)

        bottom_layout.addWidget(self.bottom_card, alignment=Qt.AlignLeft)
        bottom_layout.addWidget(self.progress_bar)

        main_layout.addLayout(bottom_layout)

    def update_metadata(self, meta: Dict[str, Any], current_index: int, total_count: int):
        """Updates text fields with new photo/video details."""
        folder = meta.get("folder_name", "")
        file_name = meta.get("file_name", "")
        date_taken = meta.get("date_taken", "")
        camera = meta.get("camera", "")
        exposure = meta.get("exposure", "")
        dimensions = meta.get("dimensions", "")

        self.lbl_folder.setText(f"📁 {folder}")
        self.lbl_filename.setText(f"{file_name}")
        self.lbl_counter.setText(f"{current_index:,} / {total_count:,}")

        date_text = f"📅 {date_taken}" if date_taken else ""
        if dimensions:
            date_text += f"   •   📐 {dimensions}"
        self.lbl_date.setText(date_text)

        exif_parts = []
        if camera:
            exif_parts.append(f"📷 {camera}")
        if exposure:
            exif_parts.append(f"⚙️ {exposure}")
        
        exif_str = "   |   ".join(exif_parts) if exif_parts else ""
        self.lbl_exif.setText(exif_str)
        self.lbl_exif.setVisible(bool(exif_str))

    def set_paused(self, paused: bool):
        self.is_paused = paused
        self.paused_card.setVisible(paused)

    def cycle_overlay_mode(self) -> str:
        modes = ["full", "minimal", "off"]
        idx = (modes.index(self.overlay_mode) + 1) % len(modes)
        self.overlay_mode = modes[idx]
        self.apply_overlay_mode()
        return self.overlay_mode

    def apply_overlay_mode(self, show_progress_bar: Optional[bool] = None):
        if show_progress_bar is not None:
            self.show_progress_bar = show_progress_bar

        show_pb = getattr(self, "show_progress_bar", True)

        if self.overlay_mode == "full":
            self.top_left_card.show()
            self.top_right_card.show()
            self.bottom_card.show()
            self.progress_bar.setVisible(show_pb)
        elif self.overlay_mode == "minimal":
            self.top_left_card.show()
            self.top_right_card.show()
            self.bottom_card.hide()
            self.progress_bar.setVisible(show_pb)
        else:  # "off"
            self.top_left_card.hide()
            self.top_right_card.hide()
            self.bottom_card.hide()
            self.progress_bar.hide()
