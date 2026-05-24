<p align="center">
  <img src="KaraokeBirdLogo.png" width="200" alt="KaraokeBird Logo" />
</p>

<h1 align="center">
  KaraokeBird
</h1>

<p align="center">
  The lightweight, transparent lyrics overlay for Windows.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows-blue" alt="Platform Windows">
  <img src="https://img.shields.io/badge/python-3.11+-yellow" alt="Python Version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

**KaraokeBird** is a minimal, open-source lyrics visualizer that lives on your desktop. It detects what you are playing on Spotify (or any media player) and displays time-synced lyrics in a beautiful, transparent overlay that sits on top of your windows—letting you sing along while you work, game, or browse.

# 🚀 Features

KaraokeBird is designed to be seamless and unobtrusive.

🎤 **Real-Time Sync:**: Automatically fetches `.lrc` files to display lyrics exactly when they are sung.

👻 **Zero-Interruption Overlay**: The window uses a click-through window and is fully transparent to input. You can click, type, and interact with windows behind the lyrics as if they weren't there.

🎧 **Privacy-First & Portable**: No account creation, no API keys, and no data collection. Works with **Spotify**, **YouTube Music**, **Apple Music**, and browser media players via Windows Media Controls.

🎨 **Fully Customizable**:
*   **Typography**: Custom fonts, stroke weights, and highlight colors.
*   **Layout**: Drag a slider to move the lyrics to the top, bottom, or middle of your screen.
*   **Animations**: Enable gentle cross-fades for a smoother visual experience.
*   **Context Lines**: Choose to see previous/next lines or keep it minimal with just the current line.

⚡ **Instant Setup**: No logins, no API keys, and no complex configuration required. Just run and sing.

# 🎥 Demo

<p align="center">
  <video controls width="720" playsinline>
    <source src="https://private-user-images.githubusercontent.com/146133452/597360661-7de47ea9-ecd5-44c2-93eb-7076c5e81366.mp4?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3Nzk2NTk0NDUsIm5iZiI6MTc3OTY1OTE0NSwicGF0aCI6Ii8xNDYxMzM0NTIvNTk3MzYwNjYxLTdkZTQ3ZWE5LWVjZDUtNDRjMi05M2ViLTcwNzZjNWU4MTM2Ni5tcDQ_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjYwNTI0JTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI2MDUyNFQyMTQ1NDVaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT02OGQ4NzAzMTdkNGJiOGRiMzU3M2ZlNzJlNzY1MjIwYjM5MWJmNmZhZTg1M2YwMmZkN2JhMzRhMGQ0ODE5OTJhJlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCZyZXNwb25zZS1jb250ZW50LXR5cGU9dmlkZW8lMkZtcDQifQ.r-0Loq00IUqII2WT0iJpyoNk0xajBiZcepQwzwZrhNk" type="video/mp4">
    Your browser does not support the video tag. You can watch the demo directly here: <a href="https://private-user-images.githubusercontent.com/146133452/597360661-7de47ea9-ecd5-44c2-93eb-7076c5e81366.mp4?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3Nzk2NTk0NDUsIm5iZiI6MTc3OTY1OTE0NSwicGF0aCI6Ii8xNDYxMzM0NTIvNTk3MzYwNjYxLTdkZTQ3ZWE5LWVjZDUtNDRjMi05M2ViLTcwNzZjNWU4MTM2Ni5tcDQ_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjYwNTI0JTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI2MDUyNFQyMTQ1NDVaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT02OGQ4NzAzMTdkNGJiOGRiMzU3M2ZlNzJlNzY1MjIwYjM5MWJmNmZhZTg1M2YwMmZkN2JhMzRhMGQ0ODE5OTJhJlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCZyZXNwb25zZS1jb250ZW50LXR5cGU9dmlkZW8lMkZtcDQifQ.r-0Loq00IUqII2WT0iJpyoNk0xajBiZcepQwzwZrhNk">direct link</a>.
  </video>
</p>

See it in action: [Watch the demo on X / Twitter](https://twitter.com/joshshiman/status/2011283617134329988)

# 💻 Installation & Usage

### Prerequisites
*   Windows 10 or 11
*   Python 3.11 or higher

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/karaokebird.git
    cd karaokebird
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the app:**
    ```bash
    python main.py
    ```

4.  **Play music!** Start a song on Spotify or your preferred player. The lyrics will appear automatically.

# ⚙️ Configuration

Look for the **KaraokeBird icon** (green square or bird logo) in your system tray (near the clock).

*   **Right-click** the icon and select **Settings...** to open the configuration menu.
*   **Sync Offset**: If lyrics are appearing too early or too late, adjust the offset slider in settings to fix the timing.

# 🛠️ How it Works

Unlike traditional lyrics apps that require a dedicated window, KaraokeBird uses the WinSDK to "listen" to your system's media bus. It then uses the syncedlyrics engine to scrape the most accurate timing data available, rendering it via a high-performance PyQt6 transparent layer.

*   **[PyQt6](https://pypi.org/project/PyQt6/)**: For the robust, transparent GUI and overlay capabilities.
*   **[winsdk](https://pypi.org/project/winsdk/)**: To interface directly with Windows Media Controls for metadata and timeline tracking.
*   **[syncedlyrics](https://github.com/moehuri/syncedlyrics)**: To scour the web for accurate time-synced lyrics.

# 🤝 Contributions

KaraokeBird is an open-source project, and contributions are welcome!

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

# 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
