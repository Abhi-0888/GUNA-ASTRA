"""
GUNA-ASTRA Interpreter Engine
Autonomous code execution loop with real-time streaming, self-correction,
multi-language support, and safety scanning.
"""

import os
import sys
import re
import subprocess
import tempfile
import threading
from datetime import datetime
from utils.logger import get_logger
from config.settings import (
    CODE_EXECUTION_MAX_RETRIES, PYTHON_TIMEOUT,
    SHELL_TIMEOUT, JS_TIMEOUT
)

logger = get_logger("InterpreterEngine")


# ── Danger Patterns for Safety Scanner ─────────────────────────────────────────

DANGER_PATTERNS = [
    (r"os\.remove\s*\(", "Deletes a file (os.remove)"),
    (r"shutil\.rmtree\s*\(", "Recursively deletes a directory (shutil.rmtree)"),
    (r"os\.rmdir\s*\(", "Removes a directory (os.rmdir)"),
    (r"os\.system\s*\(.*(rm\s+-rf|del\s+/|format)", "Dangerous shell command via os.system"),
    (r"subprocess.*rm\s+-rf", "Dangerous: rm -rf via subprocess"),
    (r"format\s*\(\s*['\"][A-Z]:", "Potential disk formatting"),
    (r"DROP\s+TABLE", "SQL: DROP TABLE"),
    (r"DELETE\s+FROM", "SQL: DELETE FROM"),
    (r"\bsudo\b", "Uses sudo (elevated privileges)"),
    (r"socket\.connect", "Network outbound connection"),
    (r"smtplib", "Sending email via SMTP"),
    (r"os\.startfile\s*\(", "Opens file with OS handler"),
    (r"winreg|_winreg|RegSetValue", "Windows registry modification"),
    (r"shutdown\s+/[sr]", "System shutdown/restart command"),
]

_COMPILED_DANGERS = [(re.compile(p, re.IGNORECASE), reason) for p, reason in DANGER_PATTERNS]


