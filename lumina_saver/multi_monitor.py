from typing import List, Optional, Any
from PySide6.QtCore import Qt, QObject, QEvent

class MultiMonitorController(QObject):
    """Orchestrates interlocked key controls and synchronized playback across multi-display setups."""

    def __init__(self, players: List[Any] = None, config: Any = None):
        super().__init__()
        self.players = players or []
        self.config = config
        self.active_focus_index = 0

    def add_player(self, player):
        if player not in self.players:
            self.players.append(player)
            player.multi_controller = self

    def handle_key_event(self, event, sender_player) -> bool:
        """Processes interlocked keyboard shortcuts across all connected display windows.
        
        Returns True if event was handled (intercepted), False otherwise.
        """
        if not self.config or not self.config.get("interlocked_multi_monitor", True):
            return False

        if len(self.players) <= 1:
            return False

        key = event.key()

        # Global Actions Across ALL Displays
        if key in (Qt.Key_Escape, Qt.Key_Q):
            print("[MultiMonitor] Interlocked Close: Exit all displays.")
            for p in list(self.players):
                p.close()
            return True

        elif key == Qt.Key_Space:
            print("[MultiMonitor] Interlocked Pause: Toggle pause on all displays.")
            for p in self.players:
                p.toggle_pause()
            return True

        elif key == Qt.Key_O:
            print("[MultiMonitor] Interlocked Overlay: Toggle HUD on all displays.")
            for p in self.players:
                p.overlay.cycle_overlay_mode()
            return True

        # Tab key toggles focus between Screen 1 and Screen 2 for single-arrow control
        elif key == Qt.Key_Tab:
            self.active_focus_index = (self.active_focus_index + 1) % len(self.players)
            target = self.players[self.active_focus_index]
            print(f"[MultiMonitor] Switched active interleaved focus to Screen {self.active_focus_index + 1}")
            target.overlay.show_temporary_message(f"Focused: Screen {self.active_focus_index + 1}")
            return True

        # Interlocked Screen Direct Controls:
        # Right Arrow -> Screen 1 Next (or focused screen)
        # Up Arrow -> Screen 2 Next
        # Left Arrow -> Screen 1 Previous
        # Down Arrow -> Screen 2 Previous
        # 1 / 2 Keys -> Direct Screen 1 / Screen 2 Next
        if key in (Qt.Key_Right, Qt.Key_N):
            p = self.players[0] if len(self.players) > 0 else sender_player
            p.next_media()
            return True

        elif key in (Qt.Key_Up, Qt.Key_PageUp):
            p = self.players[1] if len(self.players) > 1 else sender_player
            p.next_media()
            return True

        elif key in (Qt.Key_Left, Qt.Key_P):
            p = self.players[0] if len(self.players) > 0 else sender_player
            p.previous_media()
            return True

        elif key in (Qt.Key_Down, Qt.Key_PageDown):
            p = self.players[1] if len(self.players) > 1 else sender_player
            p.previous_media()
            return True

        elif key == Qt.Key_1:
            if len(self.players) >= 1:
                self.players[0].next_media()
            return True

        elif key == Qt.Key_2:
            if len(self.players) >= 2:
                self.players[1].next_media()
            return True

        return False
