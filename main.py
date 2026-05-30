import asyncio
import os
import sys
import time
import webbrowser

import keyboard
import qasync
import syncedlyrics
import winsdk.windows.media.control as wmc
from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QLabel,
    QMenu,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from settings_ui import (
    SettingsDialog,
    SettingsManager,
    compute_overlay_geometry,
    get_track_info_gap,
    get_track_info_height,
    get_track_info_width,
)
from ui_components import StrokedLabel

# --- Backend Logic ---


class SpotifyReader(QObject):
    # Signals to update UI from async loop
    track_changed = pyqtSignal(str, str)  # title, artist
    # is_playing, current_ms, duration_ms, capture_time_ms
    playback_sync = pyqtSignal(bool, int, int, float)
    lyrics_found = pyqtSignal(list)  # list of (time_ms, text)
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.manager = None
        self.current_session = None
        self.current_track_id = None
        self.lyrics_cache = {}

    async def setup(self):
        try:
            self.manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
            self.status_message.emit("Connected to Windows Media Controls")
        except Exception as e:
            self.status_message.emit(f"Error connecting to Windows: {e}")

    async def poll_status(self):
        if not self.manager:
            return

        self.current_session = self.manager.get_current_session()
        if not self.current_session:
            self.status_message.emit("Waiting for media...")
            return

        # Get Timeline & Playback Status
        try:
            timeline = self.current_session.get_timeline_properties()
            playback_info = self.current_session.get_playback_info()
            # Capture timestamps as close to the call as possible
            capture_time = time.perf_counter() * 1000
            sys_now_ms = time.time() * 1000

            if timeline and playback_info:
                raw_position_ms = timeline.position.total_seconds() * 1000

                # Handle varying SMTC timestamp formats
                try:
                    last_update_dt = timeline.last_updated_time
                    if hasattr(last_update_dt, "timestamp"):
                        last_update_ms = last_update_dt.timestamp() * 1000
                    else:
                        last_update_ms = last_update_dt.to_datetime().timestamp() * 1000
                except (AttributeError, ValueError, Exception):
                    last_update_ms = sys_now_ms

                elapsed_since_update = sys_now_ms - last_update_ms

                # Determine playback state before applying the elapsed correction.
                is_playing = (
                    playback_info.playback_status
                    == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING
                )

                # Apply correction for the time passed since the media player last updated
                # its position. Only correct when actually playing — when paused, the raw
                # position is already the correct frozen value and adding elapsed time would
                # cause the lyrics to drift forward while the song is stopped.
                if is_playing and 0 <= elapsed_since_update < 10000:
                    position = raw_position_ms + elapsed_since_update
                else:
                    position = raw_position_ms

                duration = timeline.end_time.total_seconds() * 1000
                self.playback_sync.emit(
                    is_playing, int(position), int(duration), capture_time
                )
        except Exception as e:
            print(f"Error polling SMTC: {e}")

        # Get Metadata (Title/Artist)
        try:
            props = await self.current_session.try_get_media_properties_async()
            title = props.title
            artist = props.artist

            # Simple ID generation to detect change
            track_id = f"{title} - {artist}"

            if track_id != self.current_track_id and title:
                self.current_track_id = track_id
                self.track_changed.emit(title, artist)

                # Fetch lyrics in background
                asyncio.create_task(self.fetch_lyrics(title, artist))

        except Exception as e:
            print(f"Error reading metadata: {e}")

    async def fetch_lyrics(self, title, artist):
        search_term = f"{title} {artist}"
        print(f"Searching lyrics for: {search_term}")

        try:
            # syncedlyrics provides LRC string. We run it in a thread to avoid blocking GUI/Async loop
            lrc_str = await asyncio.to_thread(syncedlyrics.search, search_term)

            if lrc_str:
                parsed = self.parse_lrc(lrc_str)
                self.lyrics_found.emit(parsed)
            else:
                self.lyrics_found.emit([])  # No lyrics found
                self.status_message.emit("No synced lyrics found.")
        except Exception as e:
            print(f"Lyrics fetch error: {e}")
            self.lyrics_found.emit([])

    def parse_lrc(self, lrc_string):
        """Parses LRC string into [(time_ms, text), ...]"""
        lyrics = []
        for line in lrc_string.split("\n"):
            if not line.strip():
                continue
            # Format: [mm:ss.xx] Lyric text
            try:
                # Find brackets
                start = line.find("[")
                end = line.find("]")
                if start != -1 and end != -1:
                    timestamp = line[start + 1 : end]
                    text = line[end + 1 :].strip()

                    # Parse timestamp
                    parts = timestamp.split(":")
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    total_ms = int((minutes * 60 + seconds) * 1000)

                    lyrics.append({"time": total_ms, "text": text})
            except (ValueError, IndexError):
                continue

        # Sort by time just in case
        lyrics.sort(key=lambda x: x["time"])

        if not lyrics:
            return []

        # Inject "..." for initial song intro if it's long
        processed_lyrics = []
        if lyrics[0]["time"] > 8000:
            processed_lyrics.append({"time": 5000, "text": "..."})

        processed_lyrics.extend(lyrics)
        return processed_lyrics


