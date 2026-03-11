"""
Agent 6: System Agent — Full System Access Edition
Executes OS-level actions using the system_tools toolkit.
Supports 40+ capabilities across every major Windows system category.

v2: Enhanced with EXTRACTED_QUERY support for accurate media playback.
"""

import os
import sys
import re
import json
import subprocess
import webbrowser
import urllib.parse
from agents.base_agent import BaseAgent
from utils import system_tools as st
from core.interpreter_engine import InterpreterEngine

SYSTEM_PROMPT = """You are the System Agent for GUNA-ASTRA — a full-access Windows system controller.

You can do ANYTHING on the user's computer. Interpret the task and return a JSON action plan.

Available actions (return one):
  open_url            - Open any website URL
  play_youtube        - Play/search YouTube (args: query)
  google_search       - Search Google in browser (args: query)
  web_search          - Get search results as text (args: query)
  open_app            - Launch any application (target: app name or path)
  open_file           - Open a file with its default program
  open_folder         - Open folder in File Explorer
  run_command         - Run any shell/CMD command
  run_powershell      - Run PowerShell command
  write_file          - Write content to a file (args: path, content)
  read_file           - Read a file's contents (args: path)
  delete_file         - Delete a file (DANGEROUS)
  copy_file           - Copy file (args: src, dst)
  move_file           - Move/rename file (args: src, dst)
  list_directory      - List files in a directory (args: path)
  search_files        - Search for files (args: root, pattern)
  zip_files           - Zip files (args: paths, output)
  unzip_file          - Unzip archive (args: path, output_dir)
  screenshot          - Take a screenshot
  minimize_window     - Minimize a window (args: title)
  maximize_window     - Maximize a window (args: title)
  close_window        - Close a window (args: title)
  list_windows        - List all open windows
  volume_set          - Set volume 0-100 (args: level)
  volume_up           - Increase volume
  volume_down         - Decrease volume
  mute                - Toggle mute
  play_pause          - Play/pause media
  next_track          - Next media track
  prev_track          - Previous media track
  get_clipboard       - Read clipboard
  set_clipboard       - Write to clipboard (args: text)
  send_keys           - Send keystrokes (args: keys)
  type_text           - Type text (args: text)
  system_info         - Get system information
  network_info        - Get network/IP info
  wifi_networks       - List nearby WiFi networks
  connect_wifi        - Connect to WiFi (args: ssid, password)
  ping                - Ping a host (args: host)
  download_file       - Download from URL (args: url, save_path)
  list_processes      - List running processes
  kill_process        - Kill a process (args: name)
  notify              - Show Windows notification (args: title, message)
  schedule_task       - Schedule a command (args: name, command, run_at)
  disk_usage          - Get disk space usage
  lock_screen         - Lock the screen
  sleep               - Put system to sleep
  set_wallpaper       - Set desktop wallpaper (args: image_path)
  screen_resolution   - Get screen resolution
  get_time            - Get current date/time
  run_python          - Run Python code (args: code)
  speak               - Speak text aloud (args: text)
  get_weather         - Get weather info (args: city)
  install_app         - Install app via winget (args: name)
  search_app          - Search apps in winget (args: name)
  send_email          - Open email client (args: to, subject, body)
  set_brightness      - Set screen brightness 0-100 (args: level)
  battery_status      - Get battery / power status
  toggle_bluetooth    - Toggle Bluetooth on/off
  empty_recycle_bin   - Empty the Recycle Bin
  list_startup_apps   - List startup programs

Return ONLY JSON with keys: "action", "target", "args", "dangerous"
Mark dangerous=true for: delete_file, shutdown, format, kill_process, restart, empty_recycle_bin
Example: {"action": "play_youtube", "target": "Pyaar Deewana Hota Hai", "args": {}, "dangerous": false}
"""


