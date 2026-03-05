"""
GUNA-ASTRA System Tools
Full Windows system access toolkit used by SystemAgent.
Covers: Files, Apps, Browser, Processes, Windows, Screen,
        Audio, Clipboard, Network, Notifications, Scheduler, Registry, Mouse/KB.
"""

import os
import sys
import shutil
import subprocess
import webbrowser
import tempfile
import glob
import zipfile
import platform
import socket
import json
import re
from datetime import datetime
from urllib.parse import quote_plus
from pathlib import Path


# ══════════════════════════════════════════════════════════
#  BROWSER / URL
# ══════════════════════════════════════════════════════════

def find_chrome() -> str | None:
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome SxS\Application\chrome.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return shutil.which("chrome") or shutil.which("google-chrome")


def find_edge() -> str | None:
    candidates = [
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return shutil.which("msedge")


def find_firefox() -> str | None:
    candidates = [
        os.path.expandvars(r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Mozilla Firefox\firefox.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return shutil.which("firefox")


def open_url(url: str, browser: str = "best") -> str:
    """Open URL in chrome / edge / firefox / default. Returns browser name used."""
    if browser == "chrome":
        exe = find_chrome()
    elif browser == "edge":
        exe = find_edge()
    elif browser == "firefox":
        exe = find_firefox()
    else:
        exe = find_chrome() or find_edge() or find_firefox()

    if exe:
        subprocess.Popen([exe, url])
        name = os.path.basename(exe).split(".")[0].title()
        return name
    webbrowser.open(url)
    return "default browser"


def youtube_search(query: str, browser: str = "best") -> tuple[str, str]:
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    used = open_url(url, browser)
    return url, used


# ══════════════════════════════════════════════════════════
#  FILE & FOLDER OPERATIONS
# ══════════════════════════════════════════════════════════

def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_file(path: str, content: str, append: bool = False) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8") as f:
        f.write(content)
    return path


def delete_file(path: str) -> bool:
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def delete_folder(path: str) -> bool:
    if os.path.isdir(path):
        shutil.rmtree(path)
        return True
    return False


def create_folder(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def copy_file(src: str, dst: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    return shutil.copy2(src, dst)


def move_file(src: str, dst: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    return shutil.move(src, dst)


def rename_file(src: str, new_name: str) -> str:
    dst = os.path.join(os.path.dirname(src), new_name)
    os.rename(src, dst)
    return dst


def list_directory(path: str = ".", pattern: str = "*") -> list[str]:
    path = os.path.expanduser(path)
    return sorted(glob.glob(os.path.join(path, pattern)))


def search_files(root: str, name_pattern: str, recursive: bool = True) -> list[str]:
    root = os.path.expanduser(root)
    matches = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if re.search(name_pattern, fn, re.IGNORECASE):
                matches.append(os.path.join(dirpath, fn))
        if not recursive:
            break
    return matches[:50]  # cap at 50


def zip_files(paths: list[str], output_zip: str) -> str:
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, os.path.basename(p))
    return output_zip


def unzip_file(zip_path: str, output_dir: str = None) -> str:
    output_dir = output_dir or os.path.dirname(zip_path)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(output_dir)
    return output_dir


def get_file_info(path: str) -> dict:
    stat = os.stat(path)
    return {
        "path": path,
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "is_file": os.path.isfile(path),
        "is_dir": os.path.isdir(path),
    }


def open_with_default(path: str):
    """Open any file/folder/URL with Windows default handler."""
    os.startfile(path)


# ══════════════════════════════════════════════════════════
#  SHELL / PROCESS EXECUTION
# ══════════════════════════════════════════════════════════

def run_shell(cmd: str, timeout: int = 30, powershell: bool = False) -> str:
    """Run a shell command and return combined output."""
    if powershell:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout
        )
    else:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
    return (result.stdout + result.stderr).strip() or "(no output)"


def launch_app(exe_or_name: str, args: list[str] = None) -> str:
    """Launch an application by path or name."""
    args = args or []
    expanded = os.path.expandvars(exe_or_name)

    # Well-known aliases
    aliases = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "wordpad": "wordpad.exe",
        "explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "taskmgr": "taskmgr.exe",
        "task manager": "taskmgr.exe",
        "control": "control.exe",
        "control panel": "control.exe",
        "regedit": "regedit.exe",
        "mmc": "mmc.exe",
        "devmgmt": "devmgmt.msc",
        "disk management": "diskmgmt.msc",
        "settings": "ms-settings:",
        "store": "ms-windows-store:",
        "snipping tool": "snippingtool.exe",
        "snip": "snippingtool.exe",
        "sticky notes": "stickynot.exe",
        "magnifier": "magnify.exe",
        "narrator": "narrator.exe",
        "character map": "charmap.exe",
        "event viewer": "eventvwr.msc",
        "services": "services.msc",
        "msconfig": "msconfig.exe",
        "winver": "winver.exe",
        "chrome": find_chrome() or "chrome",
        "google chrome": find_chrome() or "chrome",
        "edge": find_edge() or "msedge",
        "firefox": find_firefox() or "firefox",
        "vlc": os.path.expandvars(r"%PROGRAMFILES%\VideoLAN\VLC\vlc.exe"),
        "spotify": os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        "vscode": os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        "vs code": os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        "discord": os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe"),
        "teams": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe"),
        "zoom": os.path.expandvars(r"%APPDATA%\Zoom\bin\Zoom.exe"),
        "outlook": "outlook.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "onenote": "onenote.exe",
    }

    key = exe_or_name.lower().strip()
    resolved = aliases.get(key, expanded)
    resolved_exp = os.path.expandvars(resolved)

    if resolved_exp.startswith("ms-"):
        os.startfile(resolved_exp)
        return resolved_exp

    if os.path.isfile(resolved_exp):
        subprocess.Popen([resolved_exp] + args)
        return resolved_exp

    # Use PowerShell Start-Process as ultimate fallback
    subprocess.Popen(
        ["powershell", "-Command", f"Start-Process '{resolved}'"],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return resolved


def kill_process(name_or_pid: str) -> str:
    return run_shell(
        f"Stop-Process -Name '{name_or_pid}' -Force -ErrorAction SilentlyContinue",
        powershell=True
    )


def list_processes(filter_name: str = "") -> str:
    ps = "Get-Process | Select-Object Name,Id,CPU,WorkingSet | Sort-Object WorkingSet -Descending | Select-Object -First 30 | Format-Table -AutoSize"
    out = run_shell(ps, powershell=True)
    if filter_name:
        lines = [l for l in out.splitlines() if filter_name.lower() in l.lower() or "Name" in l]
        return "\n".join(lines)
    return out


def run_python_code(code: str, timeout: int = 60) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        result = subprocess.run([sys.executable, tmp], capture_output=True, text=True, timeout=timeout)
        return (result.stdout + result.stderr).strip() or "(no output)"
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════
#  WINDOW MANAGEMENT  (PowerShell / WinAPI via PS)
# ══════════════════════════════════════════════════════════

def _ps_window(action: str, title_filter: str = "") -> str:
    """Generic window controller via PowerShell."""
    if title_filter:
        ps = (
            f"Add-Type -A System.Windows.Forms; "
            f"[System.Windows.Forms.Application]::DoEvents(); "
            f"$wnd = [System.Diagnostics.Process]::GetProcesses() | "
            f"Where-Object {{$_.MainWindowTitle -like '*{title_filter}*'}} | "
            f"Select-Object -First 1; "
            f"if($wnd){{ {action} $wnd.MainWindowHandle }}"
        )
    else:
        ps = action
    return run_shell(ps, powershell=True)


def minimize_window(title: str = "") -> str:
    if title:
        ps = (
            f"Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
            f"public class W{{ [DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr h, int n); }}';"
            f"$p = Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}} | Select-Object -First 1;"
            f"if($p){{[W]::ShowWindow($p.MainWindowHandle, 6)}}"
        )
        return run_shell(ps, powershell=True) or f"Minimized: {title}"
    # Minimize foreground window
    return run_shell(
        "(New-Object -ComObject WScript.Shell).SendKeys('% {DOWN}')",
        powershell=True
    ) or "Minimized active window"


def maximize_window(title: str = "") -> str:
    if title:
        ps = (
            f"Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
            f"public class W{{ [DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr h, int n); }}';"
            f"$p = Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}} | Select-Object -First 1;"
            f"if($p){{[W]::ShowWindow($p.MainWindowHandle, 3)}}"
        )
        return run_shell(ps, powershell=True) or f"Maximized: {title}"
    return run_shell(
        "(New-Object -ComObject WScript.Shell).SendKeys('% {UP}')",
        powershell=True
    ) or "Maximized active window"


def close_window(title: str) -> str:
    ps = (
        f"$p = Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}} | Select-Object -First 1; "
        f"if($p){{$p.CloseMainWindow()}}"
    )
    return run_shell(ps, powershell=True) or f"Closed window: {title}"


def switch_to_window(title: str) -> str:
    ps = (
        f"Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
        f"public class W{{ [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr h); }}';"
        f"$p = Get-Process | Where-Object {{$_.MainWindowTitle -like '*{title}*'}} | Select-Object -First 1;"
        f"if($p){{[W]::SetForegroundWindow($p.MainWindowHandle)}}"
    )
    return run_shell(ps, powershell=True) or f"Switched to: {title}"


def list_open_windows() -> str:
    ps = "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object Name, MainWindowTitle | Format-Table -AutoSize"
    return run_shell(ps, powershell=True)


# ══════════════════════════════════════════════════════════
#  SCREENSHOT
# ══════════════════════════════════════════════════════════

def take_screenshot(out_path: str = None) -> str:
    if not out_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(os.path.expanduser("~"), "Desktop", f"screenshot_{ts}.png")
    out_path = out_path.replace("\\", "\\\\")
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
        "$scr=[System.Windows.Forms.Screen]::PrimaryScreen; "
        "$bmp=New-Object System.Drawing.Bitmap($scr.Bounds.Width,$scr.Bounds.Height); "
        "$g=[System.Drawing.Graphics]::FromImage($bmp); "
        "$g.CopyFromScreen($scr.Bounds.Location,[System.Drawing.Point]::Empty,$scr.Bounds.Size); "
        f"$bmp.Save('{out_path}'); $g.Dispose(); $bmp.Dispose()"
    )
    run_shell(ps, powershell=True)
    return out_path if os.path.isfile(out_path) else ""


# ══════════════════════════════════════════════════════════
#  AUDIO / VOLUME
# ══════════════════════════════════════════════════════════

def set_volume(level: int) -> str:
    """Set master volume 0-100."""
    level = max(0, min(100, level))
    ps = (
        f"$obj = New-Object -ComObject WScript.Shell; "
        f"1..50 | ForEach-Object {{$obj.SendKeys([char]174)}}; "
        f"1..{level//2} | ForEach-Object {{$obj.SendKeys([char]175)}}"
    )
    run_shell(ps, powershell=True)
    return f"Volume set to {level}%"


def mute_volume() -> str:
    run_shell("(New-Object -ComObject WScript.Shell).SendKeys([char]173)", powershell=True)
    return "Volume muted/unmuted"


def volume_up(steps: int = 5) -> str:
    ps = f"$o=New-Object -ComObject WScript.Shell; 1..{steps}|%{{$o.SendKeys([char]175)}}"
    run_shell(ps, powershell=True)
    return f"Volume increased by {steps} steps"


def volume_down(steps: int = 5) -> str:
    ps = f"$o=New-Object -ComObject WScript.Shell; 1..{steps}|%{{$o.SendKeys([char]174)}}"
    run_shell(ps, powershell=True)
    return f"Volume decreased by {steps} steps"


def play_pause_media() -> str:
    run_shell("(New-Object -ComObject WScript.Shell).SendKeys([char]179)", powershell=True)
    return "Media play/pause toggled"


def next_track() -> str:
    run_shell("(New-Object -ComObject WScript.Shell).SendKeys([char]176)", powershell=True)
    return "Skipped to next track"


def prev_track() -> str:
    run_shell("(New-Object -ComObject WScript.Shell).SendKeys([char]177)", powershell=True)
    return "Went to previous track"


# ══════════════════════════════════════════════════════════
#  CLIPBOARD
# ══════════════════════════════════════════════════════════

def get_clipboard() -> str:
    return run_shell("Get-Clipboard", powershell=True)


def set_clipboard(text: str) -> str:
    safe = text.replace("'", "''")
    run_shell(f"Set-Clipboard -Value '{safe}'", powershell=True)
    return f"Clipboard set: {text[:80]}"


# ══════════════════════════════════════════════════════════
#  NETWORK / SYSTEM INFO
# ══════════════════════════════════════════════════════════

def get_system_info() -> str:
    info = {
        "os": platform.platform(),
        "hostname": socket.gethostname(),
        "python": sys.version,
        "cpu_count": os.cpu_count(),
        "cwd": os.getcwd(),
    }
    # Add RAM via PowerShell
    ram = run_shell(
        "(Get-WmiObject Win32_OperatingSystem | Select-Object -ExpandProperty TotalVisibleMemorySize)/1MB",
        powershell=True
    )
    info["ram_gb_approx"] = ram.strip()
    return json.dumps(info, indent=2)


def get_ip_address() -> str:
    return run_shell("(Invoke-WebRequest -Uri 'https://api.ipify.org' -UseBasicParsing).Content", powershell=True)


def ping(host: str) -> str:
    return run_shell(f"ping -n 4 {host}")


def network_info() -> str:
    return run_shell("ipconfig /all")


def wifi_networks() -> str:
    return run_shell("netsh wlan show networks")


def download_file(url: str, save_path: str = None) -> str:
    if not save_path:
        filename = url.split("/")[-1].split("?")[0] or "download"
        save_path = os.path.join(os.path.expanduser("~"), "Downloads", filename)
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    ps = f"Invoke-WebRequest -Uri '{url}' -OutFile '{save_path}' -UseBasicParsing"
    run_shell(ps, powershell=True)
    return save_path if os.path.isfile(save_path) else f"Download may have failed: {save_path}"


# ══════════════════════════════════════════════════════════
#  KEYBOARD / MOUSE SHORTCUTS  (via PowerShell WScript)
# ══════════════════════════════════════════════════════════

def send_keys(keys: str) -> str:
    """Send keystrokes using WScript.Shell SendKeys syntax."""
    safe = keys.replace("'", "''")
    run_shell(f"(New-Object -ComObject WScript.Shell).SendKeys('{safe}')", powershell=True)
    return f"Sent keys: {keys}"


def type_text(text: str) -> str:
    safe = text.replace("'", "''")
    run_shell(f"(New-Object -ComObject WScript.Shell).SendKeys('{safe}')", powershell=True)
    return f"Typed text: {text[:50]}"


# ══════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ══════════════════════════════════════════════════════════

def show_notification(title: str, message: str, duration: int = 5) -> str:
    safe_title = title.replace("'", "''")
    safe_msg = message.replace("'", "''")
    ps = (
        f"Add-Type -AssemblyName System.Windows.Forms; "
        f"$n=New-Object System.Windows.Forms.NotifyIcon; "
        f"$n.Icon=[System.Drawing.SystemIcons]::Information; "
        f"$n.Visible=$true; "
        f"$n.ShowBalloonTip({duration*1000},'{safe_title}','{safe_msg}',"
        f"[System.Windows.Forms.ToolTipIcon]::Info); "
        f"Start-Sleep -Seconds {duration}; $n.Dispose()"
    )
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps]
    )
    return f"Notification shown: {title}"


# ══════════════════════════════════════════════════════════
#  LOCATION / TIME
# ══════════════════════════════════════════════════════════

def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_disk_usage(drive: str = "C:") -> str:
    ps = f"Get-PSDrive {drive.rstrip(':')} | Select-Object Used,Free | Format-List"
    return run_shell(ps, powershell=True)


# ══════════════════════════════════════════════════════════
#  TASK SCHEDULER
# ══════════════════════════════════════════════════════════

def schedule_task(name: str, command: str, run_at: str) -> str:
    """Schedule a one-time task. run_at format: 'HH:MM' or 'YYYY-MM-DD HH:MM'"""
    ps = (
        f"$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c {command}'; "
        f"$trigger = New-ScheduledTaskTrigger -Once -At '{run_at}'; "
        f"Register-ScheduledTask -TaskName '{name}' -Action $action -Trigger $trigger -Force"
    )
    return run_shell(ps, powershell=True) or f"Task '{name}' scheduled for {run_at}"


def list_scheduled_tasks() -> str:
    return run_shell("Get-ScheduledTask | Where-Object {$_.TaskPath -eq '\\'} | Select-Object TaskName,State | Format-Table -AutoSize", powershell=True)


# ══════════════════════════════════════════════════════════
#  POWER MANAGEMENT
# ══════════════════════════════════════════════════════════

def lock_screen() -> str:
    run_shell("rundll32.exe user32.dll,LockWorkStation")
    return "Screen locked."


def sleep_system() -> str:
    run_shell("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return "System going to sleep."


def hibernate_system() -> str:
    run_shell("shutdown /h")
    return "System hibernating."


def restart_system(delay_seconds: int = 30) -> str:
    run_shell(f"shutdown /r /t {delay_seconds}")
    return f"System will restart in {delay_seconds} seconds. Run 'shutdown /a' to abort."


def shutdown_system(delay_seconds: int = 30) -> str:
    run_shell(f"shutdown /s /t {delay_seconds}")
    return f"System will shut down in {delay_seconds} seconds. Run 'shutdown /a' to abort."


def abort_shutdown() -> str:
    run_shell("shutdown /a")
    return "Shutdown/restart aborted."


# ══════════════════════════════════════════════════════════
#  WALLPAPER / DISPLAY
# ══════════════════════════════════════════════════════════

def set_wallpaper(image_path: str) -> str:
    image_path = os.path.abspath(image_path)
    ps = (
        f"Add-Type -TypeDefinition '"
        f"using System; using System.Runtime.InteropServices; "
        f"public class WP {{ "
        f"[DllImport(\"user32.dll\", CharSet=CharSet.Auto)] "
        f"public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni); }}'; "
        f"[WP]::SystemParametersInfo(20, 0, '{image_path}', 3)"
    )
    run_shell(ps, powershell=True)
    return f"Wallpaper set to: {image_path}"


def get_screen_resolution() -> str:
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$s=[System.Windows.Forms.Screen]::PrimaryScreen; "
        "Write-Output \"$($s.Bounds.Width)x$($s.Bounds.Height)\""
    )
    return run_shell(ps, powershell=True)


# ══════════════════════════════════════════════════════════
#  GOOGLE SEARCH (in browser)
# ══════════════════════════════════════════════════════════

def google_search(query: str, browser: str = "best") -> tuple[str, str]:
    """Open Google search in browser."""
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    used = open_url(url, browser)
    return url, used


# ══════════════════════════════════════════════════════════
#  WEB SEARCH (scrape real results)
# ══════════════════════════════════════════════════════════

def web_search(query: str, num_results: int = 5) -> str:
    """Fetch real search results from DuckDuckGo HTML (no API key needed)."""
    try:
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for item in soup.select(".result")[:num_results]:
            title_el = item.select_one(".result__a")
            snippet_el = item.select_one(".result__snippet")
            if title_el:
                title = title_el.get_text(strip=True)
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                href = title_el.get("href", "")
                results.append(f"• {title}\n  {snippet}\n  {href}")
        return "\n\n".join(results) if results else "No results found."
    except ImportError:
        return "beautifulsoup4 not installed. Run: pip install beautifulsoup4"
    except Exception as e:
        return f"Search error: {e}"


# ══════════════════════════════════════════════════════════
#  TEXT-TO-SPEECH
# ══════════════════════════════════════════════════════════

def speak(text: str) -> str:
    """Make Windows speak text aloud using SAPI."""
    safe = text.replace("'", "''").replace('"', '`"')
    ps = (
        f"Add-Type -AssemblyName System.Speech; "
        f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Speak('{safe}')"
    )
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return f"🔊 Speaking: {text[:80]}"


# ══════════════════════════════════════════════════════════
#  WEATHER
# ══════════════════════════════════════════════════════════

def get_weather(city: str = "") -> str:
    """Get weather from wttr.in (free, no API key)."""
    try:
        city_q = quote_plus(city) if city else ""
        url = f"https://wttr.in/{city_q}?format=%C+%t+%h+%w&lang=en"
        r = requests.get(url, timeout=10, headers={"User-Agent": "curl/7.0"})
        if r.status_code == 200 and "Unknown" not in r.text:
            return f"🌤️ Weather{' in ' + city if city else ''}: {r.text.strip()}"
        # Fallback: detailed
        url2 = f"https://wttr.in/{city_q}?format=3"
        r2 = requests.get(url2, timeout=10, headers={"User-Agent": "curl/7.0"})
        return f"🌤️ {r2.text.strip()}"
    except Exception as e:
        return f"Weather lookup failed: {e}"


# ══════════════════════════════════════════════════════════
#  APP INSTALLER (winget)
# ══════════════════════════════════════════════════════════

def install_app(name: str) -> str:
    """Install an application using winget."""
    return run_shell(f"winget install --accept-package-agreements --accept-source-agreements \"{name}\"", timeout=120)


def search_app(name: str) -> str:
    """Search for an application in winget."""
    return run_shell(f"winget search \"{name}\"", timeout=30)


# ══════════════════════════════════════════════════════════
#  EMAIL (open default mail client)
# ══════════════════════════════════════════════════════════

def send_email(to: str = "", subject: str = "", body: str = "") -> str:
    """Open default email client with pre-filled fields using mailto: link."""
    mailto = f"mailto:{to}?subject={quote_plus(subject)}&body={quote_plus(body)}"
    os.startfile(mailto)
    return f"📧 Email client opened (to: {to}, subject: {subject})"


# ══════════════════════════════════════════════════════════
#  BRIGHTNESS
# ══════════════════════════════════════════════════════════

def set_brightness(level: int) -> str:
    """Set screen brightness (0-100)."""
    level = max(0, min(100, level))
    ps = (
        f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1, {level})"
    )
    result = run_shell(ps, powershell=True)
    if "Error" in result or "Exception" in result:
        return f"Brightness control may not be supported on desktop PCs. ({result[:100]})"
    return f"🔆 Brightness set to {level}%"


