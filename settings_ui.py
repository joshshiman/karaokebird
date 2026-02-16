import json
import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFontComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui_components import StrokedLabel

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "highlight_color": "#ffff00",
    "stroke_color": "#000000",
    "normal_color": "#ebebeb",
    "background_color": "rgba(0, 0, 0, 100)",
    "font_family": "Century Gothic",
    "font_size_highlight": 24,
    "font_size_normal": 14,
    "window_y_offset": 0,
    "num_history_lines": 0,
    "num_future_lines": 1,
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
        self.setFixedWidth(450)

        # Keep window on top
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        main_layout = QVBoxLayout()

        # --- Preview Section (Always Visible) ---
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet(
            f"background-color: {self.temp_settings.get('background_color', '#000000')}; border-radius: 8px;"
        )
        self.preview_frame.setMinimumHeight(140)

        preview_layout = QVBoxLayout()
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview_prev = StrokedLabel("Previous Lyric Line")
        self.preview_prev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_prev)

        self.preview_label = StrokedLabel("Current Active Lyric")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_label)

        self.preview_next = StrokedLabel("Upcoming Lyric Line")
        self.preview_next.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_next)

        self.preview_frame.setLayout(preview_layout)
        main_layout.addWidget(QLabel("<b>Live Preview:</b>"))
        main_layout.addWidget(self.preview_frame)
        main_layout.addSpacing(10)

        # --- Tabbed Categories ---
        self.tabs = QTabWidget()

        self.tabs.addTab(self.create_appearance_tab(), "Appearance")
        self.tabs.addTab(self.create_layout_tab(), "Layout")
        self.tabs.addTab(self.create_system_tab(), "System")

        main_layout.addWidget(self.tabs)

        # --- Buttons ---
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
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)
        self.update_preview()

    def create_appearance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Text Style Group
        font_group = QGroupBox("Typography")
        font_layout = QFormLayout()

        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self.temp_settings["font_family"]))
        self.font_combo.currentFontChanged.connect(self.update_font)
        font_layout.addRow("Font Family:", self.font_combo)

        self.spin_size_high = QSpinBox()
        self.spin_size_high.setRange(8, 72)
        self.spin_size_high.setValue(self.temp_settings["font_size_highlight"])
        self.spin_size_high.valueChanged.connect(
            lambda v: self.update_setting("font_size_highlight", v)
        )
        font_layout.addRow("Highlight Size:", self.spin_size_high)

        self.spin_size_norm = QSpinBox()
        self.spin_size_norm.setRange(8, 72)
        self.spin_size_norm.setValue(self.temp_settings["font_size_normal"])
        self.spin_size_norm.valueChanged.connect(
            lambda v: self.update_setting("font_size_normal", v)
        )
        font_layout.addRow("Context Size:", self.spin_size_norm)

        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        # Colors & Effects Group
        color_group = QGroupBox("Colors & Visuals")
        color_layout = QFormLayout()

        self.btn_color_high = QPushButton("Choose...")
        self.btn_color_high.setFixedWidth(100)
        self.btn_color_high.setStyleSheet(
            f"background-color: {self.temp_settings['highlight_color']}"
        )
        self.btn_color_high.clicked.connect(
            lambda: self.pick_color("highlight_color", self.btn_color_high)
        )
        color_layout.addRow("Highlight Color:", self.btn_color_high)

        self.btn_color_norm = QPushButton("Choose...")
        self.btn_color_norm.setFixedWidth(100)
        self.btn_color_norm.setStyleSheet(
            f"background-color: {self.temp_settings['normal_color']}"
        )
        self.btn_color_norm.clicked.connect(
            lambda: self.pick_color("normal_color", self.btn_color_norm)
        )
        color_layout.addRow("Context Color:", self.btn_color_norm)

        self.btn_color_stroke = QPushButton("Choose...")
        self.btn_color_stroke.setFixedWidth(100)
        self.btn_color_stroke.setStyleSheet(
            f"background-color: {self.temp_settings.get('stroke_color', '#000000')}"
        )
        self.btn_color_stroke.clicked.connect(
            lambda: self.pick_color("stroke_color", self.btn_color_stroke)
        )
        color_layout.addRow("Stroke Color:", self.btn_color_stroke)

        self.check_anim = QCheckBox("Smooth Cross-fades")
        self.check_anim.setChecked(self.temp_settings.get("enable_animations", True))
        self.check_anim.toggled.connect(
            lambda v: self.update_setting("enable_animations", v)
        )
        color_layout.addRow("Animations:", self.check_anim)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_layout_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Position Group
        pos_group = QGroupBox("Screen Position")
        pos_layout = QVBoxLayout()

        # Get screen height to bound the slider dynamically
        screen = QApplication.primaryScreen().availableGeometry()
        max_height = screen.height()

        h_layout = QHBoxLayout()
        self.slider_offset = QSlider(Qt.Orientation.Horizontal)
        self.slider_offset.setRange(0, max_height)
        self.slider_offset.setValue(self.temp_settings["window_y_offset"])
        self.slider_offset.valueChanged.connect(
            lambda v: self.update_setting("window_y_offset", v)
        )

        self.spin_offset = QSpinBox()
        self.spin_offset.setRange(0, max_height)
        self.spin_offset.setValue(self.temp_settings["window_y_offset"])
        self.spin_offset.valueChanged.connect(
            lambda v: self.update_setting("window_y_offset", v)
        )

        self.slider_offset.valueChanged.connect(self.spin_offset.setValue)
        self.spin_offset.valueChanged.connect(self.slider_offset.setValue)

        h_layout.addWidget(QLabel("Screen Bottom"))
        h_layout.addWidget(self.slider_offset)
        h_layout.addWidget(QLabel("Screen Top"))
        h_layout.addWidget(self.spin_offset)

        pos_layout.addLayout(h_layout)
        pos_layout.addWidget(
            QLabel("<small>Adjust the vertical height of the lyrics overlay.</small>")
        )
        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)

        # Context Group
        ctx_group = QGroupBox("Lyric Lines")
        ctx_layout = QFormLayout()

        self.spin_history = QSpinBox()
        self.spin_history.setRange(0, 5)
        self.spin_history.setValue(self.temp_settings.get("num_history_lines", 1))
        self.spin_history.valueChanged.connect(
            lambda v: self.update_setting("num_history_lines", v)
        )
        ctx_layout.addRow("History Lines:", self.spin_history)

        self.spin_future = QSpinBox()
        self.spin_future.setRange(0, 5)
        self.spin_future.setValue(self.temp_settings.get("num_future_lines", 1))
        self.spin_future.valueChanged.connect(
            lambda v: self.update_setting("num_future_lines", v)
        )
        ctx_layout.addRow("Upcoming Lines:", self.spin_future)

        ctx_group.setLayout(ctx_layout)
        layout.addWidget(ctx_group)

        # Stroke Toggle Group
        stroke_group = QGroupBox("Stroke/Outline Toggles")
        stroke_layout = QHBoxLayout()

        self.check_stroke_high = QCheckBox("On Highlight")
        self.check_stroke_high.setChecked(
            self.temp_settings.get("stroke_enabled_highlight", True)
        )
        self.check_stroke_high.toggled.connect(
            lambda v: self.update_setting("stroke_enabled_highlight", v)
        )

        self.check_stroke_context = QCheckBox("On Context")
        self.check_stroke_context.setChecked(
            self.temp_settings.get("stroke_enabled_context", True)
        )
        self.check_stroke_context.toggled.connect(
            lambda v: self.update_setting("stroke_enabled_context", v)
        )

        stroke_layout.addWidget(self.check_stroke_high)
        stroke_layout.addWidget(self.check_stroke_context)
        stroke_group.setLayout(stroke_layout)
        layout.addWidget(stroke_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_system_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Sync Group
        sync_group = QGroupBox("Timing & Sync")
        sync_layout = QFormLayout()

        self.spin_sync = QDoubleSpinBox()
        self.spin_sync.setRange(-10.0, 10.0)
        self.spin_sync.setSingleStep(0.1)
        self.spin_sync.setValue(self.temp_settings.get("sync_offset_ms", 0) / 1000.0)
        self.spin_sync.valueChanged.connect(
            lambda v: self.update_setting("sync_offset_ms", int(v * 1000))
        )
        sync_layout.addRow("Sync Offset (sec):", self.spin_sync)
        sync_layout.addRow(
            QLabel("<small>Use this if lyrics are consistently early or late.</small>")
        )

        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)

        # Controls Group
        ctrl_group = QGroupBox("Controls")
        ctrl_layout = QFormLayout()

        self.hotkey_edit = QKeySequenceEdit()
        current_hotkey = self.temp_settings.get("toggle_hotkey", "")
        if current_hotkey:
            self.hotkey_edit.setKeySequence(QKeySequence(current_hotkey))
        self.hotkey_edit.keySequenceChanged.connect(self.update_hotkey)

        ctrl_layout.addRow("Toggle Overlay Hotkey:", self.hotkey_edit)
        ctrl_layout.addRow(
            QLabel(
                "<small>Click and press a key combination (e.g., Ctrl+L) to hide/show.</small>"
            )
        )

        ctrl_group.setLayout(ctrl_layout)
        layout.addWidget(ctrl_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def update_preview(self):
        context_font = QFont(
            self.temp_settings["font_family"], self.temp_settings["font_size_normal"]
        )
        context_color = self.temp_settings["normal_color"]
        stroke_color = self.temp_settings.get("stroke_color", "#000000")

        num_history = self.temp_settings.get("num_history_lines", 1)
        num_future = self.temp_settings.get("num_future_lines", 1)

        # Update History Preview
        self.preview_prev.setFont(context_font)
        self.preview_prev.setStyleSheet(f"color: {context_color};")
        self.preview_prev.setStrokeColor(stroke_color)
        self.preview_prev.setStrokeEnabled(
            self.temp_settings.get("stroke_enabled_context", True)
        )
        self.preview_prev.setVisible(num_history > 0)

        # Update Future Preview
        self.preview_next.setFont(context_font)
        self.preview_next.setStyleSheet(f"color: {context_color};")
        self.preview_next.setStrokeColor(stroke_color)
        self.preview_next.setStrokeEnabled(
            self.temp_settings.get("stroke_enabled_context", True)
        )
        self.preview_next.setVisible(num_future > 0)

        # Update Highlight Preview
        font = QFont(
            self.temp_settings["font_family"],
            self.temp_settings["font_size_highlight"],
            QFont.Weight.Bold,
        )
        self.preview_label.setFont(font)
        self.preview_label.setStyleSheet(
            f"color: {self.temp_settings['highlight_color']};"
        )
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

        # Appearance
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
        self.check_anim.setChecked(self.temp_settings.get("enable_animations", True))

        # Layout
        self.spin_history.setValue(self.temp_settings.get("num_history_lines", 1))
        self.spin_future.setValue(self.temp_settings.get("num_future_lines", 1))
        self.check_stroke_high.setChecked(
            self.temp_settings.get("stroke_enabled_highlight", True)
        )
        self.check_stroke_context.setChecked(
            self.temp_settings.get("stroke_enabled_context", True)
        )
        self.slider_offset.setValue(self.temp_settings["window_y_offset"])

        # System
        self.spin_sync.setValue(self.temp_settings.get("sync_offset_ms", 0) / 1000.0)
        hotkey = self.temp_settings.get("toggle_hotkey", "")
        self.hotkey_edit.setKeySequence(QKeySequence(hotkey))

        self.update_preview()

    def accept(self):
        self.manager.settings = self.temp_settings
        self.manager.save()
        self.settings_changed.emit(self.manager.settings)
        super().accept()
