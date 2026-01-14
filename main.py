import asyncio
import sys

import qasync
import syncedlyrics
import winsdk.windows.media.control as wmc
from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

# --- Backend Logic ---


class SpotifyReader(QObject):
    # Signals to update UI from async loop
    track_changed = pyqtSignal(str, str)  # title, artist
    progress_updated = pyqtSignal(int, int)  # current_ms, duration_ms
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

        # Get Timeline (Progress)
        timeline = self.current_session.get_timeline_properties()
        if timeline:
            position = timeline.position.total_seconds() * 1000
            duration = timeline.end_time.total_seconds() * 1000
            self.progress_updated.emit(int(position), int(duration))

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
    def __init__(self):
        super().__init__()

        # Window Setup
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # Does not appear in taskbar
            | Qt.WindowType.WindowTransparentForInput  # Click-through!
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Geometry
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.width() // 2 - 400, screen.height() - 200, 800, 150)

        # Layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Styling
        self.setStyleSheet("QLabel { color: white; }")

        # Widgets
        self.status_label = QLabel("KaraokeBird Starting...")
        self.status_label.setStyleSheet(
            "font-size: 12px; color: #AAAAAA; background-color: rgba(0,0,0,100); padding: 4px; border-radius: 4px;"
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.prev_line = QLabel("")
        self.prev_line.setFont(QFont("Segoe UI", 14))
        self.prev_line.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        self.prev_line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.curr_line = QLabel("Waiting for music...")
        self.curr_line.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.curr_line.setStyleSheet(
            "color: #1DB954; text-shadow: 2px 2px 4px #000000;"
        )  # Spotify Green
        self.curr_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.curr_line.setWordWrap(True)

        self.next_line = QLabel("")
        self.next_line.setFont(QFont("Segoe UI", 14))
        self.next_line.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        self.next_line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.status_label)
        layout.addWidget(self.prev_line)
        layout.addWidget(self.curr_line)
        layout.addWidget(self.next_line)
        self.setLayout(layout)

        self.lyrics_data = []
        self.current_lyric_index = -1

    def update_status(self, msg):
        self.status_label.setText(msg)
        self.status_label.adjustSize()

    def on_lyrics_found(self, data):
        self.lyrics_data = data
        self.current_lyric_index = -1
        if not data:
            self.curr_line.setText("No synced lyrics found")
            self.prev_line.setText("")
            self.next_line.setText("")
        else:
            self.curr_line.setText("Lyrics loaded!")

    def on_progress(self, current_ms, duration_ms):
        if not self.lyrics_data:
            return

        # Find current line
        # We look for the last line that has a start time <= current_ms
        active_index = -1
        for i, line in enumerate(self.lyrics_data):
            if line["time"] <= current_ms:
                active_index = i
            else:
                break

        if active_index != self.current_lyric_index:
            self.current_lyric_index = active_index
            self.update_display(active_index)

    def update_display(self, index):
        if index < 0:
            self.prev_line.setText("")
            self.curr_line.setText("...")  # Intro
            self.next_line.setText(
                self.lyrics_data[0]["text"] if self.lyrics_data else ""
            )
            return

        prev_text = self.lyrics_data[index - 1]["text"] if index > 0 else ""
        curr_text = self.lyrics_data[index]["text"]
        next_text = (
            self.lyrics_data[index + 1]["text"]
            if index < len(self.lyrics_data) - 1
            else ""
        )

        self.prev_line.setText(prev_text)
        self.curr_line.setText(curr_text)
        self.next_line.setText(next_text)


# --- Main Entry ---


async def main_loop(reader):
    await reader.setup()
    while True:
        await reader.poll_status()
        await asyncio.sleep(0.5)  # Poll frequency


def main():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = OverlayWindow()
    window.show()

    reader = SpotifyReader()

    # Connect signals
    reader.status_message.connect(window.update_status)
    reader.track_changed.connect(
        lambda t, a: window.update_status(f"Searching: {t} - {a}")
    )
    reader.lyrics_found.connect(window.on_lyrics_found)
    reader.progress_updated.connect(window.on_progress)

    with loop:
        loop.create_task(main_loop(reader))
        loop.run_forever()


if __name__ == "__main__":
    main()
