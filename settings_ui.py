import json
import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFontComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "highlight_color": "#1DB954",  # Spotify Green
    "stroke_color": "#000000",
    "normal_color": "#FFFFFF",
    "background_color": "rgba(0, 0, 0, 100)",  # Semi-transparent black
    "font_family": "Segoe UI",
    "font_size_highlight": 24,
    "font_size_normal": 14,
    "window_y_offset": 250,  # From bottom
    "num_preview_lines": 1,
}


class SettingsManager:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"Error loading settings: {e}")

    def save(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key):
        return self.settings.get(key, DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.settings[key] = value


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.manager = settings_manager
        self.temp_settings = self.manager.settings.copy()
        self.setWindowTitle("KaraokeBird Settings")
        self.setFixedWidth(400)

        # Keep window on top so it's not lost behind the overlay
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout()

        form_layout = QFormLayout()

        # Font
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self.temp_settings["font_family"]))
        self.font_combo.currentFontChanged.connect(self.update_font)
        form_layout.addRow("Font Family:", self.font_combo)

        # Highlight Font Size
        self.spin_size_high = QSpinBox()
        self.spin_size_high.setRange(8, 72)
        self.spin_size_high.setValue(self.temp_settings["font_size_highlight"])
        self.spin_size_high.valueChanged.connect(
            lambda v: self.update_setting("font_size_highlight", v)
        )
        form_layout.addRow("Highlight Size:", self.spin_size_high)

        # Normal Font Size
        self.spin_size_norm = QSpinBox()
        self.spin_size_norm.setRange(8, 72)
        self.spin_size_norm.setValue(self.temp_settings["font_size_normal"])
        self.spin_size_norm.valueChanged.connect(
            lambda v: self.update_setting("font_size_normal", v)
        )
        form_layout.addRow("Normal Size:", self.spin_size_norm)

        # Colors
        self.btn_color_high = QPushButton("Choose...")
        self.btn_color_high.setStyleSheet(
            f"background-color: {self.temp_settings['highlight_color']}"
        )
        self.btn_color_high.clicked.connect(
            lambda: self.pick_color("highlight_color", self.btn_color_high)
        )
        form_layout.addRow("Highlight Color:", self.btn_color_high)

        self.btn_color_stroke = QPushButton("Choose...")
        self.btn_color_stroke.setStyleSheet(
            f"background-color: {self.temp_settings.get('stroke_color', '#000000')}"
        )
        self.btn_color_stroke.clicked.connect(
            lambda: self.pick_color("stroke_color", self.btn_color_stroke)
        )
        form_layout.addRow("Stroke Color:", self.btn_color_stroke)

        self.btn_color_norm = QPushButton("Choose...")
        self.btn_color_norm.setStyleSheet(
            f"background-color: {self.temp_settings['normal_color']}"
        )
        self.btn_color_norm.clicked.connect(
            lambda: self.pick_color("normal_color", self.btn_color_norm)
        )
        form_layout.addRow("Normal Color:", self.btn_color_norm)

        # Layout / Position
        self.spin_lines = QSpinBox()
        self.spin_lines.setRange(0, 5)
        self.spin_lines.setValue(self.temp_settings["num_preview_lines"])
        self.spin_lines.valueChanged.connect(
            lambda v: self.update_setting("num_preview_lines", v)
        )
        form_layout.addRow("Context Lines:", self.spin_lines)

        self.spin_offset = QSpinBox()
        self.spin_offset.setRange(0, 2000)
        self.spin_offset.setSingleStep(10)
        self.spin_offset.setValue(self.temp_settings["window_y_offset"])
        self.spin_offset.valueChanged.connect(
            lambda v: self.update_setting("window_y_offset", v)
        )
        form_layout.addRow("Bottom Offset (px):", self.spin_offset)

        layout.addLayout(form_layout)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            self.reset_defaults
        )
        layout.addWidget(buttons)

        self.setLayout(layout)

    def update_setting(self, key, value):
        self.temp_settings[key] = value

    def update_font(self, font):
        self.temp_settings["font_family"] = font.family()

    def pick_color(self, key, button):
        color = QColorDialog.getColor(
            QColor(self.temp_settings[key]), self, "Select Color"
        )
        if color.isValid():
            hex_color = color.name()
            self.temp_settings[key] = hex_color
            button.setStyleSheet(f"background-color: {hex_color}")

    def reset_defaults(self):
        self.temp_settings = DEFAULT_SETTINGS.copy()

        # Update UI elements
        self.font_combo.setCurrentFont(QFont(self.temp_settings["font_family"]))
        self.spin_size_high.setValue(self.temp_settings["font_size_highlight"])
        self.spin_size_norm.setValue(self.temp_settings["font_size_normal"])

        self.btn_color_high.setStyleSheet(
            f"background-color: {self.temp_settings['highlight_color']}"
        )
        self.btn_color_stroke.setStyleSheet(
            f"background-color: {self.temp_settings['stroke_color']}"
        )
        self.btn_color_norm.setStyleSheet(
            f"background-color: {self.temp_settings['normal_color']}"
        )

        self.spin_lines.setValue(self.temp_settings["num_preview_lines"])
        self.spin_offset.setValue(self.temp_settings["window_y_offset"])

    def accept(self):
        self.manager.settings = self.temp_settings
        self.manager.save()
        self.settings_changed.emit(self.manager.settings)
        super().accept()