# --- Frontend GUI ---


def get_target_screen(settings):
    screens = QApplication.screens()
    screen_index = settings.get("screen_index", 0)
    if 0 <= screen_index < len(screens):
        return screens[screen_index]
    return QApplication.primaryScreen()


class OverlayWindow(QWidget):
    visibility_toggled = pyqtSignal()
    visibility_changed = pyqtSignal(bool)

    def __init__(self, settings_manager):
        super().__init__()
        self.visibility_toggled.connect(self.toggle_visibility)
        self.settings_manager = settings_manager
        self.settings = self.settings_manager.settings

        # Window Setup
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # Does not appear in taskbar
            | Qt.WindowType.WindowTransparentForInput  # Click-through!
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Layout container
        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(self.main_layout)

        # Widget placeholders
        self.prev_labels = []
        self.next_labels = []
        self.curr_label = StrokedLabel("Waiting for music...")
        self.curr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.curr_label.setWordWrap(False)

        # Internal State
        self.lyrics_data = []
        self.current_lyric_index = -1
        self.current_title = ""
        self.current_artist = ""

        # Playback state for interpolation
        self.is_playing = False
        self.last_sync_track_time = 0
        self.last_sync_sys_time = 0
        self.duration = 0
        self.system_message_time = 0

        # High-frequency timer for smooth updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(50)  # Update every 50ms (20fps)

        # Apply initial settings
        self.apply_settings()
        self.update_hotkey()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
        self.visibility_changed.emit(self.isVisible())

    def update_hotkey(self):
        try:
            keyboard.unhook_all()
            hotkey = self.settings.get("toggle_hotkey", "")
            if hotkey:
                # Map Qt key names to keyboard library names
                hotkey = (
                    hotkey.replace("Meta", "windows")
                    .replace("Return", "enter")
                    .replace("PgUp", "page up")
                    .replace("PgDown", "page down")
                )
                keyboard.add_hotkey(hotkey, self.visibility_toggled.emit)
        except Exception as e:
            print(f"Error setting hotkey: {e}")

    def apply_settings(self, settings_override=None):
        # Update local settings ref
        if settings_override:
            self.settings = settings_override
        else:
            self.settings = self.settings_manager.settings

        # 1. Geometry / Position
        screen = get_target_screen(self.settings)
        screen_geom = screen.geometry()
        overlay_geom = compute_overlay_geometry(self.settings, screen_geom)
        self.setGeometry(
            overlay_geom["x"],
            overlay_geom["y"],
            overlay_geom["width"],
            overlay_geom["height"],
        )

        # 2. Rebuild Labels
        # Clear existing widgets from layout
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                if child.widget() == self.curr_label:
                    child.widget().setParent(None)  # Detach, don't delete
                else:
                    child.widget().deleteLater()

        self.prev_labels = []
        self.next_labels = []

        num_history = self.settings.get("num_history_lines", 1)
        num_future = self.settings.get("num_future_lines", 1)
        font_family = self.settings["font_family"]

        # --- Previous Lines ---
        for _ in range(num_history):
            l = StrokedLabel("")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setFont(QFont(font_family, self.settings["font_size_normal"]))
            l.setStyleSheet(f"color: {self.settings['normal_color']};")
            l.setStrokeColor(self.settings.get("stroke_color", "#000000"))
            l.setStrokeEnabled(self.settings.get("stroke_enabled_context", True))
            l.enable_animation = self.settings.get("enable_animations", True)
            l.animation_type = self.settings.get("animation_type", "fade")
            self.prev_labels.append(l)
            self.main_layout.addWidget(l)

        # --- Current Line ---
        self.curr_label.setFont(
            QFont(font_family, self.settings["font_size_highlight"], QFont.Weight.Bold)
        )
        self.curr_label.setStyleSheet(f"color: {self.settings['highlight_color']};")
        self.curr_label.setStrokeColor(self.settings.get("stroke_color", "#000000"))
        self.curr_label.setStrokeEnabled(
            self.settings.get("stroke_enabled_highlight", True)
        )
        self.curr_label.enable_animation = self.settings.get("enable_animations", True)
        self.curr_label.animation_type = self.settings.get("animation_type", "fade")

        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(2, 2)
        self.curr_label.setGraphicsEffect(shadow)

        self.main_layout.addWidget(self.curr_label)

        # --- Next Lines ---
        for _ in range(num_future):
            l = StrokedLabel("")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setFont(QFont(font_family, self.settings["font_size_normal"]))
            l.setStyleSheet(f"color: {self.settings['normal_color']};")
            l.setStrokeColor(self.settings.get("stroke_color", "#000000"))
            l.setStrokeEnabled(self.settings.get("stroke_enabled_context", True))
            l.enable_animation = self.settings.get("enable_animations", True)
            l.animation_type = self.settings.get("animation_type", "fade")
            self.next_labels.append(l)
            self.main_layout.addWidget(l)

        # Force refresh of text content
        if self.current_lyric_index != -1:
            self.update_display(self.current_lyric_index)
        elif not self.lyrics_data:
            self.curr_label.setText(
                "Waiting for music..." if not self.lyrics_data else "Lyrics loaded!"
            )
            self.system_message_time = time.time()

        if settings_override is None:
            self.update_hotkey()

    def set_track_info(self, title, artist):
        self.current_title = title
        self.current_artist = artist
        # Reset lyrics and show title immediately
        self.lyrics_data = []
        self.current_lyric_index = -1
        self.update_display(-1)

    def update_status(self, msg):
        # Since we removed the status label to clean up the look, we might just print to console
        # or temporarily show it on the current line if no lyrics are loaded
        if not self.lyrics_data:
            self.system_message_time = time.time()
            self.curr_label.setText(msg)
            # Clear context lines when showing status
            for lbl in self.prev_labels:
                lbl.setText("")
            for lbl in self.next_labels:
                lbl.setText("")

    def on_lyrics_found(self, data):
        self.lyrics_data = data
        if not data:
            self.curr_label.setText("No synced lyrics found")
            for lbl in self.prev_labels:
                lbl.setText("")
            for lbl in self.next_labels:
                lbl.setText("")
        else:
            # Let update_frame determine the correct starting point
            # based on current playback position. We force an update by
            # setting current index to an impossible value.
            self.current_lyric_index = -999
            self.update_frame()

    def on_playback_sync(self, is_playing, position, duration, capture_time):
        if self.is_playing and is_playing:
            # Interpolated time at the moment of capture
            expected = self.last_sync_track_time + (
                capture_time - self.last_sync_sys_time
            )
            diff = position - expected

            # STRETCHED MONOTONIC SYNC:
            # 1. Large Jump (abs(diff) > 2000ms): Assume Seek/Skip. Snap instantly.
            if abs(diff) > 2000:
                self.last_sync_track_time = position
                self.last_sync_sys_time = capture_time
            # 2. Forward Drift: If we are behind the music by > 150ms, snap forward.
            elif diff > 150:
                self.last_sync_track_time = position
                self.last_sync_sys_time = capture_time
            # 3. Backward Drift: If the reported time is behind our expectation,
            # we ignore it unless it's a huge jump. This prevents "stuttering"
            # where lyrics jump back and then forward again due to jitter.
        else:
            # Not playing or just starting -> Snap to reported position
            self.last_sync_track_time = position
            self.last_sync_sys_time = capture_time

        self.is_playing = is_playing
        self.duration = duration
        self.update_frame()

    def update_frame(self):
        if not self.lyrics_data:
            # Fade out system messages after 5 seconds
            if (
                self.system_message_time > 0
                and time.time() - self.system_message_time > 5
            ):
                if self.curr_label.text():
                    self.curr_label.setText("")
            return

        # Calculate interpolated time
        current_time = self.last_sync_track_time
        if self.is_playing:
            now = time.perf_counter() * 1000
            delta = now - self.last_sync_sys_time
            current_time += delta

        # Apply sync offset
        current_time += self.settings.get("sync_offset_ms", 0)

        # Find current line
        # We look for the last line that has a start time <= current_time
        active_index = -1
        for i, line in enumerate(self.lyrics_data):
            if line["time"] <= current_time:
                active_index = i
            else:
                break

        if active_index != self.current_lyric_index:
            self.current_lyric_index = active_index
            self.update_display(active_index)
        elif active_index < 0 and self.system_message_time > 0:
            # Fade out system messages after 5 seconds
            if time.time() - self.system_message_time > 5:
                if self.curr_label.text():
                    self.curr_label.setText("")

    def get_line_text(self, index, is_context=False):
        """
        is_context=True means this is for a previous/next label.
        """
        if 0 <= index < len(self.lyrics_data):
            return self.lyrics_data[index]["text"]

        # If it's a context label (prev/next), don't show system messages
        if is_context:
            return ""

        # Main label (index < 0) system messages
        if index == -1:
            if self.settings.get("track_info_enabled", False):
                return ""
            if not self.current_title:
                return ""
            if self.current_artist:
                return f"Now Playing: {self.current_title} — {self.current_artist}"
            return f"Now Playing: {self.current_title}"
        elif index == -2:
            return "Lyrics loaded!"
        return ""

    def update_display(self, index):
        # index is the index of the CURRENT line in self.lyrics_data
        if index < 0:
            self.system_message_time = time.time()
        else:
            self.system_message_time = 0

        # 1. Update Current
        self.curr_label.setText(self.get_line_text(index, is_context=False))

        # Context labels (previous/next) should be hidden if showing a system message
        # UNLESS that system message is the "..." gap marker (which has index >= 0)
        show_context = index >= 0

        # 2. Update Previous Labels
        num_prev = len(self.prev_labels)
        for i, lbl in enumerate(self.prev_labels):
            offset = i - num_prev
            target_idx = index + offset
            text = (
                self.get_line_text(target_idx, is_context=True) if show_context else ""
            )
            lbl.setText(text)

        # 3. Update Next Labels
        for i, lbl in enumerate(self.next_labels):
            offset = i + 1
            target_idx = index + offset
            text = (
                self.get_line_text(target_idx, is_context=True) if show_context else ""
            )
            lbl.setText(text)


