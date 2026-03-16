"""
GUNA-ASTRA Computer Controller
Master class for ALL direct OS interactions in Normal Mode.
Platform-aware — wraps system_tools.py with standardized return format.
"""

import difflib
import os
import platform
import shutil
import sys
import time
import webbrowser
from datetime import datetime

import pyautogui

try:
    import pygetwindow as gw
except ImportError:
    gw = None
from utils.logger import get_logger

logger = get_logger("ComputerController")

# ── Platform Detection ─────────────────────────────────────────────────────────

PLATFORM = platform.system()
IS_WINDOWS = PLATFORM == "Windows"
IS_MAC = PLATFORM == "Darwin"
IS_LINUX = PLATFORM == "Linux"


# ── Common Applications List (for fuzzy matching) ──────────────────────────────

COMMON_APPS = [
    "chrome",
    "firefox",
    "safari",
    "edge",
    "opera",
    "notepad",
    "notepad++",
    "vs code",
    "visual studio code",
    "sublime text",
    "atom",
    "spotify",
    "discord",
    "slack",
    "zoom",
    "teams",
    "skype",
    "vlc",
    "winamp",
    "itunes",
    "excel",
    "word",
    "powerpoint",
    "outlook",
    "onenote",
    "paint",
    "photoshop",
    "illustrator",
    "calculator",
    "terminal",
    "cmd",
    "powershell",
    "task manager",
    "file manager",
    "explorer",
    "finder",
    "steam",
    "epic games",
    "origin",
    "battle.net",
    "minecraft",
    "roblox",
    "blender",
    "unity",
    "unreal engine",
    "obs studio",
    "audacity",
    "gimp",
    "inkscape",
    "filezilla",
    "putty",
    "winscp",
    "postman",
]

# ── Path Safety ────────────────────────────────────────────────────────────────

DANGEROUS_PATHS_WIN = ["C:\\Windows", "C:\\Program Files", "C:\\System32"]
DANGEROUS_PATHS_MAC = ["/System", "/Library", "/usr"]
DANGEROUS_PATHS_LINUX = ["/etc", "/sys", "/proc", "/dev", "/bin", "/sbin", "/usr"]


def _result(success: bool, output: str, action: str) -> dict:
    """Standardized result format for all controller methods."""
    return {"success": success, "output": output, "action": action}


def _is_safe_path(path: str) -> bool:
    """Check if a path is safe to operate on."""
    abs_path = (
        os.path.abspath(path).replace("/", "\\")
        if IS_WINDOWS
        else os.path.abspath(path)
    )

    dangerous = (
        DANGEROUS_PATHS_WIN
        if IS_WINDOWS
        else DANGEROUS_PATHS_MAC if IS_MAC else DANGEROUS_PATHS_LINUX
    )

    for dp in dangerous:
        if abs_path.lower().startswith(dp.lower()):
            return False
    return True


