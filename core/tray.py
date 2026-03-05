"""
GUNA-ASTRA System Tray Icon
Shows a tray icon in the Windows taskbar with menu options.
"""

import os
import sys
import threading
import webbrowser
from utils.logger import get_logger
from config.settings import API_PORT

logger = get_logger("Tray")


def create_tray_icon(orchestrator=None, on_quit=None):
    """Create and run the system tray icon. Blocks the calling thread."""
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("pystray or Pillow not installed. Tray icon disabled.")
        logger.warning("Install with: py -m pip install pystray Pillow")
        return

    # Generate a simple icon programmatically (blue "G" on dark background)
    def _create_icon_image():
        img = Image.new("RGBA", (64, 64), (20, 20, 30, 255))
        draw = ImageDraw.Draw(img)
        # Draw a cyan "G" circle
        draw.ellipse([8, 8, 56, 56], outline=(0, 220, 255, 255), width=3)
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except Exception:
            font = ImageFont.load_default()
        draw.text((18, 10), "G", fill=(0, 220, 255, 255), font=font)
        return img

    def _open_console(icon, item):
        """Open a new terminal with GUNA-ASTRA CLI."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.system(f'start cmd /k "cd /d {script_dir} && py main.py"')

    def _open_api(icon, item):
        """Open API docs in browser."""
        webbrowser.open(f"http://127.0.0.1:{API_PORT}/docs")

    def _show_status(icon, item):
        """Show status notification."""
        mode = orchestrator.current_mode if orchestrator else "unknown"
        icon.notify(
            f"Mode: {mode.upper()}\n"
            f"Conversation: {len(orchestrator._conversation) if orchestrator else 0} msgs",
            "GUNA-ASTRA Status"
        )

    def _switch_normal(icon, item):
        if orchestrator:
            orchestrator.current_mode = "normal"
            icon.notify("Switched to Normal Mode ⚡", "GUNA-ASTRA")

    def _switch_working(icon, item):
        if orchestrator:
            orchestrator.current_mode = "working"
            icon.notify("Switched to Working Mode 🧠", "GUNA-ASTRA")

    def _quit(icon, item):
        icon.stop()
        if on_quit:
            on_quit()

    menu = pystray.Menu(
        pystray.MenuItem("🖥️  Open Console", _open_console),
        pystray.MenuItem("🌐  Open API Docs", _open_api),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("⚡ Normal Mode", _switch_normal),
        pystray.MenuItem("🧠 Working Mode", _switch_working),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("📊  Status", _show_status),
        pystray.MenuItem("❌  Quit GUNA-ASTRA", _quit),
    )

    icon = pystray.Icon(
        name="GUNA-ASTRA",
        icon=_create_icon_image(),
        title="GUNA-ASTRA — AI Assistant (Running)",
        menu=menu
    )

    logger.info("System tray icon active.")
    icon.run()


def run_tray_in_background(orchestrator=None, on_quit=None):
    """Start the tray icon in a background thread."""
    thread = threading.Thread(
        target=create_tray_icon,
        args=(orchestrator, on_quit),
        daemon=True
    )
    thread.start()
    return thread
