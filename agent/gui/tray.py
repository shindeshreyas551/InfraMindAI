"""
System Tray Manager for InfraMind AI Windows Agent.
Renders taskbar system tray icon using pystray and Pillow with interactive menu.
"""

import sys
import webbrowser
import threading
from typing import Callable, Optional

try:
    import pystray  # type: ignore
    from PIL import Image, ImageDraw  # type: ignore
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


def _create_tray_icon_image(color="indigo") -> "Image.Image":
    """Generate a high-DPI 64x64 icon for Windows System Tray."""
    width, height = 64, 64
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Draw rounded shield background
    bg_color = (99, 102, 241, 255) if color == "indigo" else (239, 68, 68, 255) if color == "red" else (100, 116, 139, 255)
    draw.rounded_rectangle([4, 4, 60, 60], radius=16, fill=bg_color)

    # Draw inner shield symbol (letter 'M')
    draw.polygon([(16, 20), (32, 44), (48, 20), (40, 20), (32, 32), (24, 20)], fill=(255, 255, 255, 255))
    return image


class AgentSystemTray:
    """Manages taskbar system tray icon and interactive menu."""

    def __init__(
        self,
        dashboard_url: str = "http://localhost:3000/dashboard",
        on_pause: Optional[Callable[[], None]] = None,
        on_resume: Optional[Callable[[], None]] = None,
        on_restart: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
    ):
        self.dashboard_url = dashboard_url
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_restart = on_restart
        self.on_exit = on_exit

        self.is_paused = False
        self.icon: Optional["pystray.Icon"] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the system tray icon in a dedicated daemon thread."""
        if not HAS_TRAY:
            return

        self._thread = threading.Thread(target=self._run_tray, daemon=True, name="SystemTrayThread")
        self._thread.start()

    def _run_tray(self) -> None:
        try:
            image = _create_tray_icon_image("indigo")
            menu = pystray.Menu(
                pystray.MenuItem("🛡️ InfraMind Agent v0.3", None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("🌐 Open Dashboard", self._open_dashboard),
                pystray.MenuItem(
                    lambda item: "▶️ Resume Monitoring" if self.is_paused else "⏸️ Pause Monitoring",
                    self._toggle_pause,
                ),
                pystray.MenuItem("🔄 Restart Agent", self._restart),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ Exit Agent", self._exit),
            )

            self.icon = pystray.Icon(
                "InfraMindAgent",
                image,
                "InfraMind AI Endpoint Monitoring Agent",
                menu,
            )
            self.icon.run()
        except Exception:
            pass

    def _open_dashboard(self, icon=None, item=None) -> None:
        webbrowser.open(self.dashboard_url)

    def _toggle_pause(self, icon=None, item=None) -> None:
        self.is_paused = not self.is_paused
        if self.icon:
            color = "gray" if self.is_paused else "indigo"
            self.icon.icon = _create_tray_icon_image(color)

        if self.is_paused and self.on_pause:
            self.on_pause()
        elif not self.is_paused and self.on_resume:
            self.on_resume()

    def _restart(self, icon=None, item=None) -> None:
        if self.on_restart:
            self.on_restart()

    def _exit(self, icon=None, item=None) -> None:
        if self.icon:
            self.icon.stop()
        if self.on_exit:
            self.on_exit()
        sys.exit(0)

    def stop(self) -> None:
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