def scan_code_for_danger(code: str) -> list:
    """
    Scan code for dangerous patterns.
    Returns: list of {"line_num": int, "line": str, "reason": str}
    """
    dangers = []
    for i, line in enumerate(code.split("\n"), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for pattern, reason in _COMPILED_DANGERS:
            if pattern.search(line):
                dangers.append({
                    "line_num": i,
                    "line": stripped,
                    "reason": reason
                })
                break  # One danger per line is enough
    return dangers


def detect_language(code: str) -> str:
    """Auto-detect the programming language from code content."""
    code_lower = code.strip().lower()

    # Shell indicators
    if code_lower.startswith("#!/bin/bash") or code_lower.startswith("#!/bin/sh"):
        return "shell"
    shell_keywords = ["rm -rf", "mkdir -p", "cd ", "chmod ", "chown ",
                      "apt-get", "yum ", "brew ", "echo $"]
    if any(kw in code_lower for kw in shell_keywords):
        return "shell"

    # JavaScript indicators
    js_keywords = ["console.log", "const ", "let ", "require(", "module.exports",
                   "async function", "document.", "window."]
    if any(kw in code_lower for kw in js_keywords):
        return "javascript"

    # Default to Python
    return "python"


class InterpreterEngine:
    """Autonomous code execution engine with streaming and self-correction."""

    def __init__(self):
        self.logger = logger
        self.working_directory = os.path.expanduser("~")
        self._dir_history = [self.working_directory]

    # ── Working Directory Management ──────────────────────────────────────────

    def set_working_directory(self, path: str) -> str:
        """Change working directory. Returns the new path."""
        expanded = os.path.expanduser(path)
        if not os.path.isabs(expanded):
            expanded = os.path.join(self.working_directory, expanded)
        expanded = os.path.abspath(expanded)

        if os.path.isdir(expanded):
            self._dir_history.append(self.working_directory)
            self.working_directory = expanded
            return expanded
        return None

    def go_back(self) -> str:
        """Go to previous directory."""
        if self._dir_history:
            self.working_directory = self._dir_history.pop()
        return self.working_directory

    # ── Real-Time Streaming Execution ─────────────────────────────────────────

    def _stream_process(self, cmd: list, timeout: int = 60, cwd: str = None) -> dict:
        """
        Execute a command with real-time stdout/stderr streaming.
        Returns: {"returncode": int, "stdout": str, "stderr": str}
        """
        cwd = cwd or self.working_directory
        stdout_lines = []
        stderr_lines = []

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace"
            )

            # Read stderr in a background thread
            def read_stderr():
                try:
                    for line in iter(process.stderr.readline, ""):
                        if line:
                            stderr_lines.append(line.rstrip())
                            print(f"\033[91m  {line.rstrip()}\033[0m")
                except Exception:
                    pass

            err_thread = threading.Thread(target=read_stderr, daemon=True)
            err_thread.start()

            # Stream stdout in main thread
            try:
                for line in iter(process.stdout.readline, ""):
                    if line:
                        stdout_lines.append(line.rstrip())
                        print(f"\033[93m  {line.rstrip()}\033[0m")
            except Exception:
                pass

            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stderr_lines.append(f"[TIMEOUT] Process killed after {timeout}s")
                print(f"\033[91m  [TIMEOUT] Process killed after {timeout}s\033[0m")

            err_thread.join(timeout=2)

            return {
                "returncode": process.returncode or -1,
                "stdout": "\n".join(stdout_lines),
                "stderr": "\n".join(stderr_lines)
            }

        except FileNotFoundError as e:
            return {"returncode": -1, "stdout": "", "stderr": f"Command not found: {e}"}
        except Exception as e:
            return {"returncode": -1, "stdout": "", "stderr": str(e)}

    # ── Python Execution ──────────────────────────────────────────────────────

    def execute_python(self, code: str, timeout: int = None) -> dict:
        """Execute Python code with real-time streaming."""
        timeout = timeout or PYTHON_TIMEOUT
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8",
            dir=self.working_directory
        )
        try:
            tmp.write(code)
            tmp.close()

            print(f"\033[90m  ─── Running: {os.path.basename(tmp.name)} ───\033[0m")
            start = datetime.now()

            result = self._stream_process(
                [sys.executable, tmp.name],
                timeout=timeout,
                cwd=self.working_directory
            )

            elapsed = (datetime.now() - start).total_seconds()
            status = "SUCCESS" if result["returncode"] == 0 else "ERROR"
            color = "\033[92m" if status == "SUCCESS" else "\033[91m"
            print(f"\033[90m  ─── Result: {color}{status}\033[90m ({elapsed:.1f}s) ───\033[0m")

            result["elapsed"] = elapsed
            return result
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    # ── Shell Execution ───────────────────────────────────────────────────────

    def execute_shell(self, command: str, cwd: str = None) -> dict:
        """Execute a shell command with streaming."""
        import platform
        timeout = SHELL_TIMEOUT

        print(f"\033[90m  ─── Running: {command[:60]} ───\033[0m")
        start = datetime.now()

        if platform.system() == "Windows":
            cmd = ["cmd", "/c", command]
        else:
            cmd = ["bash", "-c", command]

        result = self._stream_process(cmd, timeout=timeout, cwd=cwd or self.working_directory)

        elapsed = (datetime.now() - start).total_seconds()
        status = "SUCCESS" if result["returncode"] == 0 else "ERROR"
        color = "\033[92m" if status == "SUCCESS" else "\033[91m"
        print(f"\033[90m  ─── Result: {color}{status}\033[90m ({elapsed:.1f}s) ───\033[0m")

        result["elapsed"] = elapsed
        result["success"] = result["returncode"] == 0
        result["output"] = result["stdout"] or result["stderr"] or "(no output)"
        result["action"] = "RUN_COMMAND"
        return result

    # ── JavaScript Execution ──────────────────────────────────────────────────

    def execute_javascript(self, code: str, timeout: int = None) -> dict:
        """Execute JavaScript code via Node.js."""
        timeout = timeout or JS_TIMEOUT
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False, encoding="utf-8"
        )
        try:
            tmp.write(code)
            tmp.close()

            print(f"\033[90m  ─── Running: {os.path.basename(tmp.name)} ───\033[0m")
            start = datetime.now()

            result = self._stream_process(
                ["node", tmp.name],
                timeout=timeout,
                cwd=self.working_directory
            )

            elapsed = (datetime.now() - start).total_seconds()
            status = "SUCCESS" if result["returncode"] == 0 else "ERROR"
            color = "\033[92m" if status == "SUCCESS" else "\033[91m"
            print(f"\033[90m  ─── Result: {color}{status}\033[90m ({elapsed:.1f}s) ───\033[0m")

            result["elapsed"] = elapsed
            return result
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    # ── Auto-Language Execution ───────────────────────────────────────────────

    def execute_code(self, code: str, language: str = None) -> dict:
        """Execute code in any supported language (auto-detects if not specified)."""
        lang = language or detect_language(code)

        if lang == "python":
            return self.execute_python(code)
        elif lang == "shell":
            return self.execute_shell(code)
        elif lang == "javascript":
            return self.execute_javascript(code)
        else:
            return self.execute_python(code)

    # ── Self-Correcting Execution Loop ────────────────────────────────────────

    def execute_with_retry(self, code: str, task_description: str = "",
                           language: str = None) -> dict:
        """
        Execute code with automatic self-correction.
        If code fails, asks CodingAgent to fix it, up to MAX_RETRIES attempts.
        """
        max_attempts = CODE_EXECUTION_MAX_RETRIES
        current_code = code
        last_error = ""

        for attempt in range(1, max_attempts + 1):
            print(f"\n\033[96m[GUNA-ASTRA] Running code (attempt {attempt}/{max_attempts})...\033[0m")

            # Safety check
            dangers = scan_code_for_danger(current_code)
            if dangers:
                print(f"\n\033[93m⚠️ Potentially dangerous operations detected:\033[0m")
                for d in dangers:
                    print(f"\033[93m  Line {d['line_num']}: {d['line']}\033[0m")
                    print(f"\033[90m  Reason: {d['reason']}\033[0m")
                try:
                    choice = input("\n\033[93mProceed? (yes/no): \033[0m").strip().lower()
                    if choice not in ("yes", "y"):
                        return {
                            "returncode": -1,
                            "stdout": "",
                            "stderr": "Execution cancelled by user.",
                            "success": False,
                            "output": "Code execution cancelled by user due to safety concerns.",
                            "action": "CODE_EXECUTION"
                        }
                except EOFError:
                    return {
                        "returncode": -1, "stdout": "", "stderr": "Cancelled.",
                        "success": False, "output": "Cancelled.", "action": "CODE_EXECUTION"
                    }

            result = self.execute_code(current_code, language)

            if result["returncode"] == 0:
                return {
                    "returncode": 0,
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "success": True,
                    "output": result.get("stdout", "") or "Code executed successfully.",
                    "action": "CODE_EXECUTION",
                    "attempts": attempt
                }

            # Error — try to fix
            last_error = result.get("stderr", "") or result.get("stdout", "")
            self.logger.warning(f"Attempt {attempt} failed: {last_error[:200]}")

            if attempt < max_attempts:
                print(f"\033[93m[GUNA-ASTRA] Error detected. Asking Coding Agent to fix...\033[0m")
                try:
                    from agents.coding_agent import CodingAgent
                    coder = CodingAgent()
                    fixed = coder.fix_code(current_code, last_error)
                    if fixed and fixed != current_code:
                        current_code = fixed
                        print(f"\033[92m[GUNA-ASTRA] Code fixed. Retrying...\033[0m")
                    else:
                        print(f"\033[91m[GUNA-ASTRA] Could not fix the code.\033[0m")
                        break
                except Exception as e:
                    self.logger.error(f"Fix attempt failed: {e}")
                    break

        return {
            "returncode": -1,
            "stdout": "",
            "stderr": last_error,
            "success": False,
            "output": f"Code execution failed after {max_attempts} attempts.\nLast error: {last_error[:500]}",
            "action": "CODE_EXECUTION",
            "attempts": max_attempts
        }