class SystemAgent(BaseAgent):
    def __init__(self):
        super().__init__("SystemAgent", SYSTEM_PROMPT)
        self._engine = InterpreterEngine()

    # ── v2 Interface ──────────────────────────────────────────────────────────
    def execute(self, task: str) -> str:
        """v2 orchestrator interface: handles hints like [EXTRACTED_QUERY: ...] [PLATFORM: ...]"""
        extracted_query = self._extract_hint(task, "EXTRACTED_QUERY")
        extracted_platform = self._extract_hint(task, "PLATFORM") or "youtube"

        t = task.lower()
        # v2 media handling with proper URL encoding
        if extracted_query or any(w in t for w in ["play ", "listen to", "put on"]):
            return self._v2_play_media(task, extracted_query, extracted_platform)

        # v2 browser handling
        if any(w in t for w in ["search ", "google "]) and extracted_query:
            url = f"https://www.google.com/search?q={urllib.parse.quote(extracted_query)}"
            webbrowser.open(url)
            return f"🔍 Google search: '{extracted_query}'"

        # Delegate to existing run() for everything else
        clean_task = self._clean_hint_text(task)
        result = self.run({"description": clean_task, "original_goal": clean_task})
        return result.get("output", str(result))

    def _extract_hint(self, text: str, key: str) -> str:
        """Extract orchestrator-injected hints like [EXTRACTED_QUERY: ...]"""
        m = re.search(rf"\[{re.escape(key)}:\s*(.+?)\]", text)
        return m.group(1).strip() if m else ""

    def _clean_hint_text(self, text: str) -> str:
        """Remove hint brackets from display."""
        return re.sub(r"\[(?:EXTRACTED_QUERY|PLATFORM):[^\]]+\]", "", text).strip()

    def _v2_play_media(self, task: str, query: str, platform: str) -> str:
        """v2-style media playback with proper URL encoding."""
        if not query:
            # Parse from task text
            text = self._clean_hint_text(task)
            text = re.sub(r"\s+(?:on|in|via|using)\s+(?:youtube|spotify|music|soundcloud)\s*$", "", text, flags=re.I)
            query = re.sub(r"^(?:play|listen to|put on|start playing|can you play|please play)\s+", "", text, flags=re.I)
            query = query.strip().strip(".,!?\"'")

        if not query:
            return "I couldn't figure out what to play. Could you say the song name again?"

        if platform == "spotify":
            url = f"https://open.spotify.com/search/{urllib.parse.quote(query)}"
            msg = "Spotify"
        else:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            msg = "YouTube"

        try:
            webbrowser.open(url)
            return f"🎵 Opened {msg} searching for: '{query}'"
        except Exception as e:
            return f"Couldn't open browser: {e}"

    def run(self, task: dict) -> dict:
        description = task.get("description", "")
        code_to_run = task.get("code", None)

        if code_to_run:
            return self.execute_from_code(code_to_run, task)

        self.logger.info(f"System task: {description}")

        # ── Fast path (no LLM needed) ──────────────────────────────────────
        fast = self._fast_path(description, task)
        if fast:
            return fast

        # ── Ask LLM to plan ───────────────────────────────────────────────
        response = self.think(f"Plan the OS action for this task:\n{description}")

        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            plan = json.loads(match.group()) if match else {}
        except Exception:
            plan = {}

        if not plan:
            return self._handle_by_keywords(description, task)

        return self._execute_plan(plan, task)

    # ── Fast-path heuristics ──────────────────────────────────────────────────

    def _fast_path(self, description: str, task: dict) -> dict | None:
        d = description.lower()

        # YouTube / music / song / play
        if any(w in d for w in ["youtube", "play ", "song", "music video", "watch"]):
            return self._do_play_youtube(description, task)

        # Screenshot
        if any(w in d for w in ["screenshot", "screen capture", "screen shot", "capture screen"]):
            path = st.take_screenshot()
            if path:
                return self.report("success", f"📸 Screenshot saved: {path}", task)
            return self.report("failed", "Screenshot failed.", task)

        # Volume controls
        if "volume" in d or "mute" in d or "unmute" in d:
            return self._do_volume(description, task)

        # Media controls
        if "play pause" in d or "pause music" in d or "pause song" in d:
            return self.report("success", st.play_pause_media(), task)
        if "next track" in d or "next song" in d or "skip song" in d:
            return self.report("success", st.next_track(), task)
        if "previous track" in d or "previous song" in d or "prev song" in d:
            return self.report("success", st.prev_track(), task)

        # Clipboard
        if "clipboard" in d:
            return self._do_clipboard(description, task)

        # Lock / sleep / power
        if "lock screen" in d or "lock pc" in d or "lock computer" in d:
            return self.report("success", st.lock_screen(), task)
        if "sleep" in d and ("pc" in d or "computer" in d or "system" in d):
            return self.report("success", st.sleep_system(), task)
        if "abort shutdown" in d or "cancel shutdown" in d:
            return self.report("success", st.abort_shutdown(), task)

        # System info
        if any(w in d for w in ["system info", "pc info", "computer info", "hardware info", "ram", "cpu info"]):
            return self.report("success", st.get_system_info(), task)
        if "disk" in d and ("space" in d or "usage" in d or "storage" in d):
            return self.report("success", st.get_disk_usage(), task)
        if "screen resolution" in d or "display resolution" in d:
            return self.report("success", st.get_screen_resolution(), task)
        if "current time" in d or "what time" in d or "date and time" in d:
            return self.report("success", st.get_current_time(), task)

        # Network
        if "my ip" in d or "ip address" in d or "public ip" in d:
            return self.report("success", f"Your IP: {st.get_ip_address()}", task)
        if "network info" in d or "ipconfig" in d or "wifi info" in d:
            return self.report("success", st.network_info(), task)
        if "wifi networks" in d or "available wifi" in d or "wifi list" in d:
            return self.report("success", st.wifi_networks(), task)

        # Process management
        if "list processes" in d or "running processes" in d or "show processes" in d:
            return self.report("success", st.list_processes(), task)

        # Windows
        if "list windows" in d or "open windows" in d or "show windows" in d:
            return self.report("success", st.list_open_windows(), task)

        # Open browser / website
        if any(w in d for w in ["open browser", "open chrome", "open edge", "browse to", "go to website"]):
            url = self._extract_url(description) or "https://www.google.com"
            browser_used = st.open_url(url)
            return self.report("success", f"Opened {url} in {browser_used}.", task)

        # Google search
        if any(w in d for w in ["search google", "google search", "google for", "look up", "search for"]):
            query = re.sub(r'(search|google|for|look up|find|on google)\s*', '', d, flags=re.IGNORECASE).strip() or description
            url, browser = st.google_search(query)
            return self.report("success", f"🔍 Searched Google for '{query}' in {browser}.\n🔗 {url}", task)

        # Weather
        if any(w in d for w in ["weather", "temperature", "forecast"]):
            city = re.sub(r'(weather|temperature|forecast|what|is|the|in|of|for|show|get|check|whats)\s*', '', d).strip()
            return self.report("success", st.get_weather(city), task)

        # Text-to-speech
        if any(w in d for w in ["say ", "speak ", "read aloud", "tell me", "read out"]):
            text = re.sub(r'^(say|speak|read aloud|read out|tell me)\s*', '', d, flags=re.IGNORECASE).strip() or description
            return self.report("success", st.speak(text), task)

        # Email
        if any(w in d for w in ["send email", "send mail", "compose email", "write email", "draft email"]):
            return self.report("success", st.send_email(), task)

        # Battery
        if "battery" in d or "power status" in d or "charge level" in d:
            return self.report("success", st.get_battery_status(), task)

        # Brightness
        if "brightness" in d:
            nums = re.findall(r'\d+', d)
            level = int(nums[0]) if nums else 50
            return self.report("success", st.set_brightness(level), task)

        # Bluetooth
        if "bluetooth" in d:
            return self.report("success", st.toggle_bluetooth(), task)

        # Recycle bin
        if "recycle bin" in d or "trash" in d or "empty bin" in d:
            return self.report("success", st.empty_recycle_bin(), task)

        # Startup apps
        if "startup" in d and ("app" in d or "program" in d or "list" in d):
            return self.report("success", st.list_startup_apps(), task)

        # Install app
        if any(w in d for w in ["install ", "download app", "get app"]):
            app = re.sub(r'(install|download|get|app)\s*', '', d).strip()
            if app:
                return self.report("success", f"Installing {app}...\n{st.install_app(app)}", task)

        # Notification
        if "notification" in d or "notify me" in d or "send notification" in d:
            msg = description
            return self.report("success", st.show_notification("GUNA-ASTRA", msg), task)

        return None

    # ── LLM plan executor ─────────────────────────────────────────────────────

    def _execute_plan(self, plan: dict, task: dict) -> dict:
        action = plan.get("action", "")
        target = plan.get("target", "")
        args = plan.get("args", {})
        dangerous = plan.get("dangerous", False)

        if dangerous:
            return self.report(
                "pending_confirmation",
                f"⚠️  DANGEROUS ACTION REQUESTED\n"
                f"Action : {action}\n"
                f"Target : {target}\n\n"
                f"Type 'confirm' to proceed or anything else to cancel.",
                task
            )

        return self._dispatch(action, target, args, task)

    def _dispatch(self, action: str, target: str, args: dict, task: dict) -> dict:
        try:
            # ── Browser / URL ──────────────────────────────────────────────
            if action == "open_url":
                browser_used = st.open_url(target)
                return self.report("success", f"Opened {target} in {browser_used}.", task)

            if action == "play_youtube":
                query = target or args.get("query", "")
                return self._do_play_youtube(query, task)

            # ── Apps / Files / Folders ─────────────────────────────────────
            if action == "open_app":
                path = st.launch_app(target, args.get("args", []))
                return self.report("success", f"✅ Launched: {target} ({path})", task)

            if action == "open_file":
                path = target or args.get("path", "")
                st.open_with_default(path)
                return self.report("success", f"Opened file: {path}", task)

            if action == "open_folder":
                folder = target or args.get("path", os.path.expanduser("~"))
                st.open_with_default(folder)
                return self.report("success", f"Opened folder: {folder}", task)

            # ── File CRUD ──────────────────────────────────────────────────
            if action == "write_file":
                path = args.get("path", target or "output.txt")
                content = args.get("content", "")
                st.write_file(path, content)
                return self.report("success", f"✅ File written: {path}", task)

            if action == "read_file":
                path = target or args.get("path", "")
                content = st.read_file(path)
                return self.report("success", f"📄 {path}:\n{content[:2000]}", task)

            if action == "delete_file":
                path = target or args.get("path", "")
                st.delete_file(path)
                return self.report("success", f"🗑️ Deleted: {path}", task)

            if action == "copy_file":
                src = args.get("src", target)
                dst = args.get("dst", "")
                st.copy_file(src, dst)
                return self.report("success", f"Copied {src} → {dst}", task)

            if action == "move_file":
                src = args.get("src", target)
                dst = args.get("dst", "")
                st.move_file(src, dst)
                return self.report("success", f"Moved {src} → {dst}", task)

            if action == "list_directory":
                path = target or args.get("path", ".")
                items = st.list_directory(path)
                listing = "\n".join(items[:60]) or "(empty)"
                return self.report("success", f"📂 {path}:\n{listing}", task)

            if action == "search_files":
                root = args.get("root", os.path.expanduser("~"))
                pattern = args.get("pattern", target or "")
                found = st.search_files(root, pattern)
                return self.report("success", f"🔍 Found {len(found)} files:\n" + "\n".join(found), task)

            if action == "zip_files":
                paths = args.get("paths", [target])
                out = args.get("output", "archive.zip")
                st.zip_files(paths, out)
                return self.report("success", f"📦 Zipped to: {out}", task)

            if action == "unzip_file":
                path = target or args.get("path", "")
                out_dir = args.get("output_dir", "")
                st.unzip_file(path, out_dir)
                return self.report("success", f"📦 Unzipped: {path}", task)

            # ── Shell commands ─────────────────────────────────────────────
            if action == "run_command":
                output = st.run_shell(target)
                return self.report("success", f"💻 Output:\n{output}", task)

            if action == "run_powershell":
                output = st.run_shell(target, powershell=True)
                return self.report("success", f"💻 PS Output:\n{output}", task)

            if action == "run_python":
                code = args.get("code", target)
                output = st.run_python_code(code)
                return self.report("success", f"🐍 Output:\n{output}", task)

            # ── Screenshot ─────────────────────────────────────────────────
            if action == "screenshot":
                path = args.get("path", None)
                saved = st.take_screenshot(path)
                if saved:
                    return self.report("success", f"📸 Screenshot saved: {saved}", task)
                return self.report("failed", "Screenshot failed.", task)

            # ── Windows ────────────────────────────────────────────────────
            if action == "minimize_window":
                return self.report("success", st.minimize_window(target), task)
            if action == "maximize_window":
                return self.report("success", st.maximize_window(target), task)
            if action == "close_window":
                return self.report("success", st.close_window(target), task)
            if action == "list_windows":
                return self.report("success", st.list_open_windows(), task)

            # ── Audio ──────────────────────────────────────────────────────
            if action == "volume_set":
                lvl = int(args.get("level", target or 50))
                return self.report("success", st.set_volume(lvl), task)
            if action == "volume_up":
                steps = int(args.get("steps", 5))
                return self.report("success", st.volume_up(steps), task)
            if action == "volume_down":
                steps = int(args.get("steps", 5))
                return self.report("success", st.volume_down(steps), task)
            if action == "mute":
                return self.report("success", st.mute_volume(), task)
            if action == "play_pause":
                return self.report("success", st.play_pause_media(), task)
            if action == "next_track":
                return self.report("success", st.next_track(), task)
            if action == "prev_track":
                return self.report("success", st.prev_track(), task)

            # ── Clipboard / Keys ───────────────────────────────────────────
            if action == "get_clipboard":
                return self.report("success", f"📋 Clipboard: {st.get_clipboard()}", task)
            if action == "set_clipboard":
                text = target or args.get("text", "")
                return self.report("success", st.set_clipboard(text), task)
            if action == "send_keys":
                keys = target or args.get("keys", "")
                return self.report("success", st.send_keys(keys), task)
            if action == "type_text":
                text = target or args.get("text", "")
                return self.report("success", st.type_text(text), task)

            # ── System Info / Network ──────────────────────────────────────
            if action == "system_info":
                return self.report("success", st.get_system_info(), task)
            if action == "network_info":
                return self.report("success", st.network_info(), task)
            if action == "wifi_networks":
                return self.report("success", st.wifi_networks(), task)
            if action == "ping":
                host = target or args.get("host", "google.com")
                return self.report("success", st.ping(host), task)
            if action == "download_file":
                url = target or args.get("url", "")
                save = args.get("save_path", "")
                result = st.download_file(url, save or None)
                return self.report("success", f"⬇️ Downloaded: {result}", task)
            if action == "list_processes":
                return self.report("success", st.list_processes(target), task)
            if action == "kill_process":
                return self.report("success", st.kill_process(target), task)
            if action == "disk_usage":
                drive = target or "C:"
                return self.report("success", st.get_disk_usage(drive), task)
            if action == "screen_resolution":
                return self.report("success", st.get_screen_resolution(), task)
            if action == "get_time":
                return self.report("success", st.get_current_time(), task)

            # ── Notifications / Scheduler ──────────────────────────────────
            if action == "notify":
                title = args.get("title", "GUNA-ASTRA")
                message = args.get("message", target)
                return self.report("success", st.show_notification(title, message), task)
            if action == "schedule_task":
                name = args.get("name", "GUNA-ASTRA-Task")
                cmd = args.get("command", target)
                run_at = args.get("run_at", "")
                return self.report("success", st.schedule_task(name, cmd, run_at), task)

            # ── Power ──────────────────────────────────────────────────────
            if action == "lock_screen":
                return self.report("success", st.lock_screen(), task)
            if action == "sleep":
                return self.report("success", st.sleep_system(), task)
            if action == "set_wallpaper":
                path = target or args.get("image_path", "")
                return self.report("success", st.set_wallpaper(path), task)

            # ── NEW: Google / Web Search ───────────────────────────────────
            if action == "google_search":
                query = target or args.get("query", "")
                url, browser = st.google_search(query)
                return self.report("success", f"🔍 Searched Google for '{query}' in {browser}.\n🔗 {url}", task)
            if action == "web_search":
                query = target or args.get("query", "")
                results = st.web_search(query)
                return self.report("success", f"🔍 Search results for '{query}':\n{results}", task)

            # ── NEW: TTS / Weather / Email ─────────────────────────────────
            if action == "speak":
                text = target or args.get("text", "")
                return self.report("success", st.speak(text), task)
            if action == "get_weather":
                city = target or args.get("city", "")
                return self.report("success", st.get_weather(city), task)
            if action == "send_email":
                to = args.get("to", target)
                subject = args.get("subject", "")
                body = args.get("body", "")
                return self.report("success", st.send_email(to, subject, body), task)

            # ── NEW: Install / Brightness / Battery / Bluetooth ───────────
            if action == "install_app":
                name = target or args.get("name", "")
                return self.report("success", st.install_app(name), task)
            if action == "search_app":
                name = target or args.get("name", "")
                return self.report("success", st.search_app(name), task)
            if action == "set_brightness":
                level = int(args.get("level", target or 50))
                return self.report("success", st.set_brightness(level), task)
            if action == "battery_status":
                return self.report("success", st.get_battery_status(), task)
            if action == "toggle_bluetooth":
                return self.report("success", st.toggle_bluetooth(), task)
            if action == "empty_recycle_bin":
                return self.report("success", st.empty_recycle_bin(), task)
            if action == "list_startup_apps":
                return self.report("success", st.list_startup_apps(), task)
            if action == "connect_wifi":
                ssid = target or args.get("ssid", "")
                password = args.get("password", "")
                return self.report("success", st.connect_wifi(ssid, password), task)

            # ── Fallback ───────────────────────────────────────────────────
            return self._handle_by_keywords(task.get("description", target), task)

        except Exception as e:
            self.logger.error(f"Action '{action}' failed: {e}")
            return self.report("failed", f"Error executing '{action}': {e}", task)

    # ── Helper actions ────────────────────────────────────────────────────────

    def _do_play_youtube(self, description: str, task: dict) -> dict:
        strip_words = [
            "play", "search", "find", "open", "watch", "on youtube", "youtube",
            "in chrome", "in browser", "song", "video", "music", "me", "the", "a"
        ]
        query = description.lower()
        for w in strip_words:
            query = query.replace(w, " ")
        query = " ".join(query.split()).strip() or "top hits"

        url, browser = st.youtube_search(query)
        return self.report(
            "success",
            f"🎵 Opened YouTube search for '{query}' in {browser}.\n🔗 {url}",
            task
        )

    def _do_volume(self, description: str, task: dict) -> dict:
        d = description.lower()
        nums = re.findall(r'\d+', d)

        if "mute" in d or "unmute" in d:
            return self.report("success", st.mute_volume(), task)
        if nums:
            level = int(nums[0])
            return self.report("success", st.set_volume(level), task)
        if any(w in d for w in ["up", "increase", "louder", "raise"]):
            return self.report("success", st.volume_up(), task)
        if any(w in d for w in ["down", "decrease", "lower", "quieter", "reduce"]):
            return self.report("success", st.volume_down(), task)
        if "max" in d or "100" in d:
            return self.report("success", st.set_volume(100), task)
        if "min" in d or "0" in d:
            return self.report("success", st.set_volume(0), task)
        return self.report("success", st.volume_up(), task)

    def _do_clipboard(self, description: str, task: dict) -> dict:
        d = description.lower()
        if any(w in d for w in ["get", "read", "show", "what", "paste", "copy from"]):
            return self.report("success", f"📋 Clipboard:\n{st.get_clipboard()}", task)
        content = re.sub(
            r'.*(clipboard|copy)\s*[:\-]?\s*', '', description, flags=re.IGNORECASE
        ).strip() or description
        return self.report("success", st.set_clipboard(content), task)

    def _extract_url(self, text: str) -> str | None:
        match = re.search(r'https?://\S+', text)
        return match.group() if match else None

    # ── Keyword fallback (always works) ───────────────────────────────────────

    def _handle_by_keywords(self, description: str, task: dict) -> dict:
        d = description.lower()

        if any(w in d for w in ["youtube", "play ", "song", "music", "watch"]):
            return self._do_play_youtube(description, task)
        if "screenshot" in d or "screen capture" in d:
            path = st.take_screenshot()
            return self.report("success" if path else "failed",
                               f"📸 Screenshot: {path}" if path else "Screenshot failed.", task)
        if "volume" in d or "mute" in d:
            return self._do_volume(description, task)
        if "clipboard" in d:
            return self._do_clipboard(description, task)
        if "lock" in d and "screen" in d:
            return self.report("success", st.lock_screen(), task)
        if "system info" in d or "pc info" in d:
            return self.report("success", st.get_system_info(), task)
        if "ip" in d or "internet" in d:
            return self.report("success", f"IP: {st.get_ip_address()}", task)
        if "notepad" in d:
            st.launch_app("notepad"); return self.report("success", "Opened Notepad.", task)
        if "calculator" in d or " calc" in d:
            st.launch_app("calculator"); return self.report("success", "Opened Calculator.", task)
        if "task manager" in d:
            st.launch_app("task manager"); return self.report("success", "Opened Task Manager.", task)
        if "file explorer" in d or "open folder" in d:
            st.open_with_default(os.path.expanduser("~"))
            return self.report("success", "Opened File Explorer.", task)
        if "chrome" in d:
            url = self._extract_url(description) or "https://www.google.com"
            st.open_url(url, "chrome")
            return self.report("success", f"Opened Chrome at {url}.", task)
        if "edge" in d:
            url = self._extract_url(description) or "https://www.google.com"
            st.open_url(url, "edge")
            return self.report("success", f"Opened Edge at {url}.", task)
        if any(w in d for w in ["open", "launch", "start", "run"]):
            # Generic app launch attempt
            app = re.sub(r'(open|launch|start|run)\s+', '', d).strip()
            if app:
                try:
                    path = st.launch_app(app)
                    return self.report("success", f"Launched: {app}", task)
                except Exception:
                    pass

        return self.report("failed", f"Could not determine system action for: {description}", task)

    # ── InterpreterEngine code execution ──────────────────────────────────────────

    def execute_from_code(self, code: str, task: dict) -> dict:
        """Execute code using InterpreterEngine with automatic retry."""
        description = task.get("description", "code execution")
        self.logger.info(f"Executing code via InterpreterEngine: {description[:80]}")
        result = self._engine.execute_with_retry(code, description)
        status = "success" if result.get("success") else "failed"
        output = result.get("output", "")
        return self.report(status, f"Script output:\n{output}", task)

