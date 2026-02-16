from PyQt6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    pyqtProperty,
)
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QLabel


class StrokedLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stroke_color = QColor("#000000")
        self.stroke_width = 3
        self.stroke_enabled = True

        # Animation Settings
        self.enable_animation = False
        self.animation_type = "fade"  # "fade", "slide", "zoom"

        # Animation Properties
        self._text_opacity = 1.0
        self._y_offset = 0.0
        self._text_scale = 1.0

        # Internal Animation State
        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.finished.connect(self._on_anim_finished)
        self._anim_stage = 0  # 0: Idle, 1: Out, 2: In
        self._pending_text = ""

    # --- Properties for Animation ---

    @pyqtProperty(float)
    def textOpacity(self):
        return self._text_opacity

    @textOpacity.setter
    def textOpacity(self, opacity):
        self._text_opacity = opacity
        self.update()

    @pyqtProperty(float)
    def textOffset(self):
        return self._y_offset

    @textOffset.setter
    def textOffset(self, offset):
        self._y_offset = offset
        self.update()

    @pyqtProperty(float)
    def textScale(self):
        return self._text_scale

    @textScale.setter
    def textScale(self, scale):
        self._text_scale = scale
        self.update()

    # --- Public API ---

    def setStrokeColor(self, color):
        self.stroke_color = QColor(color)

    def setStrokeEnabled(self, enabled):
        self.stroke_enabled = enabled
        self.update()

    def setText(self, text):
        if not self.enable_animation:
            super().setText(text)
            return

        # If we are already displaying this text, skip.
        if self.text() == text:
            return

        # If we are already queuing this text, skip.
        if self._anim_stage != 0 and self._pending_text == text:
            return

        self._pending_text = text

        # If already animating out, just wait for text swap.
        if self._anim_stage == 1:
            return

        # Start animation out
        self._start_anim_stage(1)

    # --- Animation Logic ---

    def _start_anim_stage(self, stage):
        self._anim_stage = stage
        self._anim_group.stop()
        self._anim_group.clear()

        duration = 150
        easing = QEasingCurve.Type.OutQuad

        # 1. Opacity Animation (Universal)
        opacity_anim = QPropertyAnimation(self, b"textOpacity")
        opacity_anim.setDuration(duration)
        opacity_anim.setEasingCurve(easing)

        # 2. Translation Animation (Slide)
        offset_anim = QPropertyAnimation(self, b"textOffset")
        offset_anim.setDuration(duration)
        offset_anim.setEasingCurve(easing)

        # 3. Scaling Animation (Zoom)
        scale_anim = QPropertyAnimation(self, b"textScale")
        scale_anim.setDuration(duration)
        scale_anim.setEasingCurve(easing)

        if stage == 1:  # MOVING OUT
            opacity_anim.setStartValue(self._text_opacity)
            opacity_anim.setEndValue(0.0)

            offset_anim.setStartValue(self._y_offset)
            offset_anim.setEndValue(-15.0 if self.animation_type == "slide" else 0.0)

            scale_anim.setStartValue(self._text_scale)
            scale_anim.setEndValue(0.8 if self.animation_type == "zoom" else 1.0)
        else:  # MOVING IN
            opacity_anim.setStartValue(0.0)
            opacity_anim.setEndValue(1.0)

            offset_anim.setStartValue(15.0 if self.animation_type == "slide" else 0.0)
            offset_anim.setEndValue(0.0)

            scale_anim.setStartValue(1.2 if self.animation_type == "zoom" else 1.0)
            scale_anim.setEndValue(1.0)

        self._anim_group.addAnimation(opacity_anim)
        if self.animation_type == "slide":
            self._anim_group.addAnimation(offset_anim)
        if self.animation_type == "zoom":
            self._anim_group.addAnimation(scale_anim)

        self._anim_group.start()

    def _on_anim_finished(self):
        if self._anim_stage == 1:
            # Text is invisible/out. Change it and bring it back in.
            super().setText(self._pending_text)
            self._start_anim_stage(2)
        else:
            self._anim_stage = 0

    # --- Rendering ---

    def paintEvent(self, event):
        if not self.text():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._text_opacity)

        metrics = self.fontMetrics()
        # Calculate base centered position
        tw = metrics.horizontalAdvance(self.text())
        th = metrics.ascent()
        x = (self.width() - tw) / 2
        y = (self.height() + th - metrics.descent()) / 2

        # Transform for Slide and Zoom
        # Calculate center point for transformation
        cx = x + tw / 2
        cy = y - th / 2

        painter.translate(cx, cy)
        if self.animation_type == "slide":
            painter.translate(0, self._y_offset)
        if self.animation_type == "zoom":
            painter.scale(self._text_scale, self._text_scale)
        painter.translate(-cx, -cy)

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
