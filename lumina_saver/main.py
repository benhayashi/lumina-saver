import sys
import os
import signal
import argparse
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QDoubleSpinBox, QComboBox, QCheckBox, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QIcon

from lumina_saver.config import ConfigManager
from lumina_saver.indexer import MediaIndexer
from lumina_saver.player_window import PlayerWindow
from lumina_saver.sleep_inhibitor import SleepInhibitor

class ScannerWorker(QThread):
    progress = Signal(int)

    def __init__(self, indexer: MediaIndexer):
        super().__init__()
        self.indexer = indexer
        self._is_interrupted = False

    def stop(self):
        self._is_interrupted = True

    def run(self):
        self._is_interrupted = False
        # 1. Fast directory scan
        self.indexer.scan_directories(progress_callback=lambda count: self.progress.emit(count))

        # 2. Lazily inspect unindexed dimensions in the background during idle time
        while not self._is_interrupted:
            updated = self.indexer.populate_unindexed_dimensions(batch_size=50)
            if updated == 0:
                break
            self.msleep(15)  # Yield CPU and network so playback remains 100% smooth

class SettingsDialog(QDialog):
    """Configuration GUI for selecting folders, resolution/orientation filters, and video options."""

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("LuminaSaver Settings 🌟")
        self.resize(620, 680)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Folder Selection Group
        grp_folders = QGroupBox("📁 Media Folders (Local & Network Shares)", self)
        folder_layout = QVBoxLayout(grp_folders)

        self.list_folders = QListWidget(self)
        for folder in self.config.media_directories:
            self.list_folders.addItem(folder)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("➕ Add Folder", self)
        btn_add.clicked.connect(self._add_folder)
        btn_remove = QPushButton("❌ Remove Selected", self)
        btn_remove.clicked.connect(self._remove_folder)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)

        folder_layout.addWidget(self.list_folders)
        folder_layout.addLayout(btn_layout)
        layout.addWidget(grp_folders)

        # Playback & Order Options Group
        grp_opts = QGroupBox("⏱ Playback & Order", self)
        opts_layout = QVBoxLayout(grp_opts)

        # Display Order (Random / Sequential Resume)
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("Display Order:"))
        self.combo_order = QComboBox(self)
        self.combo_order.addItem("Random (Default)", "random")
        self.combo_order.addItem("Sequential (Resume from last run)", "sequential")
        current_order = self.config.get("display_order", "random")
        idx = self.combo_order.findData(current_order)
        if idx >= 0:
            self.combo_order.setCurrentIndex(idx)
        order_layout.addWidget(self.combo_order)
        opts_layout.addLayout(order_layout)

        # Image Duration
        dur_layout = QHBoxLayout()
        dur_layout.addWidget(QLabel("Photo Display Duration (seconds):"))
        self.spin_dur = QDoubleSpinBox(self)
        self.spin_dur.setRange(1.0, 300.0)
        self.spin_dur.setValue(self.config.image_duration)
        dur_layout.addWidget(self.spin_dur)
        opts_layout.addLayout(dur_layout)

        # Transition Type
        trans_layout = QHBoxLayout()
        trans_layout.addWidget(QLabel("Transition Effect:"))
        self.combo_trans = QComboBox(self)
        self.combo_trans.addItems(["kenburns", "crossfade", "fade", "none"])
        self.combo_trans.setCurrentText(self.config.transition_type)
        trans_layout.addWidget(self.combo_trans)
        opts_layout.addLayout(trans_layout)

        # Overlay Mode
        over_layout = QHBoxLayout()
        over_layout.addWidget(QLabel("Metadata Overlay Mode:"))
        self.combo_overlay = QComboBox(self)
        self.combo_overlay.addItems(["full", "minimal", "off"])
        self.combo_overlay.setCurrentText(self.config.overlay_mode)
        over_layout.addWidget(self.combo_overlay)
        opts_layout.addLayout(over_layout)

        # Progress Bar Checkbox
        self.chk_progress = QCheckBox("Show Slide Timer Progress Bar (Blue bottom indicator)", self)
        self.chk_progress.setChecked(self.config.get("show_progress_bar", True))
        opts_layout.addWidget(self.chk_progress)

        layout.addWidget(grp_opts)

        # Video Settings Group
        grp_video = QGroupBox("📹 Video Settings", self)
        video_layout = QVBoxLayout(grp_video)

        self.chk_mute = QCheckBox("Mute Video Audio", self)
        self.chk_mute.setChecked(self.config.get("mute_videos", False))
        video_layout.addWidget(self.chk_mute)

        vdur_layout = QHBoxLayout()
        vdur_layout.addWidget(QLabel("Video Playback Duration:"))
        self.combo_vmode = QComboBox(self)
        self.combo_vmode.addItem("Play Full Video Clip", "full")
        self.combo_vmode.addItem("Match Photo Display Duration", "photo_duration")
        self.combo_vmode.addItem("Custom Time Limit (180s max)", "custom")
        current_vmode = self.config.get("video_duration_mode", "full")
        vidx = self.combo_vmode.findData(current_vmode)
        if vidx >= 0:
            self.combo_vmode.setCurrentIndex(vidx)
        vdur_layout.addWidget(self.combo_vmode)
        video_layout.addLayout(vdur_layout)

        layout.addWidget(grp_video)

        # Window & Multi-Monitor Group
        grp_win = QGroupBox("🖥 Display & Multi-Monitor", self)
        win_layout = QVBoxLayout(grp_win)

        wmode_layout = QHBoxLayout()
        wmode_layout.addWidget(QLabel("Window Mode:"))
        self.combo_wmode = QComboBox(self)
        self.combo_wmode.addItem("Fullscreen (Screensaver)", "fullscreen")
        self.combo_wmode.addItem("Windowed (Resizable Window)", "windowed")
        cur_wmode = self.config.get("window_mode", "fullscreen")
        widx = self.combo_wmode.findData(cur_wmode)
        if widx >= 0:
            self.combo_wmode.setCurrentIndex(widx)
        wmode_layout.addWidget(self.combo_wmode)
        win_layout.addLayout(wmode_layout)

        mmon_layout = QHBoxLayout()
        mmon_layout.addWidget(QLabel("Multi-Monitor Setup:"))
        self.combo_mmon = QComboBox(self)
        self.combo_mmon.addItem("Multi-Monitor Independent (Unique photo per screen)", "dual_independent")
        self.combo_mmon.addItem("Primary Monitor Only", "primary_only")
        cur_mmon = self.config.get("multi_monitor_mode", "dual_independent")
        midx = self.combo_mmon.findData(cur_mmon)
        if midx >= 0:
            self.combo_mmon.setCurrentIndex(midx)
        mmon_layout.addWidget(self.combo_mmon)
        win_layout.addLayout(mmon_layout)

        # Interlocked Multi-Monitor Checkbox
        self.chk_interlock = QCheckBox("Interlock Multi-Monitor Key Controls (Right Arrow = Screen 1, Up Arrow = Screen 2)", self)
        self.chk_interlock.setChecked(self.config.get("interlocked_multi_monitor", True))
        win_layout.addWidget(self.chk_interlock)

        # Prevent Display Sleep Checkbox
        self.chk_prevent_sleep = QCheckBox("Prevent Display Sleep / Screen Timeout (Keep screen awake)", self)
        self.chk_prevent_sleep.setChecked(self.config.get("prevent_display_sleep", True))
        self.chk_prevent_sleep.setToolTip("Disables screen blanking, DPMS monitor power-off, and OS screen lock timeouts while LuminaSaver is running.")
        win_layout.addWidget(self.chk_prevent_sleep)

        layout.addWidget(grp_win)

        # Resolution & Orientation Filters Group
        grp_filter = QGroupBox("🔍 Display Filters (Resolution & Aspect Ratio)", self)
        filter_layout = QVBoxLayout(grp_filter)

        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Minimum Photo Resolution:"))
        self.combo_res = QComboBox(self)
        self.combo_res.addItem("None (Display all photos)", "none")
        self.combo_res.addItem("HD Minimum (1280×720+)", "720p")
        self.combo_res.addItem("Full HD Minimum (1920×1080+)", "1080p")
        self.combo_res.addItem("4K Minimum (3840×2160+)", "4k")
        cres = self.config.get("min_resolution", "none")
        ridx = self.combo_res.findData(cres)
        if ridx >= 0:
            self.combo_res.setCurrentIndex(ridx)
        res_layout.addWidget(self.combo_res)
        filter_layout.addLayout(res_layout)

        orient_layout = QHBoxLayout()
        orient_layout.addWidget(QLabel("Photo Aspect Ratio / Orientation:"))
        self.combo_orient = QComboBox(self)
        self.combo_orient.addItem("All Orientations", "all")
        self.combo_orient.addItem("Landscape Only (Wide photos)", "landscape")
        self.combo_orient.addItem("Portrait Only (Tall photos)", "portrait")
        corient = self.config.get("orientation_filter", "all")
        oidx = self.combo_orient.findData(corient)
        if oidx >= 0:
            self.combo_orient.setCurrentIndex(oidx)
        orient_layout.addWidget(self.combo_orient)
        filter_layout.addLayout(orient_layout)

        layout.addWidget(grp_filter)

        # Re-index button & Save & Launch Buttons
        bottom_box = QHBoxLayout()
        btn_reindex = QPushButton("⚡ Force Re-Index Library", self)
        btn_reindex.clicked.connect(self._force_reindex)
        btn_save = QPushButton("💾 Save Settings", self)
        btn_save.clicked.connect(self._save_settings)
        btn_launch = QPushButton("▶ Launch Slideshow", self)
        btn_launch.setStyleSheet("font-weight: bold; background-color: #3B82F6; color: white;")
        btn_launch.clicked.connect(self._launch_slideshow)

        bottom_box.addWidget(btn_reindex)
        bottom_box.addWidget(btn_save)
        bottom_box.addWidget(btn_launch)
        layout.addLayout(bottom_box)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Photo/Video Folder or Network Share")
        if folder:
            self.list_folders.addItem(folder)

    def _remove_folder(self):
        row = self.list_folders.currentRow()
        if row >= 0:
            self.list_folders.takeItem(row)

    def _force_reindex(self):
        self._save_settings(show_message=False)
        indexer = MediaIndexer(
            db_path=self.config.get("cache_db_path"),
            media_dirs=self.config.media_directories,
            image_exts=self.config.get("image_extensions"),
            video_exts=self.config.get("video_extensions")
        )
        total = indexer.scan_directories()
        QMessageBox.information(self, "Library Re-Indexed", f"Re-indexed library! Discovered {total:,} media files.")

    def _save_settings(self, show_message: bool = True):
        folders = [self.list_folders.item(i).text() for i in range(self.list_folders.count())]
        self.config.set("media_directories", folders)
        self.config.set("window_mode", self.combo_wmode.currentData())
        self.config.set("multi_monitor_mode", self.combo_mmon.currentData())
        self.config.set("interlocked_multi_monitor", self.chk_interlock.isChecked())
        self.config.set("display_order", self.combo_order.currentData())
        self.config.set("image_duration", self.spin_dur.value())
        self.config.set("transition_type", self.combo_trans.currentText())
        self.config.set("overlay_mode", self.combo_overlay.currentText())
        self.config.set("show_progress_bar", self.chk_progress.isChecked())
        self.config.set("mute_videos", self.chk_mute.isChecked())
        self.config.set("video_duration_mode", self.combo_vmode.currentData())
        self.config.set("min_resolution", self.combo_res.currentData())
        self.config.set("orientation_filter", self.combo_orient.currentData())
        self.config.set("prevent_display_sleep", self.chk_prevent_sleep.isChecked())
        
        if show_message:
            QMessageBox.information(self, "Settings Saved", "LuminaSaver configuration updated successfully!")

    def _launch_slideshow(self):
        self._save_settings(show_message=False)
        self.accept()

