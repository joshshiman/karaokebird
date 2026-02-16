from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QLabel


class StrokedLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stroke_color = QColor("#000000")
        self.stroke_width = 3
        self.stroke_enabled = True

        # Animation state
        self.enable_animation = False
        self._text_opacity = 1.0
        self._anim = QPropertyAnimation(self, b"textOpacity")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.finished.connect(self._on_anim_finished)
        self._pending_text = ""

    def get_text_opacity(self):
        return self._text_opacity

    def set_text_opacity(self, opacity):
        self._text_opacity = opacity
        self.update()

    textOpacity = pyqtProperty(float, get_text_opacity, set_text_opacity)

    def setStrokeColor(self, color):
        self.stroke_color = QColor(color)

    def setStrokeEnabled(self, enabled):
        self.stroke_enabled = enabled
        self.update()

    def setText(self, text):
        if not self.enable_animation:
            super().setText(text)
            return

        # If we are already displaying this text, or it's already queued to be shown, skip.
        if self.text() == text or (
            self._anim.state() == QPropertyAnimation.State.Running
            and self._pending_text == text
        ):
            return

        self._pending_text = text

        if self._anim.state() == QPropertyAnimation.State.Running:
            # If we are already fading out, just update the target _pending_text and continue.
            if self._anim.direction() == QPropertyAnimation.Direction.Forward:
                return

            # If we were fading in, reverse to fade out the now-stale text.
            self._anim.stop()
            self._anim.setDirection(QPropertyAnimation.Direction.Forward)
            # Start from current opacity for smoothness
            self._anim.setStartValue(self._text_opacity)
            self._anim.setEndValue(0.0)
            # Adjust duration based on current opacity
            duration = int(150 * self._text_opacity)
            self._anim.setDuration(max(20, duration))
            self._anim.start()
            return

        # Not running: Start a fresh fade out
        self._anim.setDirection(QPropertyAnimation.Direction.Forward)
        self._anim.setDuration(150)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_anim_finished(self):
        if self._anim.direction() == QPropertyAnimation.Direction.Forward:
            # Faded out. Update the actual label text and fade back in.
            super().setText(self._pending_text)
            self._anim.setDirection(QPropertyAnimation.Direction.Backward)
            # Ensure we fade back to full opacity
            self._anim.setStartValue(1.0)
            self._anim.setEndValue(0.0)
            self._anim.setDuration(150)
            self._anim.start()

    def paintEvent(self, event):
        if not self.text():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._text_opacity)

        metrics = self.fontMetrics()
        # Calculate centered position (assuming AlignCenter)
        x = (self.width() - metrics.horizontalAdvance(self.text())) / 2
        y = (self.height() + metrics.ascent() - metrics.descent()) / 2

        path = QPainterPath()
        path.addText(x, y, self.font(), self.text())

        # Draw Stroke
        if self.stroke_enabled:
            pen = QPen(self.stroke_color)
            pen.setWidth(self.stroke_width)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        # Draw Fill
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.palette().text())
        painter.drawPath(path)
