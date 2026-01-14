from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QLabel


class StrokedLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stroke_color = QColor("#000000")
        self.stroke_width = 3

    def setStrokeColor(self, color):
        self.stroke_color = QColor(color)

    def paintEvent(self, event):
        if not self.text():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        metrics = self.fontMetrics()
        # Calculate centered position (assuming AlignCenter)
        x = (self.width() - metrics.horizontalAdvance(self.text())) / 2
        y = (self.height() + metrics.ascent() - metrics.descent()) / 2

        path = QPainterPath()
        path.addText(x, y, self.font(), self.text())

        # Draw Stroke
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
