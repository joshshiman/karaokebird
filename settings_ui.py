import json
import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFontComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from ui_components import StrokedLabel

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "highlight_color": "#ffff00",
    "stroke_color": "#000000",
    "normal_color": "#ebebeb",
    "background_color": "rgba(0, 0, 0, 100)",  # Semi-transparent black
    "font_family": "Century Gothic",
    "font_size_highlight": 24,
    "font_size_normal": 14,
    "window_y_offset": 300,
    "num_preview_lines": 1,
    "sync_offset_ms": 0,
    "enable_animations": False,
    "stroke_enabled_highlight": True,
    "stroke_enabled_context": False,
    "toggle_hotkey": "",
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

        # --- Preview Section ---
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet(
            f"background-color: {self.temp_settings.get('background_color', '#000000')}; border-radius: 8px;"
        )
        self.preview_frame.setMinimumHeight(160)

        preview_layout = QVBoxLayout()
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview_prev = StrokedLabel("Previous Context Line")
        self.preview_prev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_prev)

        self.preview_label = StrokedLabel("Live Preview Lyric")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_label)

        self.preview_next = StrokedLabel("Next Context Line")
        self.preview_next.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_next)

        self.preview_frame.setLayout(preview_layout)

        layout.addWidget(QLabel("Preview:"))
        layout.addWidget(self.preview_frame)
        layout.addSpacing(10)

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

        self.check_stroke_high = QCheckBox()
        self.check_stroke_high.setChecked(
            self.temp_settings.get("stroke_enabled_highlight", True)
        )
        self.check_stroke_high.toggled.connect(
            lambda v: self.update_setting("stroke_enabled_highlight", v)
        )
        form_layout.addRow("Highlight Stroke:", self.check_stroke_high)

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
        form_layout.addRow("Context Text Color:", self.btn_color_norm)

        self.check_stroke_context = QCheckBox()
        self.check_stroke_context.setChecked(
            self.temp_settings.get("stroke_enabled_context", True)
        )
        self.check_stroke_context.toggled.connect(
            lambda v: self.update_setting("stroke_enabled_context", v)
        )
        form_layout.addRow("Context Stroke:", self.check_stroke_context)

        # Layout / Position
        self.spin_lines = QSpinBox()
        self.spin_lines.setRange(0, 5)
        self.spin_lines.setValue(self.temp_settings["num_preview_lines"])
        self.spin_lines.valueChanged.connect(
            lambda v: self.update_setting("num_preview_lines", v)
        )
        form_layout.addRow("Context Lines:", self.spin_lines)

        # Vertical Position (Slider + SpinBox)
        self.pos_layout = QHBoxLayout()
        self.slider_offset = QSlider(Qt.Orientation.Horizontal)
        self.slider_offset.setRange(0, 1200)
        self.slider_offset.setValue(self.temp_settings["window_y_offset"])
        self.slider_offset.valueChanged.connect(
            lambda v: self.update_setting("window_y_offset", v)
        )

        self.spin_offset = QSpinBox()
        self.spin_offset.setRange(0, 1200)
        self.spin_offset.setValue(self.temp_settings["window_y_offset"])
        self.spin_offset.valueChanged.connect(
            lambda v: self.update_setting("window_y_offset", v)
        )

        # Sync slider and spinbox
        self.slider_offset.valueChanged.connect(self.spin_offset.setValue)
        self.spin_offset.valueChanged.connect(self.slider_offset.setValue)

        self.pos_layout.addWidget(QLabel("Low"))
        self.pos_layout.addWidget(self.slider_offset)
        self.pos_layout.addWidget(QLabel("High"))
        self.pos_layout.addWidget(self.spin_offset)

        form_layout.addRow("Vertical Position:", self.pos_layout)

        # Sync Offset
        self.spin_sync = QDoubleSpinBox()
        self.spin_sync.setRange(-10.0, 10.0)
        self.spin_sync.setSingleStep(0.1)
        self.spin_sync.setValue(self.temp_settings.get("sync_offset_ms", 0) / 1000.0)
        self.spin_sync.valueChanged.connect(
            lambda v: self.update_setting("sync_offset_ms", int(v * 1000))
        )
        form_layout.addRow("Sync Offset (sec):", self.spin_sync)

        # Animations
        self.check_anim = QCheckBox()
        self.check_anim.setChecked(self.temp_settings.get("enable_animations", True))
        self.check_anim.toggled.connect(
            lambda v: self.update_setting("enable_animations", v)
        )
        form_layout.addRow("Enable Animations:", self.check_anim)

        # Hotkey
        self.hotkey_edit = QKeySequenceEdit()
        current_hotkey = self.temp_settings.get("toggle_hotkey", "")
        if current_hotkey:
            self.hotkey_edit.setKeySequence(QKeySequence(current_hotkey))

        self.hotkey_edit.keySequenceChanged.connect(self.update_hotkey)
        form_layout.addRow("Toggle Hotkey:", self.hotkey_edit)

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
        self.update_preview()

    def update_preview(self):
        # --- Context Style ---
        context_font = QFont(
            self.temp_settings["font_family"],
            self.temp_settings["font_size_normal"],
        )
        context_color = self.temp_settings["normal_color"]
        stroke_color = self.temp_settings.get("stroke_color", "#000000")
        show_context = self.temp_settings["num_preview_lines"] > 0

        self.preview_prev.setFont(context_font)
        self.preview_prev.setStyleSheet(f"color: {context_color};")
        self.preview_prev.setStrokeColor(stroke_color)
        self.preview_prev.setStrokeEnabled(
            self.temp_settings.get("stroke_enabled_context", True)
        )
        self.preview_prev.setVisible(show_context)

        self.preview_next.setFont(context_font)
        self.preview_next.setStyleSheet(f"color: {context_color};")
        self.preview_next.setStrokeColor(stroke_color)
        self.preview_next.setStrokeEnabled(
            self.temp_settings.get("stroke_enabled_context", True)
        )
        self.preview_next.setVisible(show_context)

        # --- Highlight Style ---
        font = QFont(
            self.temp_settings["font_family"],
            self.temp_settings["font_size_highlight"],
            QFont.Weight.Bold,
        )
        self.preview_label.setFont(font)

        text_color = self.temp_settings["highlight_color"]

        self.preview_label.setStyleSheet(f"color: {text_color};")
        self.preview_label.setStrokeColor(stroke_color)
        self.preview_label.setStrokeEnabled(
            self.temp_settings.get("stroke_enabled_highlight", True)
        )

    def update_setting(self, key, value):
        self.temp_settings[key] = value
        self.update_preview()

    def update_hotkey(self, sequence):
        hotkey_str = sequence.toString(QKeySequence.SequenceFormat.PortableText)
        self.temp_settings["toggle_hotkey"] = hotkey_str
        # No preview update needed for hotkey

    def update_font(self, font):
        self.temp_settings["font_family"] = font.family()
        self.update_preview()

    def pick_color(self, key, button):
        color = QColorDialog.getColor(
            QColor(self.temp_settings[key]), self, "Select Color"
        )
        if color.isValid():
            hex_color = color.name()
            self.temp_settings[key] = hex_color
            button.setStyleSheet(f"background-color: {hex_color}")
            self.update_preview()

    def reset_defaults(self):
        self.temp_settings = DEFAULT_SETTINGS.copy()

        # Update UI elements
        self.font_combo.setCurrentFont(QFont(self.temp_settings["font_family"]))
        self.spin_size_high.setValue(self.temp_settings["font_size_highlight"])
        self.spin_size_norm.setValue(self.temp_settings["font_size_normal"])

        self.check_stroke_high.setChecked(
            self.temp_settings["stroke_enabled_highlight"]
        )
        self.check_stroke_context.setChecked(
            self.temp_settings["stroke_enabled_context"]
        )

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
        self.slider_offset.setValue(self.temp_settings["window_y_offset"])
        self.spin_offset.setValue(self.temp_settings["window_y_offset"])
        self.spin_sync.setValue(self.temp_settings.get("sync_offset_ms", 0) / 1000.0)
        self.check_anim.setChecked(self.temp_settings.get("enable_animations", True))

        hotkey = self.temp_settings.get("toggle_hotkey", "")
        self.hotkey_edit.setKeySequence(QKeySequence(hotkey))

        self.update_preview()

    def accept(self):
        self.manager.settings = self.temp_settings
        self.manager.save()
        self.settings_changed.emit(self.manager.settings)
        super().accept()