class TrackInfoWindow(QWidget):
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.settings = self.settings_manager.settings
        self.current_title = ""
        self.current_artist = ""
        self.overlay_visible = True

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = StrokedLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.apply_settings()

    def set_track_info(self, title, artist):
        self.current_title = title
        self.current_artist = artist
        self.update_text()

    def update_text(self):
        if self.current_title and self.current_artist:
            text = f"{self.current_title} — {self.current_artist}"
        else:
            text = self.current_title or ""
        self.label.setText(text)

    def update_visibility(self, overlay_visible):
        self.overlay_visible = overlay_visible
        if overlay_visible and self.settings.get("track_info_enabled", False):
            self.show()
        else:
            self.hide()

    def apply_settings(self, settings_override=None, overlay_visible=None):
        if settings_override:
            self.settings = settings_override
        else:
            self.settings = self.settings_manager.settings

        if overlay_visible is not None:
            self.overlay_visible = overlay_visible

        font_family = self.settings.get("font_family", "Century Gothic")
        font_size = self.settings.get("font_size_normal", 14)
        self.label.setFont(QFont(font_family, font_size))
        self.label.setStyleSheet(f"color: {self.settings['normal_color']};")
        self.label.setStrokeColor(self.settings.get("stroke_color", "#000000"))
        self.label.setStrokeEnabled(self.settings.get("stroke_enabled_context", True))

        screen = get_target_screen(self.settings)
        screen_geom = screen.geometry()
        overlay_geom = compute_overlay_geometry(self.settings, screen_geom)

        width = get_track_info_width(screen_geom.width())
        height = get_track_info_height(font_size)
        gap = get_track_info_gap(font_size)

        base_x = overlay_geom["x"] + (overlay_geom["width"] - width) // 2
        base_y = overlay_geom["y"] + (overlay_geom["height"] // 2) - height - gap

        min_x = screen_geom.x()
        max_x = screen_geom.x() + screen_geom.width() - width
        min_y = screen_geom.y()
        max_y = screen_geom.y() + screen_geom.height() - height

        x_offset = self.settings.get("track_info_x_offset", 0)
        y_offset = self.settings.get("track_info_y_offset", 0)

        min_x_offset = min_x - base_x
        max_x_offset = max_x - base_x
        min_y_offset = min_y - base_y
        max_y_offset = max_y - base_y

        x_offset = max(min_x_offset, min(x_offset, max_x_offset))
        y_offset = max(min_y_offset, min(y_offset, max_y_offset))

        x_pos = base_x + x_offset
        y_pos = base_y + y_offset

        self.setGeometry(x_pos, y_pos, width, height)
        self.update_text()
        self.update_visibility(self.overlay_visible)


# --- Main Entry ---


async def main_loop(reader):
    await reader.setup()
    while True:
        await reader.poll_status()
        await asyncio.sleep(0.2)  # Higher poll frequency (5Hz)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def create_tray_icon(app, window, settings_manager, track_info_window=None):
    tray = QSystemTrayIcon(app)

    # Check for custom logo
    logo_path = resource_path("KaraokeBirdLogo.png")
    if os.path.exists(logo_path):
        icon = QIcon(logo_path)
    else:
        # Fallback: Create a simple icon (Green Square)
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#1DB954"))
        icon = QIcon(pixmap)

    tray.setIcon(icon)
    app.setWindowIcon(icon)

    menu = QMenu()

    # Title Action
    title_action = QAction("Karaoke Bird", app)
    title_action.setEnabled(False)
    menu.addAction(title_action)
    menu.addSeparator()

    # Toggle Visibility
    action_toggle = QAction("Show/Hide Overlay", app)
    action_toggle.triggered.connect(window.toggle_visibility)
    menu.addAction(action_toggle)

    # Settings Action
    action_settings = QAction("Settings...", app)

    def show_settings():
        dlg = SettingsDialog(settings_manager)

        # Hook into the dialog's update_preview to trigger live updates on the main window
        original_update_preview = dlg.update_preview

        def live_update_proxy():
            original_update_preview()
            window.apply_settings(settings_override=dlg.temp_settings)
            if track_info_window:
                track_info_window.apply_settings(
                    settings_override=dlg.temp_settings,
                    overlay_visible=window.isVisible(),
                )

        dlg.update_preview = live_update_proxy

        # When settings are accepted/changed (Save), update the overlay permanently
        def apply_saved_settings():
            window.apply_settings()
            if track_info_window:
                track_info_window.apply_settings(overlay_visible=window.isVisible())

        dlg.settings_changed.connect(lambda s: apply_saved_settings())

        if not dlg.exec():
            # If Cancelled, revert to original settings
            window.apply_settings()
            if track_info_window:
                track_info_window.apply_settings(overlay_visible=window.isVisible())

    action_settings.triggered.connect(show_settings)
    menu.addAction(action_settings)

    # Check for Updates
    action_updates = QAction("Check for Updates...", app)
    action_updates.triggered.connect(
        lambda: webbrowser.open("https://github.com/joshshiman/karaokebird/releases")
    )
    menu.addAction(action_updates)

    menu.addSeparator()

    # Exit Action
    action_exit = QAction("Exit KaraokeBird", app)
    action_exit.triggered.connect(app.quit)
    menu.addAction(action_exit)

    tray.setContextMenu(menu)
    tray.show()
    return tray


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running for tray

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    settings_manager = SettingsManager()

    window = OverlayWindow(settings_manager)
    window.show()

    track_info_window = TrackInfoWindow(settings_manager)
    window.visibility_changed.connect(track_info_window.update_visibility)
    track_info_window.update_visibility(window.isVisible())

    # Create tray icon
    tray = create_tray_icon(app, window, settings_manager, track_info_window)

    reader = SpotifyReader()

    # Connect signals
    reader.status_message.connect(window.update_status)
    reader.track_changed.connect(window.set_track_info)
    reader.track_changed.connect(track_info_window.set_track_info)
    reader.lyrics_found.connect(window.on_lyrics_found)
    reader.playback_sync.connect(window.on_playback_sync)

    with loop:
        loop.create_task(main_loop(reader))
        loop.run_forever()


if __name__ == "__main__":
    main()