class ComputerController:
    """Master class for all direct OS interactions."""

    def __init__(self):
        self.logger = logger
        # Lazy-import system_tools to avoid circular deps
        try:
            from utils import system_tools as st

            self._st = st
        except ImportError:
            self._st = None
            self.logger.warning("system_tools not available.")

    # ── Applications ──────────────────────────────────────────────────────────

    def open_application(self, app_name: str) -> dict:
        """Launch any application by name."""
        try:
            if self._st:
                path = self._st.launch_app(app_name)
                return _result(True, f"✅ Launched: {app_name}", "OPEN_APP")
            # Fallback
            if IS_WINDOWS:
                os.startfile(app_name)
            elif IS_MAC:
                import subprocess

                subprocess.Popen(["open", "-a", app_name])
            else:
                import subprocess

                subprocess.Popen([app_name])
            return _result(True, f"✅ Launched: {app_name}", "OPEN_APP")
        except Exception as e:
            # Try fuzzy match
            suggestions = difflib.get_close_matches(
                app_name.lower(), COMMON_APPS, n=3, cutoff=0.6
            )
            if suggestions:
                msg = f"Could not find '{app_name}'. Did you mean: {', '.join(suggestions)}?"
            else:
                msg = f"Could not find application: '{app_name}'. Error: {e}"
            self.logger.warning(msg)
            return _result(False, f"❌ {msg}", "OPEN_APP")

    # ── Browser / URL ─────────────────────────────────────────────────────────

    def open_url(self, url: str) -> dict:
        """Open a URL in the default browser."""
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            if self._st:
                browser = self._st.open_url(url)
                return _result(True, f"🌐 Opened {url} in {browser}.", "OPEN_URL")
            webbrowser.open(url)
            return _result(True, f"🌐 Opened {url} in default browser.", "OPEN_URL")
        except Exception as e:
            return _result(False, f"❌ Failed to open URL: {e}", "OPEN_URL")

    def play_youtube(self, query: str) -> dict:
        """Search YouTube and open results in browser."""
        try:
            # For "Jarvis" feel, we want to try and play the first result directly
            # A common search-to-watch URL format is not stable, so we open search
            # and then optionally use pyautogui to click the first video if we want to be fancy.
            from urllib.parse import quote_plus

            url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            webbrowser.open(url)

            # Small delay to let browser open, then optional click (experimental)
            # time.sleep(2)
            # pyautogui.click(x=600, y=400) # Highly dependent on resolution

            return _result(True, f"🎵 Playing '{query}' on YouTube.", "PLAY_MUSIC")
        except Exception as e:
            return _result(False, f"❌ Failed to play YouTube: {e}", "PLAY_MUSIC")

    # ── File Operations ───────────────────────────────────────────────────────

    def create_file(self, path: str, content: str = "") -> dict:
        """Create a file at the given path with optional content."""
        try:
            dir_name = os.path.dirname(os.path.abspath(path))
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return _result(
                True, f"📄 File created: {os.path.abspath(path)}", "CREATE_FILE"
            )
        except Exception as e:
            return _result(False, f"❌ Failed to create file: {e}", "CREATE_FILE")

    def create_folder(self, path: str) -> dict:
        """Create a directory (and parent directories)."""
        try:
            os.makedirs(path, exist_ok=True)
            return _result(
                True, f"📁 Folder created: {os.path.abspath(path)}", "CREATE_FOLDER"
            )
        except Exception as e:
            return _result(False, f"❌ Failed to create folder: {e}", "CREATE_FOLDER")

    def delete_file(self, path: str) -> dict:
        """Delete a file (requires user confirmation via orchestrator)."""
        try:
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                return _result(False, f"❌ File not found: {abs_path}", "DELETE_FILE")
            if not _is_safe_path(abs_path):
                return _result(
                    False,
                    f"❌ Cannot delete files in protected directory: {abs_path}",
                    "DELETE_FILE",
                )
            size = os.path.getsize(abs_path)
            os.remove(abs_path)
            return _result(
                True, f"🗑️ Deleted: {abs_path} ({size:,} bytes)", "DELETE_FILE"
            )
        except Exception as e:
            return _result(False, f"❌ Failed to delete: {e}", "DELETE_FILE")

    def delete_folder(self, path: str, recursive: bool = False) -> dict:
        """Delete a folder."""
        try:
            abs_path = os.path.abspath(path)
            if not os.path.isdir(abs_path):
                return _result(
                    False, f"❌ Folder not found: {abs_path}", "DELETE_FOLDER"
                )
            if not _is_safe_path(abs_path):
                return _result(
                    False,
                    f"❌ Cannot delete protected directory: {abs_path}",
                    "DELETE_FOLDER",
                )
            if recursive:
                shutil.rmtree(abs_path)
            else:
                os.rmdir(abs_path)
            return _result(True, f"🗑️ Deleted folder: {abs_path}", "DELETE_FOLDER")
        except Exception as e:
            return _result(False, f"❌ Failed to delete folder: {e}", "DELETE_FOLDER")

    def move_file(self, src: str, dst: str) -> dict:
        """Move a file or folder."""
        try:
            shutil.move(src, dst)
            return _result(True, f"📦 Moved {src} → {dst}", "MOVE_FILE")
        except Exception as e:
            return _result(False, f"❌ Failed to move: {e}", "MOVE_FILE")

    def copy_file(self, src: str, dst: str) -> dict:
        """Copy a file or folder."""
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
                shutil.copy2(src, dst)
            return _result(True, f"📋 Copied {src} → {dst}", "COPY_FILE")
        except Exception as e:
            return _result(False, f"❌ Failed to copy: {e}", "COPY_FILE")

    def rename_file(self, path: str, new_name: str) -> dict:
        """Rename a file."""
        try:
            new_path = os.path.join(os.path.dirname(path), new_name)
            os.rename(path, new_path)
            return _result(
                True,
                f"✏️ Renamed: {os.path.basename(path)} → {new_name}",
                "RENAME_FILE",
            )
        except Exception as e:
            return _result(False, f"❌ Failed to rename: {e}", "RENAME_FILE")

    def list_directory(self, path: str = ".") -> dict:
        """List contents of a directory."""
        try:
            path = os.path.expanduser(path)
            if not os.path.isdir(path):
                return _result(False, f"❌ Not a directory: {path}", "LIST_DIR")

            entries = sorted(os.listdir(path))
            folders = []
            files = []

            for entry in entries:
                full = os.path.join(path, entry)
                try:
                    if os.path.isdir(full):
                        folders.append(f"  📁 {entry}/")
                    else:
                        size = os.path.getsize(full)
                        if size < 1024:
                            sz = f"{size} B"
                        elif size < 1024 * 1024:
                            sz = f"{size / 1024:.1f} KB"
                        else:
                            sz = f"{size / (1024 * 1024):.1f} MB"
                        files.append(f"  📄 {entry} ({sz})")
                except OSError:
                    files.append(f"  ❓ {entry}")

            output_lines = [f"📂 {os.path.abspath(path)}"]
            if folders:
                output_lines.extend(folders)
            if files:
                output_lines.extend(files)
            if not folders and not files:
                output_lines.append("  (empty)")

            output_lines.append(f"\n  {len(folders)} folders, {len(files)} files")
            return _result(True, "\n".join(output_lines), "LIST_DIR")
        except Exception as e:
            return _result(False, f"❌ Failed to list directory: {e}", "LIST_DIR")

    # ── Time / Date ───────────────────────────────────────────────────────────

    def show_datetime(self) -> dict:
        """Show current date and time."""
        try:
            now = datetime.now()
            formatted = now.strftime("%A, %B %d, %Y — %H:%M:%S")
            return _result(True, f"🕐 {formatted}", "SHOW_TIME")
        except Exception as e:
            return _result(False, f"❌ {e}", "SHOW_TIME")

    # ── Volume Control ────────────────────────────────────────────────────────

    def set_volume(self, level: int) -> dict:
        """Set system volume to a specific percentage."""
        try:
            level = max(0, min(100, level))
            if self._st:
                msg = self._st.set_volume(level)
                return _result(True, f"🔊 {msg}", "SET_VOLUME")
            return _result(False, "Volume control not available.", "SET_VOLUME")
        except Exception as e:
            return _result(False, f"❌ Volume control failed: {e}", "SET_VOLUME")

    def volume_up(self, amount: int = 10) -> dict:
        """Increase volume."""
        try:
            steps = max(1, amount // 2)
            if self._st:
                msg = self._st.volume_up(steps)
                return _result(True, f"🔊 {msg}", "VOLUME_UP")
            return _result(False, "Volume control not available.", "VOLUME_UP")
        except Exception as e:
            return _result(False, f"❌ {e}", "VOLUME_UP")

    def volume_down(self, amount: int = 10) -> dict:
        """Decrease volume."""
        try:
            steps = max(1, amount // 2)
            if self._st:
                msg = self._st.volume_down(steps)
                return _result(True, f"🔉 {msg}", "VOLUME_DOWN")
            return _result(False, "Volume control not available.", "VOLUME_DOWN")
        except Exception as e:
            return _result(False, f"❌ {e}", "VOLUME_DOWN")

    def mute_volume(self) -> dict:
        """Toggle mute."""
        try:
            if self._st:
                msg = self._st.mute_volume()
                return _result(True, f"🔇 {msg}", "MUTE_VOLUME")
            return _result(False, "Volume control not available.", "MUTE_VOLUME")
        except Exception as e:
            return _result(False, f"❌ {e}", "MUTE_VOLUME")

    # ── Screenshots ───────────────────────────────────────────────────────────

    def take_screenshot(self, name: str = None) -> dict:
        """Take a screenshot of the current screen."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = name or f"screenshot_{timestamp}.png"

            # Ensure data dir exists
            from config.settings import DATA_DIR

            ss_dir = os.path.join(DATA_DIR, "screenshots")
            os.makedirs(ss_dir, exist_ok=True)

            path = os.path.join(ss_dir, filename)
            pyautogui.screenshot(path)

            return _result(True, f"📸 Screenshot captured: {path}", "TAKE_SCREENSHOT")
        except Exception as e:
            return _result(False, f"❌ Screenshot failed: {e}", "TAKE_SCREENSHOT")

    def get_active_window(self) -> dict:
        """Get the title of the currently focused window."""
        try:
            if not gw:
                return _result(False, "pygetwindow not installed.", "GET_WINDOW")

            window = gw.getActiveWindow()
            if window:
                return _result(True, f"Active Window: {window.title}", "GET_WINDOW")
            return _result(False, "No active window detected.", "GET_WINDOW")
        except Exception as e:
            return _result(False, f"❌ Failed to get window title: {e}", "GET_WINDOW")

    def read_document(self, file_path: str) -> dict:
        """Extract text from a document for GUNA to read aloud."""
        try:
            from utils.doc_reader import extract_text

            text = extract_text(file_path)
            if text:
                # Limit text for speech to first 2000 chars or so to avoid buffer issues
                snippet = text[:2000]
                return _result(True, snippet, "READ_DOC")
            return _result(False, "Could not extract text from document.", "READ_DOC")
        except Exception as e:
            return _result(False, f"❌ Failed to read document: {e}", "READ_DOC")

    # ── System Information ────────────────────────────────────────────────────

    def get_system_info(self) -> dict:
        """Return detailed system information."""
        try:
            info_lines = [f"💻 System Information"]
            info_lines.append(f"  OS: {platform.platform()}")
            info_lines.append(f"  CPU Cores: {os.cpu_count()}")

            try:
                import psutil

                mem = psutil.virtual_memory()
                info_lines.append(
                    f"  RAM: {mem.total / (1024**3):.1f} GB total, "
                    f"{mem.used / (1024**3):.1f} GB used ({mem.percent}%)"
                )

                cpu_pct = psutil.cpu_percent(interval=0.5)
                info_lines.append(f"  CPU Usage: {cpu_pct}%")

                for part in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        info_lines.append(
                            f"  Disk {part.mountpoint}: "
                            f"{usage.total / (1024**3):.1f} GB total, "
                            f"{usage.used / (1024**3):.1f} GB used ({usage.percent}%)"
                        )
                    except (PermissionError, OSError):
                        pass

                if hasattr(psutil, "sensors_battery"):
                    batt = psutil.sensors_battery()
                    if batt:
                        info_lines.append(
                            f"  Battery: {batt.percent}% "
                            f"({'charging' if batt.power_plugged else 'discharging'})"
                        )

                boot = datetime.fromtimestamp(psutil.boot_time())
                uptime = datetime.now() - boot
                hrs = int(uptime.total_seconds() // 3600)
                mins = int((uptime.total_seconds() % 3600) // 60)
                info_lines.append(f"  Uptime: {hrs}h {mins}m")

            except ImportError:
                if self._st:
                    info_lines.append(self._st.get_system_info())
                else:
                    info_lines.append("  (psutil not installed for detailed info)")

            return _result(True, "\n".join(info_lines), "SHOW_SYSTEM_INFO")
        except Exception as e:
            return _result(False, f"❌ System info failed: {e}", "SHOW_SYSTEM_INFO")

    def get_battery_status(self) -> dict:
        """Show battery information."""
        try:
            try:
                import psutil

                batt = psutil.sensors_battery()
                if batt:
                    status = "🔌 Plugged in" if batt.power_plugged else "🔋 On battery"
                    time_left = ""
                    if batt.secsleft > 0 and not batt.power_plugged:
                        hrs = batt.secsleft // 3600
                        mins = (batt.secsleft % 3600) // 60
                        time_left = f" — {hrs}h {mins}m remaining"
                    return _result(
                        True, f"{status}: {batt.percent}%{time_left}", "SHOW_BATTERY"
                    )
                return _result(
                    True, "🔌 No battery detected (desktop PC).", "SHOW_BATTERY"
                )
            except ImportError:
                if self._st:
                    return _result(True, self._st.get_battery_status(), "SHOW_BATTERY")
                return _result(
                    False, "psutil not installed for battery info.", "SHOW_BATTERY"
                )
        except Exception as e:
            return _result(False, f"❌ Battery check failed: {e}", "SHOW_BATTERY")

    # ── Processes ─────────────────────────────────────────────────────────────

    def list_processes(self) -> dict:
        """Show running processes."""
        try:
            try:
                import psutil

                procs = []
                for p in psutil.process_iter(
                    ["pid", "name", "cpu_percent", "memory_percent"]
                ):
                    try:
                        info = p.info
                        procs.append(info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                procs.sort(key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
                lines = [
                    "  PID    | CPU%  | MEM%  | Name",
                    "  -------|-------|-------|----------------",
                ]
                for p in procs[:20]:
                    lines.append(
                        f"  {p.get('pid', '?'):>6} | {p.get('cpu_percent', 0):>5.1f} | "
                        f"{p.get('memory_percent', 0):>5.1f} | {p.get('name', '?')}"
                    )
                return _result(True, "\n".join(lines), "LIST_PROCESSES")
            except ImportError:
                if self._st:
                    return _result(True, self._st.list_processes(), "LIST_PROCESSES")
                return _result(False, "psutil not installed.", "LIST_PROCESSES")
        except Exception as e:
            return _result(False, f"❌ {e}", "LIST_PROCESSES")

    def kill_process(self, name: str) -> dict:
        """Kill a process by name."""
        try:
            if self._st:
                result = self._st.kill_process(name)
                return _result(True, f"💀 {result}", "KILL_PROCESS")
            return _result(False, "Process control not available.", "KILL_PROCESS")
        except Exception as e:
            return _result(False, f"❌ Failed to kill process: {e}", "KILL_PROCESS")

    # ── Search Files ──────────────────────────────────────────────────────────

    def search_files(self, query: str, path: str = None) -> dict:
        """Find files matching a pattern."""
        try:
            root = path or os.path.expanduser("~")
            if self._st:
                found = self._st.search_files(root, query)
                if found:
                    output = f"🔍 Found {len(found)} files:\n" + "\n".join(
                        f"  {f}" for f in found[:30]
                    )
                else:
                    output = f"🔍 No files matching '{query}' found."
                return _result(True, output, "SEARCH_FILES")
            return _result(False, "Search not available.", "SEARCH_FILES")
        except Exception as e:
            return _result(False, f"❌ Search failed: {e}", "SEARCH_FILES")

    # ── Network ───────────────────────────────────────────────────────────────

    def get_network_info(self) -> dict:
        """Show network information."""
        try:
            if self._st:
                info = self._st.network_info()
                return _result(True, f"🌐 Network Info:\n{info}", "SHOW_NETWORK")
            return _result(False, "Network info not available.", "SHOW_NETWORK")
        except Exception as e:
            return _result(False, f"❌ {e}", "SHOW_NETWORK")

    def check_website(self, url: str) -> dict:
        """Check if a website is online."""
        try:
            import requests

            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            start = datetime.now()
            r = requests.head(url, timeout=5, allow_redirects=True)
            elapsed = (datetime.now() - start).total_seconds() * 1000
            return _result(
                True,
                f"🌐 {url} — {'✅ Online' if r.status_code < 400 else '⚠️ Issues'} "
                f"(Status: {r.status_code}, Response: {elapsed:.0f}ms)",
                "CHECK_WEBSITE",
            )
        except Exception as e:
            return _result(
                False, f"❌ {url} appears to be offline: {e}", "CHECK_WEBSITE"
            )

    # ── Weather ───────────────────────────────────────────────────────────────

    def get_weather(self, city: str = None) -> dict:
        """Get current weather."""
        try:
            if self._st:
                result = self._st.get_weather(city or "")
                return _result(True, result, "GET_WEATHER")
            from urllib.parse import quote_plus

            import requests

            if not city:
                try:
                    loc = requests.get("https://ipapi.co/json/", timeout=5).json()
                    city = loc.get("city", "")
                except Exception:
                    city = ""
            url = f"https://wttr.in/{quote_plus(city)}?format=%C+%t+%h+%w&lang=en"
            r = requests.get(url, timeout=10, headers={"User-Agent": "curl/7.0"})
            if r.status_code == 200:
                return _result(
                    True,
                    f"🌤️ Weather{' in ' + city if city else ''}: {r.text.strip()}",
                    "GET_WEATHER",
                )
            return _result(False, "Weather lookup failed.", "GET_WEATHER")
        except Exception as e:
            return _result(False, f"❌ Weather lookup failed: {e}", "GET_WEATHER")

    # ── Trash ─────────────────────────────────────────────────────────────────

    def empty_trash(self) -> dict:
        """Empty the recycle bin / trash."""
        try:
            if self._st:
                result = self._st.empty_recycle_bin()
                return _result(True, result, "EMPTY_TRASH")
            return _result(False, "Trash emptying not available.", "EMPTY_TRASH")
        except Exception as e:
            return _result(False, f"❌ {e}", "EMPTY_TRASH")

    # ── Power ─────────────────────────────────────────────────────────────────

    def lock_screen(self) -> dict:
        """Lock the computer screen."""
        try:
            if IS_WINDOWS:
                import ctypes

                ctypes.windll.user32.LockWorkStation()
            elif self._st:
                self._st.lock_screen()
            return _result(True, "🔒 Screen locked.", "LOCK_SCREEN")
        except Exception as e:
            return _result(False, f"❌ Lock failed: {e}", "LOCK_SCREEN")

    def shutdown_computer(self) -> dict:
        """Shutdown the computer (confirmation handled by orchestrator)."""
        try:
            if self._st:
                result = self._st.shutdown_system(30)
                return _result(True, result, "SHUTDOWN")
            return _result(False, "Shutdown not available.", "SHUTDOWN")
        except Exception as e:
            return _result(False, f"❌ {e}", "SHUTDOWN")

    def restart_computer(self) -> dict:
        """Restart the computer (confirmation handled by orchestrator)."""
        try:
            if self._st:
                result = self._st.restart_system(30)
                return _result(True, result, "RESTART")
            return _result(False, "Restart not available.", "RESTART")
        except Exception as e:
            return _result(False, f"❌ {e}", "RESTART")

    def sleep_computer(self) -> dict:
        """Put computer to sleep."""
        try:
            if self._st:
                result = self._st.sleep_system()
                return _result(True, result, "SLEEP")
            return _result(False, "Sleep not available.", "SLEEP")
        except Exception as e:
            return _result(False, f"❌ {e}", "SLEEP")

    # ── Clipboard ─────────────────────────────────────────────────────────────

    def get_clipboard(self) -> dict:
        """Get current clipboard content."""
        try:
            if self._st:
                content = self._st.get_clipboard()
                return _result(True, f"📋 Clipboard:\n{content}", "GET_CLIPBOARD")
            try:
                import pyperclip

                return _result(
                    True, f"📋 Clipboard:\n{pyperclip.paste()}", "GET_CLIPBOARD"
                )
            except ImportError:
                return _result(
                    False, "Clipboard access not available.", "GET_CLIPBOARD"
                )
        except Exception as e:
            return _result(False, f"❌ {e}", "GET_CLIPBOARD")

    def set_clipboard(self, text: str) -> dict:
        """Copy text to clipboard."""
        try:
            if self._st:
                result = self._st.set_clipboard(text)
                return _result(True, f"📋 {result}", "SET_CLIPBOARD")
            try:
                import pyperclip

                pyperclip.copy(text)
                return _result(
                    True, f"📋 Copied to clipboard: {text[:80]}", "SET_CLIPBOARD"
                )
            except ImportError:
                return _result(
                    False, "Clipboard access not available.", "SET_CLIPBOARD"
                )
        except Exception as e:
            return _result(False, f"❌ {e}", "SET_CLIPBOARD")

    # ── Keyboard / Input ──────────────────────────────────────────────────────

    def type_text(self, text: str) -> dict:
        """Type text into the active window."""
        try:
            if self._st:
                result = self._st.type_text(text)
                return _result(True, f"⌨️ {result}", "TYPE_TEXT")
            try:
                import pyautogui

                pyautogui.typewrite(text, interval=0.05)
                return _result(True, f"⌨️ Typed: {text[:50]}", "TYPE_TEXT")
            except ImportError:
                return _result(False, "pyautogui not installed.", "TYPE_TEXT")
        except Exception as e:
            return _result(False, f"❌ {e}", "TYPE_TEXT")

    def press_key(self, key: str) -> dict:
        """Press a keyboard shortcut."""
        try:
            if self._st:
                result = self._st.send_keys(key)
                return _result(True, f"⌨️ {result}", "PRESS_KEY")
            try:
                import pyautogui

                parts = [k.strip() for k in key.split("+")]
                if len(parts) > 1:
                    pyautogui.hotkey(*parts)
                else:
                    pyautogui.press(parts[0])
                return _result(True, f"⌨️ Pressed: {key}", "PRESS_KEY")
            except ImportError:
                return _result(False, "pyautogui not installed.", "PRESS_KEY")
        except Exception as e:
            return _result(False, f"❌ {e}", "PRESS_KEY")

    # ── Zip / Unzip ───────────────────────────────────────────────────────────

    def zip_files(self, paths: list, output: str = "archive.zip") -> dict:
        """Create a zip archive."""
        try:
            import zipfile

            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
                if isinstance(paths, str):
                    paths = [p.strip() for p in paths.split(",")]
                for p in paths:
                    if os.path.exists(p):
                        z.write(p, os.path.basename(p))
            return _result(True, f"📦 Created: {output}", "ZIP_FILES")
        except Exception as e:
            return _result(False, f"❌ Zip failed: {e}", "ZIP_FILES")

    def unzip_file(self, path: str, destination: str = ".") -> dict:
        """Extract a zip archive."""
        try:
            import zipfile

            with zipfile.ZipFile(path, "r") as z:
                z.extractall(destination)
            return _result(
                True,
                f"📦 Extracted {path} to {os.path.abspath(destination)}",
                "UNZIP_FILE",
            )
        except Exception as e:
            return _result(False, f"❌ Unzip failed: {e}", "UNZIP_FILE")

    # ── Download ──────────────────────────────────────────────────────────────

    def download_file(self, url: str, destination: str = None) -> dict:
        """Download a file from a URL."""
        try:
            import requests

            if not destination:
                filename = url.split("/")[-1].split("?")[0] or "download"
                destination = os.path.join(
                    os.path.expanduser("~"), "Downloads", filename
                )
            os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)

            r = requests.get(url, stream=True, timeout=120)
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))

            with open(destination, "wb") as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

            size = os.path.getsize(destination)
            if size < 1024 * 1024:
                sz = f"{size / 1024:.1f} KB"
            else:
                sz = f"{size / (1024 * 1024):.1f} MB"
            return _result(
                True, f"⬇️ Downloaded: {destination} ({sz})", "DOWNLOAD_FILE"
            )
        except Exception as e:
            return _result(False, f"❌ Download failed: {e}", "DOWNLOAD_FILE")

    # ── File Manager ──────────────────────────────────────────────────────────

    def open_file_manager(self, path: str = None) -> dict:
        """Open the file manager at a specific path."""
        try:
            path = path or os.path.expanduser("~")
            if IS_WINDOWS:
                import subprocess

                subprocess.Popen(["explorer", path])
            elif IS_MAC:
                import subprocess

                subprocess.Popen(["open", path])
            else:
                import subprocess

                subprocess.Popen(["xdg-open", path])
            return _result(
                True, f"📂 Opened file manager at: {path}", "OPEN_FILE_MANAGER"
            )
        except Exception as e:
            return _result(False, f"❌ {e}", "OPEN_FILE_MANAGER")

    # ── Find and Replace ──────────────────────────────────────────────────────

    def find_replace_in_file(self, file_path: str, find: str, replace: str) -> dict:
        """Find and replace text in a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            count = content.count(find)
            if count == 0:
                return _result(
                    False, f"❌ '{find}' not found in {file_path}", "FIND_REPLACE"
                )
            new_content = content.replace(find, replace)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return _result(
                True,
                f"✏️ Replaced {count} occurrence(s) in {file_path}",
                "FIND_REPLACE",
            )
        except Exception as e:
            return _result(False, f"❌ Find/replace failed: {e}", "FIND_REPLACE")