def print_help():
    print("""LuminaSaver - High-Performance Photo & Video Screensaver and Slideshow

Usage:
  lumina-saver [options]

General Options:
  -h, --help            Show this help message and exit
  -v, --version         Show program version
  -c, --config          Open configuration settings dialog
  -w, --windowed        Run in standalone windowed mode (1280x720)
  -f, --fullscreen      Run in standalone fullscreen mode
  --prevent-sleep       Keep display awake and disable screen timeouts
  --allow-sleep         Allow normal OS display sleep and screen timeouts

Screensaver Options:
  -s, --screensaver     Run in screensaver mode (exits on mouse movement or Esc)
  /s                    Windows screensaver flag (fullscreen screensaver)
  /c, /configure        Windows screensaver configuration flag
  /p <hwnd>             Windows screensaver preview flag
  -root                 Linux XScreenSaver fullscreen mode
  -window-id <id>       Linux XScreenSaver preview window
""")

def main():
    from lumina_saver.multi_monitor import MultiMonitorController

    # Pre-parse help/version before starting Qt event loop if possible
    raw_args = [a.lower() for a in sys.argv[1:]]
    if "-h" in raw_args or "--help" in raw_args or "/?" in raw_args:
        print_help()
        sys.exit(0)
    if "-v" in raw_args or "--version" in raw_args:
        print("LuminaSaver version 1.0.0")
        sys.exit(0)

    app = QApplication(sys.argv)

    is_screensaver = False
    show_config = False
    force_window_mode = None
    override_prevent_sleep = None

    for arg in raw_args:
        if arg in ("/s", "-s", "--screensaver", "-root"):
            is_screensaver = True
        elif arg in ("/c", "-c", "--config", "--configure", "--settings") or arg.startswith("/c:"):
            show_config = True
        elif arg.startswith("/p") or arg == "-window-id":
            # Screensaver mini-preview pane - exit cleanly
            sys.exit(0)
        elif arg in ("-w", "--windowed"):
            force_window_mode = "windowed"
        elif arg in ("-f", "--fullscreen"):
            force_window_mode = "fullscreen"
        elif arg == "--prevent-sleep":
            override_prevent_sleep = True
        elif arg == "--allow-sleep":
            override_prevent_sleep = False

    config = ConfigManager()
    if force_window_mode:
        config.data["window_mode"] = force_window_mode
    if override_prevent_sleep is not None:
        config.data["prevent_display_sleep"] = override_prevent_sleep

    if show_config or (len(sys.argv) == 1 and not is_screensaver):
        dlg = SettingsDialog(config)
        if dlg.exec() != QDialog.DialogCode.Accepted and not is_screensaver:
            sys.exit(0)

    # Cleanly exit on terminal Ctrl+C without traceback
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    indexer = MediaIndexer(
        db_path=config.get("cache_db_path"),
        media_dirs=config.media_directories,
        image_exts=config.get("image_extensions"),
        video_exts=config.get("video_extensions")
    )

    # If library is empty, do a fast initial scan so there are files to show immediately
    if indexer.get_total_count() == 0:
        print("[Main] Initial media library scan...")
        indexer.scan_directories()

    # Initialize cross-platform display sleep / screen timeout inhibitor
    sleep_inhibitor = SleepInhibitor(app_name="LuminaSaver", reason="LuminaSaver Slideshow active")
    app._sleep_inhibitor = sleep_inhibitor
    if config.get("prevent_display_sleep", True):
        sleep_inhibitor.inhibit()
    app.aboutToQuit.connect(sleep_inhibitor.release)

    screens = app.screens()
    mmon_mode = config.get("multi_monitor_mode", "dual_independent")
    players = []

    if (is_screensaver or mmon_mode == "dual_independent") and len(screens) > 1:
        # Launch independent slideshow player on each connected screen!
        print(f"[Main] Launching dual/multi-monitor independent slideshow across {len(screens)} screens.")
        for scr in screens:
            p = PlayerWindow(config=config, indexer=indexer, is_screensaver=is_screensaver, target_screen=scr, sleep_inhibitor=sleep_inhibitor)
            players.append(p)

        # Set up Interlocked Multi-Monitor Controller
        controller = MultiMonitorController(players=players, config=config, sleep_inhibitor=sleep_inhibitor)
        for p in players:
            p.multi_controller = controller
            p.start()
    else:
        # Single screen mode
        p = PlayerWindow(config=config, indexer=indexer, is_screensaver=is_screensaver, target_screen=app.primaryScreen(), sleep_inhibitor=sleep_inhibitor)
        players.append(p)
        controller = MultiMonitorController(players=players, config=config, sleep_inhibitor=sleep_inhibitor)
        p.multi_controller = controller
        p.start()

    # Start non-blocking background scanner worker to keep index synced
    scanner_worker = ScannerWorker(indexer)
    app._scanner_worker = scanner_worker
    scanner_worker.start()

    # Auto re-index interval timer if configured
    reindex_mins = config.get("auto_reindex_minutes", 15)
    if reindex_mins > 0:
        reindex_timer = QTimer(app)
        reindex_timer.setInterval(reindex_mins * 60 * 1000)
        reindex_timer.timeout.connect(lambda: scanner_worker.start() if not scanner_worker.isRunning() else None)
        reindex_timer.start()
        app._reindex_timer = reindex_timer

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
