import asyncio
import os
import sys
import time

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

from settings_ui import SettingsDialog, SettingsManager
from ui_components import StrokedLabel

# --- Backend Logic ---


class SpotifyReader(QObject):
    # Signals to update UI from async loop
    track_changed = pyqtSignal(str, str)  # title, artist
    # is_playing, current_ms, duration_ms
    playback_sync = pyqtSignal(bool, int, int)
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
        timeline = self.current_session.get_timeline_properties()
        playback_info = self.current_session.get_playback_info()

        if timeline and playback_info:
            position = timeline.position.total_seconds() * 1000
            duration = timeline.end_time.total_seconds() * 1000
            is_playing = (
                playback_info.playback_status
                == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING
            )
            self.playback_sync.emit(is_playing, int(position), int(duration))

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
                self.status_message.emit(f"Playing: {title}")

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
            except Exception:
                continue

        # Sort by time just in case
        lyrics.sort(key=lambda x: x["time"])
        return lyrics


# --- Frontend GUI ---


class OverlayWindow(QWidget):
    def __init__(self, settings_manager):
        super().__init__()
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

        # Playback state for interpolation
        self.is_playing = False
        self.last_sync_track_time = 0
        self.last_sync_sys_time = 0
        self.duration = 0

        # High-frequency timer for smooth updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(50)  # Update every 50ms (20fps)

        # Apply initial settings
        self.apply_settings()

    def apply_settings(self, settings_override=None):
        # Update local settings ref
        if settings_override:
            self.settings = settings_override
        else:
            self.settings = self.settings_manager.settings

        # 1. Geometry / Position
        screen = QApplication.primaryScreen().geometry()
        width = 1200
        height = 400
        # Position from bottom based on offset
        y_pos = screen.height() - self.settings["window_y_offset"] - (height // 2)
        # Ensure it doesn't go off screen bottom if offset is small
        if y_pos > screen.height() - height:
            y_pos = screen.height() - height

        self.setGeometry(screen.width() // 2 - (width // 2), y_pos, width, height)

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

        num_lines = self.settings["num_preview_lines"]
        font_family = self.settings["font_family"]

        # --- Previous Lines ---
        for _ in range(num_lines):
            l = QLabel("")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setFont(QFont(font_family, self.settings["font_size_normal"]))
            l.setStyleSheet(f"color: {self.settings['normal_color']};")
            self.prev_labels.append(l)
            self.main_layout.addWidget(l)

        # --- Current Line ---
        self.curr_label.setFont(
            QFont(font_family, self.settings["font_size_highlight"], QFont.Weight.Bold)
        )
        self.curr_label.setStyleSheet(f"color: {self.settings['highlight_color']};")
        self.curr_label.setStrokeColor(self.settings.get("stroke_color", "#000000"))

        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(2, 2)
        self.curr_label.setGraphicsEffect(shadow)

        self.main_layout.addWidget(self.curr_label)

        # --- Next Lines ---
        for _ in range(num_lines):
            l = QLabel("")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setFont(QFont(font_family, self.settings["font_size_normal"]))
            l.setStyleSheet(f"color: {self.settings['normal_color']};")
            self.next_labels.append(l)
            self.main_layout.addWidget(l)

        # Force refresh of text content
        if self.current_lyric_index != -1:
            self.update_display(self.current_lyric_index)
        elif not self.lyrics_data:
            self.curr_label.setText(
                "Waiting for music..." if not self.lyrics_data else "Lyrics loaded!"
            )

    def update_status(self, msg):
        # Since we removed the status label to clean up the look, we might just print to console
        # or temporarily show it on the current line if no lyrics are loaded
        if not self.lyrics_data:
            self.curr_label.setText(msg)

    def on_lyrics_found(self, data):
        self.lyrics_data = data
        self.current_lyric_index = -1
        if not data:
            self.curr_label.setText("No synced lyrics found")
            for l in self.prev_labels:
                l.setText("")
            for l in self.next_labels:
                l.setText("")
        else:
            self.curr_label.setText("Lyrics loaded!")

    def on_playback_sync(self, is_playing, position, duration):
        now = time.time() * 1000

        if self.is_playing and is_playing:
            # Interpolated time right now
            expected = self.last_sync_track_time + (now - self.last_sync_sys_time)
            diff = position - expected

            # STRICT MONOTONIC SYNC:
            # 1. Large Jump (abs(diff) > 2000ms): Assume Seek/Skip. Snap instantly.
            # 2. Forward Drift (diff > 0): We are lagging behind Windows. Catch up.
            # 3. Backward Drift (diff < 0): Windows sent stale time. IGNORE update.

            if abs(diff) > 2000 or diff > 0:
                self.last_sync_track_time = position
                self.last_sync_sys_time = now
            # else: diff < 0 (Stale poll). Do nothing, keep extrapolating from old anchor.
        else:
            # Not playing or just starting -> Snap to reported position
            self.last_sync_track_time = position
            self.last_sync_sys_time = now

        self.is_playing = is_playing
        self.duration = duration
        self.update_frame()

    def update_frame(self):
        if not self.lyrics_data:
            return

        # Calculate interpolated time
        current_time = self.last_sync_track_time
        if self.is_playing:
            now = time.time() * 1000
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

    def update_display(self, index):
        # index is the index of the CURRENT line in self.lyrics_data

        # 1. Update Current
        if 0 <= index < len(self.lyrics_data):
            self.curr_label.setText(self.lyrics_data[index]["text"])
        else:
            self.curr_label.setText("..." if index < 0 else "")

        # 2. Update Previous Labels
        # self.prev_labels[0] is the top-most (furthest back).
        # self.prev_labels[-1] is right above current.
        num_prev = len(self.prev_labels)
        for i, lbl in enumerate(self.prev_labels):
            # i=0 (top) -> if num_prev=2 -> offset = -2
            # i=1 (bottom) -> if num_prev=2 -> offset = -1
            offset = i - num_prev
            target_idx = index + offset

            if 0 <= target_idx < len(self.lyrics_data):
                lbl.setText(self.lyrics_data[target_idx]["text"])
            else:
                lbl.setText("")

        # 3. Update Next Labels
        # self.next_labels[0] is right below current.
        for i, lbl in enumerate(self.next_labels):
            offset = i + 1
            target_idx = index + offset

            if 0 <= target_idx < len(self.lyrics_data):
                lbl.setText(self.lyrics_data[target_idx]["text"])
            else:
                lbl.setText("")


# --- Main Entry ---


async def main_loop(reader):
    await reader.setup()
    while True:
        await reader.poll_status()
        await asyncio.sleep(0.5)  # Poll frequency


def create_tray_icon(app, window, settings_manager):
    tray = QSystemTrayIcon(app)

    # Check for custom logo
    if os.path.exists("KaraokeBirdLogo.png"):
        icon = QIcon("KaraokeBirdLogo.png")
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

    # Settings Action
    action_settings = QAction("Settings...", app)

    def show_settings():
        dlg = SettingsDialog(settings_manager)

        # Hook into the dialog's update_preview to trigger live updates on the main window
        original_update_preview = dlg.update_preview

        def live_update_proxy():
            original_update_preview()
            window.apply_settings(settings_override=dlg.temp_settings)

        dlg.update_preview = live_update_proxy

        # When settings are accepted/changed (Save), update the overlay permanently
        dlg.settings_changed.connect(lambda s: window.apply_settings())

        if not dlg.exec():
            # If Cancelled, revert to original settings
            window.apply_settings()

    action_settings.triggered.connect(show_settings)
    menu.addAction(action_settings)

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

    # Create tray icon
    tray = create_tray_icon(app, window, settings_manager)

    reader = SpotifyReader()

    # Connect signals
    reader.status_message.connect(window.update_status)
    reader.track_changed.connect(
        lambda t, a: window.update_status(f"Searching: {t} - {a}")
    )
    reader.lyrics_found.connect(window.on_lyrics_found)
    reader.playback_sync.connect(window.on_playback_sync)

    with loop:
        loop.create_task(main_loop(reader))
        loop.run_forever()


if __name__ == "__main__":
    main()
