import unittest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from lumina_saver.multi_monitor import MultiMonitorController

class DummyPlayer:
    def __init__(self, name="Player"):
        self.name = name
        self.next_calls = 0
        self.prev_calls = 0
        self.paused = False
        self.closed = False
        self.overlay = MagicMock()

    def next_media(self):
        self.next_calls += 1

    def previous_media(self):
        self.prev_calls += 1

    def toggle_pause(self):
        self.paused = not self.paused

    def close(self):
        self.closed = True

class DummyConfig:
    def __init__(self, interlocked=True):
        self._interlocked = interlocked

    def get(self, key, default=None):
        if key == "interlocked_multi_monitor":
            return self._interlocked
        return default

class TestMultiMonitorController(unittest.TestCase):

    def setUp(self):
        self.p1 = DummyPlayer("Screen1")
        self.p2 = DummyPlayer("Screen2")
        self.config = DummyConfig(interlocked=True)
        self.controller = MultiMonitorController(players=[self.p1, self.p2], config=self.config)

    def _make_key_event(self, key):
        return QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)

    def test_single_player_returns_false(self):
        single_controller = MultiMonitorController(players=[self.p1], config=self.config)
        event = self._make_key_event(Qt.Key_Right)
        handled = single_controller.handle_key_event(event, self.p1)
        self.assertFalse(handled)

    def test_escape_closes_all_players(self):
        event = self._make_key_event(Qt.Key_Escape)
        handled = self.controller.handle_key_event(event, self.p1)
        self.assertTrue(handled)
        self.assertTrue(self.p1.closed)
        self.assertTrue(self.p2.closed)

    def test_space_pauses_all_players(self):
        event = self._make_key_event(Qt.Key_Space)
        handled = self.controller.handle_key_event(event, self.p1)
        self.assertTrue(handled)
        self.assertTrue(self.p1.paused)
        self.assertTrue(self.p2.paused)

    def test_interlocked_arrow_routing(self):
        # Right arrow -> Screen 1 next
        event_right = self._make_key_event(Qt.Key_Right)
        self.assertTrue(self.controller.handle_key_event(event_right, self.p1))
        self.assertEqual(self.p1.next_calls, 1)
        self.assertEqual(self.p2.next_calls, 0)

        # Up arrow -> Screen 2 next
        event_up = self._make_key_event(Qt.Key_Up)
        self.assertTrue(self.controller.handle_key_event(event_up, self.p1))
        self.assertEqual(self.p1.next_calls, 1)
        self.assertEqual(self.p2.next_calls, 1)

        # Left arrow -> Screen 1 previous
        event_left = self._make_key_event(Qt.Key_Left)
        self.assertTrue(self.controller.handle_key_event(event_left, self.p1))
        self.assertEqual(self.p1.prev_calls, 1)
        self.assertEqual(self.p2.prev_calls, 0)

        # Down arrow -> Screen 2 previous
        event_down = self._make_key_event(Qt.Key_Down)
        self.assertTrue(self.controller.handle_key_event(event_down, self.p1))
        self.assertEqual(self.p1.prev_calls, 1)
        self.assertEqual(self.p2.prev_calls, 1)

    def test_tab_focus_switching(self):
        event_tab = self._make_key_event(Qt.Key_Tab)
        handled = self.controller.handle_key_event(event_tab, self.p1)
        self.assertTrue(handled)
        self.assertEqual(self.controller.active_focus_index, 1)
        self.p2.overlay.show_temporary_message.assert_called_with("Focused: Screen 2")

if __name__ == "__main__":
    unittest.main()
