import random
from typing import Tuple
from PySide6.QtWidgets import QWidget, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect, QPoint, QParallelAnimationGroup, Qt
from PySide6.QtGui import QPixmap, QTransform

class TransitionManager:
    """Manages GPU-accelerated smooth slide transitions and Ken Burns zoom effects."""

    @staticmethod
    def apply_crossfade(old_widget: QWidget, new_widget: QWidget, duration_ms: int = 1000, on_complete=None):
        """Crossfades old_widget to new_widget with smooth opacity curves."""
        old_effect = QGraphicsOpacityEffect(old_widget)
        new_effect = QGraphicsOpacityEffect(new_widget)

        old_widget.setGraphicsEffect(old_effect)
        new_widget.setGraphicsEffect(new_effect)

        new_widget.show()
        new_widget.raise_()

        anim_old = QPropertyAnimation(old_effect, b"opacity")
        anim_old.setDuration(duration_ms)
        anim_old.setStartValue(1.0)
        anim_old.setEndValue(0.0)
        anim_old.setEasingCurve(QEasingCurve.Type.InOutQuad)

        anim_new = QPropertyAnimation(new_effect, b"opacity")
        anim_new.setDuration(duration_ms)
        anim_new.setStartValue(0.0)
        anim_new.setEndValue(1.0)
        anim_new.setEasingCurve(QEasingCurve.Type.InOutQuad)

        group = QParallelAnimationGroup()
        group.addAnimation(anim_old)
        group.addAnimation(anim_new)

        def cleanup():
            old_widget.hide()
            old_widget.setGraphicsEffect(None)
            new_widget.setGraphicsEffect(None)
            if on_complete:
                on_complete()

        group.finished.connect(cleanup)
        group.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        # Keep reference attached
        new_widget._current_transition = group

    @staticmethod
    def calculate_kenburns_transform(pixmap_size: QPoint, container_size: QPoint, progress: float) -> Tuple[QRect, QRect]:
        """Calculates start and end rectangles for smooth Ken Burns pan/zoom."""
        sw, sh = pixmap_size.x(), pixmap_size.y()
        cw, ch = container_size.x(), container_size.y()

        if sw == 0 or sh == 0 or cw == 0 or ch == 0:
            return QRect(0, 0, cw, ch), QRect(0, 0, cw, ch)

        scale_base = max(cw / sw, ch / sh)
        zoom_start = scale_base * random.uniform(1.0, 1.05)
        zoom_end = scale_base * random.uniform(1.08, 1.15)

        dx = (sw * zoom_end - cw) / 2
        dy = (sh * zoom_end - ch) / 2

        # Random pan directions
        pan_x = random.choice([-dx, dx])
        pan_y = random.choice([-dy, dy])

        rect_start = QRect(int(-dx), int(-dy), int(sw * zoom_start), int(sh * zoom_start))
        rect_end = QRect(int(pan_x), int(pan_y), int(sw * zoom_end), int(sh * zoom_end))

        return rect_start, rect_end