# ══════════════════════════════════════════════════════════
#  WIFI CONNECT
# ══════════════════════════════════════════════════════════

def connect_wifi(ssid: str, password: str = "") -> str:
    """Connect to a Wi-Fi network."""
    if password:
        # Create a temporary profile XML
        profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM><security>
        <authEncryption><authentication>WPA2PSK</authentication>
        <encryption>AES</encryption><useOneX>false</useOneX></authEncryption>
        <sharedKey><keyType>passPhrase</keyType><protected>false</protected>
        <keyMaterial>{password}</keyMaterial></sharedKey>
    </security></MSM>
</WLANProfile>"""
        profile_path = os.path.join(tempfile.gettempdir(), f"wifi_{ssid}.xml")
        with open(profile_path, "w") as f:
            f.write(profile_xml)
        run_shell(f'netsh wlan add profile filename="{profile_path}"')
        os.unlink(profile_path)
    result = run_shell(f'netsh wlan connect name="{ssid}"')
    return result or f"Connecting to {ssid}..."


# ══════════════════════════════════════════════════════════
#  BATTERY / POWER STATUS
# ══════════════════════════════════════════════════════════

def get_battery_status() -> str:
    """Get battery status (laptops)."""
    ps = (
        "Get-WmiObject Win32_Battery | "
        "Select-Object EstimatedChargeRemaining, BatteryStatus | "
        "Format-List"
    )
    result = run_shell(ps, powershell=True)
    if not result.strip() or "No instances" in result:
        return "🔌 No battery detected (desktop PC)."
    return f"🔋 Battery: {result.strip()}"


# ══════════════════════════════════════════════════════════
#  RECYCLE BIN
# ══════════════════════════════════════════════════════════

def empty_recycle_bin() -> str:
    """Empty the Windows Recycle Bin."""
    ps = "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
    run_shell(ps, powershell=True)
    return "🗑️ Recycle Bin emptied."


# ══════════════════════════════════════════════════════════
#  STARTUP APPS
# ══════════════════════════════════════════════════════════

def list_startup_apps() -> str:
    """List programs that run at startup."""
    ps = (
        "Get-CimInstance Win32_StartupCommand | "
        "Select-Object Name, Command, Location | "
        "Format-Table -AutoSize"
    )
    return run_shell(ps, powershell=True)


# ══════════════════════════════════════════════════════════
#  BLUETOOTH
# ══════════════════════════════════════════════════════════

def toggle_bluetooth() -> str:
    """Toggle Bluetooth on/off."""
    ps = (
        "$radio = Get-PnpDevice -Class Bluetooth | Where-Object {$_.FriendlyName -notlike '*Radio*'} | Select-Object -First 1; "
        "if($radio.Status -eq 'OK'){Disable-PnpDevice -InstanceId $radio.InstanceId -Confirm:$false; 'Bluetooth OFF'}"
        "else{Enable-PnpDevice -InstanceId $radio.InstanceId -Confirm:$false; 'Bluetooth ON'}"
    )
    return run_shell(ps, powershell=True)
