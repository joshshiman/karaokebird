import json
import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
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

OVERLAY_WIDTH = 1200
OVERLAY_HEIGHT = 400


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def get_track_info_height(font_size):
    return max(60, int(font_size * 3))


def get_track_info_width(screen_width):
    return min(screen_width, max(OVERLAY_WIDTH, int(screen_width * 0.9)))


def get_track_info_gap(font_size):
    return max(6, int(font_size * 0.5))


def compute_overlay_geometry(settings, screen_geom):
    width = OVERLAY_WIDTH
    height = OVERLAY_HEIGHT

    extra_y = height // 2
    min_y_offset = -extra_y
    max_y_offset = screen_geom.height() - height + extra_y
    y_offset = clamp(settings.get("window_y_offset", 0), min_y_offset, max_y_offset)
    base_y = screen_geom.y() + (screen_geom.height() - height)
    y_pos = base_y - y_offset

    max_x_offset = max(0, (screen_geom.width() - width) // 2)
    x_offset = clamp(settings.get("window_x_offset", 0), -max_x_offset, max_x_offset)

    center_x = screen_geom.x() + (screen_geom.width() - width) // 2
    x_pos = center_x + x_offset

    min_x = screen_geom.x()
    max_x = screen_geom.x() + screen_geom.width() - width
    if max_x < min_x:
        x_pos = center_x
    else:
        x_pos = clamp(x_pos, min_x, max_x)

    return {
        "x": x_pos,
        "y": y_pos,
        "width": width,
        "height": height,
        "min_y_offset": min_y_offset,
        "max_y_offset": max_y_offset,
    }


DEFAULT_SETTINGS = {
    "highlight_color": "#ffff00",
    "stroke_color": "#000000",
    "normal_color": "#ebebeb",
    "background_color": "rgba(0, 0, 0, 100)",
    "font_family": "Century Gothic",
    "font_size_highlight": 24,
    "font_size_normal": 14,
    "window_y_offset": 0,
    "window_x_offset": 0,
    "screen_index": 0,
    "num_history_lines": 0,
    "num_future_lines": 1,
    "sync_offset_ms": 0,
    "enable_animations": False,
    "animation_type": "fade",
    "stroke_enabled_highlight": True,
    "stroke_enabled_context": False,
    "toggle_hotkey": "",
    "track_info_enabled": False,
    "track_info_x_offset": 0,
    "track_info_y_offset": 0,
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

        self.check_anim = QCheckBox("Enable Transitions")
        self.check_anim.setChecked(self.temp_settings.get("enable_animations", True))
        self.check_anim.toggled.connect(
            lambda v: self.update_setting("enable_animations", v)
        )
        color_layout.addRow("Visuals:", self.check_anim)
        color_layout.addRow(
            QLabel("<small>Apply smooth motion when the lyric line changes.</small>")
        )

        self.combo_anim_type = QComboBox()
        self.combo_anim_type.addItems(["fade", "slide", "zoom"])
        self.combo_anim_type.setCurrentText(
            self.temp_settings.get("animation_type", "fade")
        )
        self.combo_anim_type.currentTextChanged.connect(
            lambda v: self.update_setting("animation_type", v)
        )
        color_layout.addRow("Effect Style:", self.combo_anim_type)

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

        screen_layout = QFormLayout()
        self.screen_combo = QComboBox()
        screens = QApplication.screens()
        for i, screen in enumerate(screens):
            geometry = screen.geometry()
            name = screen.name() or f"Display {i + 1}"
            self.screen_combo.addItem(
                f"{name} ({geometry.width()}x{geometry.height()})", i
            )

        screen_index = self.temp_settings.get("screen_index", 0)
        if 0 <= screen_index < self.screen_combo.count():
            self.screen_combo.setCurrentIndex(screen_index)
        self.screen_combo.currentIndexChanged.connect(self.update_screen_selection)
        screen_layout.addRow("Display:", self.screen_combo)
        pos_layout.addLayout(screen_layout)

        # Vertical Position
        y_layout = QHBoxLayout()
        self.slider_offset_y = QSlider(Qt.Orientation.Horizontal)
        self.slider_offset_y.setValue(self.temp_settings["window_y_offset"])
        self.slider_offset_y.valueChanged.connect(
            lambda v: self.update_setting("window_y_offset", v)
        )

        self.spin_offset_y = QSpinBox()
        self.spin_offset_y.setValue(self.temp_settings["window_y_offset"])
        self.spin_offset_y.valueChanged.connect(
            lambda v: self.update_setting("window_y_offset", v)
        )

        self.slider_offset_y.valueChanged.connect(self.spin_offset_y.setValue)
        self.spin_offset_y.valueChanged.connect(self.slider_offset_y.setValue)

        y_layout.addWidget(QLabel("Screen Bottom"))
        y_layout.addWidget(self.slider_offset_y)
        y_layout.addWidget(QLabel("Screen Top"))
        y_layout.addWidget(self.spin_offset_y)

        pos_layout.addLayout(y_layout)
        pos_layout.addWidget(
            QLabel(
                "<small>Adjust the vertical height. Negative values push lower.</small>"
            )
        )

        # Horizontal Position
        x_layout = QHBoxLayout()
        self.slider_offset_x = QSlider(Qt.Orientation.Horizontal)
        self.slider_offset_x.setValue(self.temp_settings.get("window_x_offset", 0))
        self.slider_offset_x.valueChanged.connect(
            lambda v: self.update_setting("window_x_offset", v)
        )

        self.spin_offset_x = QSpinBox()
        self.spin_offset_x.setValue(self.temp_settings.get("window_x_offset", 0))
        self.spin_offset_x.valueChanged.connect(
            lambda v: self.update_setting("window_x_offset", v)
        )

        self.slider_offset_x.valueChanged.connect(self.spin_offset_x.setValue)
        self.spin_offset_x.valueChanged.connect(self.slider_offset_x.setValue)

        x_layout.addWidget(QLabel("Screen Left"))
        x_layout.addWidget(self.slider_offset_x)
        x_layout.addWidget(QLabel("Screen Right"))
        x_layout.addWidget(self.spin_offset_x)

        pos_layout.addLayout(x_layout)
        pos_layout.addWidget(
            QLabel("<small>Adjust the horizontal position. 0 = center.</small>")
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
        ctx_layout.addRow(
            QLabel(
                "<small>Number of previous lines to keep visible above the current one.</small>"
            )
        )

        self.spin_future = QSpinBox()
        self.spin_future.setRange(0, 5)
        self.spin_future.setValue(self.temp_settings.get("num_future_lines", 1))
        self.spin_future.valueChanged.connect(
            lambda v: self.update_setting("num_future_lines", v)
        )
        ctx_layout.addRow("Upcoming Lines:", self.spin_future)
        ctx_layout.addRow(
            QLabel(
                "<small>Number of future lines to show ahead of time below the current one.</small>"
            )
        )

        ctx_group.setLayout(ctx_layout)
        layout.addWidget(ctx_group)

        # Track Info Group
        track_group = QGroupBox("Track Info")
        track_layout = QVBoxLayout()

        self.check_track_info = QCheckBox("Show song and artist permanently")
        self.check_track_info.setChecked(
            self.temp_settings.get("track_info_enabled", False)
        )
        self.check_track_info.toggled.connect(
            lambda v: self.update_setting("track_info_enabled", v)
        )
        track_layout.addWidget(self.check_track_info)

        track_x_layout = QHBoxLayout()
        self.slider_track_x = QSlider(Qt.Orientation.Horizontal)
        self.slider_track_x.setValue(self.temp_settings.get("track_info_x_offset", 0))
        self.slider_track_x.valueChanged.connect(
            lambda v: self.update_setting("track_info_x_offset", v)
        )

        self.spin_track_x = QSpinBox()
        self.spin_track_x.setValue(self.temp_settings.get("track_info_x_offset", 0))
        self.spin_track_x.valueChanged.connect(
            lambda v: self.update_setting("track_info_x_offset", v)
        )

        self.slider_track_x.valueChanged.connect(self.spin_track_x.setValue)
        self.spin_track_x.valueChanged.connect(self.slider_track_x.setValue)

        track_x_layout.addWidget(QLabel("Left"))
        track_x_layout.addWidget(self.slider_track_x)
        track_x_layout.addWidget(QLabel("Right"))
        track_x_layout.addWidget(self.spin_track_x)
        track_layout.addLayout(track_x_layout)

        track_y_layout = QHBoxLayout()
        self.slider_track_y = QSlider(Qt.Orientation.Horizontal)
        self.slider_track_y.setValue(self.temp_settings.get("track_info_y_offset", 0))
        self.slider_track_y.valueChanged.connect(
            lambda v: self.update_setting("track_info_y_offset", v)
        )

        self.spin_track_y = QSpinBox()
        self.spin_track_y.setValue(self.temp_settings.get("track_info_y_offset", 0))
        self.spin_track_y.valueChanged.connect(
            lambda v: self.update_setting("track_info_y_offset", v)
        )

        self.slider_track_y.valueChanged.connect(self.spin_track_y.setValue)
        self.spin_track_y.valueChanged.connect(self.slider_track_y.setValue)

        track_y_layout.addWidget(QLabel("Top"))
        track_y_layout.addWidget(self.slider_track_y)
        track_y_layout.addWidget(QLabel("Bottom"))
        track_y_layout.addWidget(self.spin_track_y)
        track_layout.addLayout(track_y_layout)

        track_layout.addWidget(
            QLabel("<small>Offsets are relative to the lyrics overlay.</small>")
        )

        track_group.setLayout(track_layout)
        layout.addWidget(track_group)

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
        self.update_position_bounds()
        context_font = QFont(
            self.temp_settings["font_family"], self.temp_settings["font_size_normal"]
        )
        context_color = self.temp_settings["normal_color"]
        stroke_color = self.temp_settings.get("stroke_color", "#000000")
        anim_type = self.temp_settings.get("animation_type", "fade")

        num_history = self.temp_settings.get("num_history_lines", 0)
        num_future = self.temp_settings.get("num_future_lines", 1)

        # Update History Preview
        self.preview_prev.setFont(context_font)
        self.preview_prev.setStyleSheet(f"color: {context_color};")
        self.preview_prev.setStrokeColor(stroke_color)
        self.preview_prev.setStrokeEnabled(
            self.temp_settings.get("stroke_enabled_context", True)
        )
        self.preview_prev.animation_type = anim_type
        self.preview_prev.setVisible(num_history > 0)

        # Update Future Preview
        self.preview_next.setFont(context_font)
        self.preview_next.setStyleSheet(f"color: {context_color};")
        self.preview_next.setStrokeColor(stroke_color)
        self.preview_next.setStrokeEnabled(
            self.temp_settings.get("stroke_enabled_context", True)
        )
        self.preview_next.animation_type = anim_type
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
        self.preview_label.animation_type = anim_type

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
        self.combo_anim_type.setCurrentText(
            self.temp_settings.get("animation_type", "fade")
        )

        # Layout
        self.spin_history.setValue(self.temp_settings.get("num_history_lines", 1))
        self.spin_future.setValue(self.temp_settings.get("num_future_lines", 1))
        self.check_stroke_high.setChecked(
            self.temp_settings.get("stroke_enabled_highlight", True)
        )
        self.check_stroke_context.setChecked(
            self.temp_settings.get("stroke_enabled_context", True)
        )
        if 0 <= self.temp_settings.get("screen_index", 0) < self.screen_combo.count():
            self.screen_combo.setCurrentIndex(self.temp_settings.get("screen_index", 0))
        self.slider_offset_y.setValue(self.temp_settings["window_y_offset"])
        self.slider_offset_x.setValue(self.temp_settings.get("window_x_offset", 0))
        self.check_track_info.setChecked(
            self.temp_settings.get("track_info_enabled", False)
        )
        self.slider_track_x.setValue(self.temp_settings.get("track_info_x_offset", 0))
        self.slider_track_y.setValue(self.temp_settings.get("track_info_y_offset", 0))

        self.update_position_bounds()

        # System
        self.spin_sync.setValue(self.temp_settings.get("sync_offset_ms", 0) / 1000.0)
        hotkey = self.temp_settings.get("toggle_hotkey", "")
        self.hotkey_edit.setKeySequence(QKeySequence(hotkey))

        self.update_preview()

    def get_selected_screen_geometry(self):
        screens = QApplication.screens()
        screen_index = self.temp_settings.get("screen_index", 0)
        if 0 <= screen_index < len(screens):
            return screens[screen_index].geometry()
        return QApplication.primaryScreen().geometry()

    def update_screen_selection(self, index):
        self.temp_settings["screen_index"] = index
        self.update_position_bounds()

    def update_position_bounds(self):
        if not hasattr(self, "slider_offset_y"):
            return

        screen_geom = self.get_selected_screen_geometry()
        overlay_geom = compute_overlay_geometry(self.temp_settings, screen_geom)
        min_y_offset = overlay_geom["min_y_offset"]
        max_y_offset = overlay_geom["max_y_offset"]
        max_x_offset = max(0, (screen_geom.width() - OVERLAY_WIDTH) // 2)

        y_value = clamp(
            self.temp_settings.get("window_y_offset", 0), min_y_offset, max_y_offset
        )
        x_value = clamp(
            self.temp_settings.get("window_x_offset", 0), -max_x_offset, max_x_offset
        )

        self.slider_offset_y.blockSignals(True)
        self.spin_offset_y.blockSignals(True)
        self.slider_offset_x.blockSignals(True)
        self.spin_offset_x.blockSignals(True)

        self.slider_offset_y.setRange(min_y_offset, max_y_offset)
        self.spin_offset_y.setRange(min_y_offset, max_y_offset)
        self.slider_offset_x.setRange(-max_x_offset, max_x_offset)
        self.spin_offset_x.setRange(-max_x_offset, max_x_offset)

        self.slider_offset_y.setValue(y_value)
        self.spin_offset_y.setValue(y_value)
        self.slider_offset_x.setValue(x_value)
        self.spin_offset_x.setValue(x_value)

        self.slider_offset_y.blockSignals(False)
        self.spin_offset_y.blockSignals(False)
        self.slider_offset_x.blockSignals(False)
        self.spin_offset_x.blockSignals(False)

        self.temp_settings["window_y_offset"] = y_value
        self.temp_settings["window_x_offset"] = x_value

        font_size = self.temp_settings.get("font_size_normal", 14)
        track_height = get_track_info_height(font_size)
        track_width = get_track_info_width(screen_geom.width())
        track_gap = get_track_info_gap(font_size)

        base_x = overlay_geom["x"] + (overlay_geom["width"] - track_width) // 2
        base_y = (
            overlay_geom["y"] + (overlay_geom["height"] // 2) - track_height - track_gap
        )

        min_track_x = screen_geom.x() - base_x
        max_track_x = screen_geom.x() + screen_geom.width() - track_width - base_x
        min_track_y = screen_geom.y() - base_y
        max_track_y = screen_geom.y() + screen_geom.height() - track_height - base_y

        track_x_value = clamp(
            self.temp_settings.get("track_info_x_offset", 0),
            min_track_x,
            max_track_x,
        )
        track_y_value = clamp(
            self.temp_settings.get("track_info_y_offset", 0),
            min_track_y,
            max_track_y,
        )

        self.slider_track_x.blockSignals(True)
        self.spin_track_x.blockSignals(True)
        self.slider_track_y.blockSignals(True)
        self.spin_track_y.blockSignals(True)

        self.slider_track_x.setRange(min_track_x, max_track_x)
        self.spin_track_x.setRange(min_track_x, max_track_x)
        self.slider_track_y.setRange(min_track_y, max_track_y)
        self.spin_track_y.setRange(min_track_y, max_track_y)

        self.slider_track_x.setValue(track_x_value)
        self.spin_track_x.setValue(track_x_value)
        self.slider_track_y.setValue(track_y_value)
        self.spin_track_y.setValue(track_y_value)

        self.slider_track_x.blockSignals(False)
        self.spin_track_x.blockSignals(False)
        self.slider_track_y.blockSignals(False)
        self.spin_track_y.blockSignals(False)

        self.temp_settings["track_info_x_offset"] = track_x_value
        self.temp_settings["track_info_y_offset"] = track_y_value

    def accept(self):
        self.manager.settings = self.temp_settings
        self.manager.save()
        self.settings_changed.emit(self.manager.settings)
        super().accept()
