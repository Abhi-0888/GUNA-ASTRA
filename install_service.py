"""
GUNA-ASTRA Service Installer
Registers/unregisters GUNA-ASTRA to auto-start when Windows boots.

Usage:
    py install_service.py              — install auto-start
    py install_service.py --uninstall  — remove auto-start
    py install_service.py --status     — check if installed
"""

import os
import sys
import subprocess

TASK_NAME = "GUNA-ASTRA"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable  # e.g., E:\Python312\python.exe
PYTHONW_EXE = PYTHON_EXE.replace("python.exe", "pythonw.exe")
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "main.py")

# Use pythonw.exe if available (no console window), else python.exe
if not os.path.isfile(PYTHONW_EXE):
    PYTHONW_EXE = PYTHON_EXE


def install():
    """Register GUNA-ASTRA to start at user login."""
    cmd = (
        f'schtasks /create /tn "{TASK_NAME}" '
        f'/tr "\\"{PYTHONW_EXE}\\" \\"{MAIN_SCRIPT}\\" --service" '
        f'/sc ONLOGON /rl HIGHEST /f'
    )
    print(f"\n[GUNA-ASTRA] Registering auto-start...")
    print(f"  Python:  {PYTHONW_EXE}")
    print(f"  Script:  {MAIN_SCRIPT}")
    print(f"  Trigger: On user login")
    print()

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ GUNA-ASTRA registered for auto-start!")
        print("   It will launch automatically when you log in.")
        print(f"   To start it now: py main.py --service")
    else:
        print(f"❌ Failed to register: {result.stderr.strip()}")
        print("   Try running this script as Administrator.")


def uninstall():
    """Remove GUNA-ASTRA from auto-start."""
    cmd = f'schtasks /delete /tn "{TASK_NAME}" /f'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ GUNA-ASTRA removed from auto-start.")
    else:
        print(f"❌ Could not remove: {result.stderr.strip()}")


def status():
    """Check if auto-start is registered."""
    cmd = f'schtasks /query /tn "{TASK_NAME}" 2>nul'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if TASK_NAME in result.stdout:
        print("✅ GUNA-ASTRA is registered for auto-start.")
        # Show relevant line
        for line in result.stdout.splitlines():
            if TASK_NAME in line:
                print(f"   {line.strip()}")
    else:
        print("❌ GUNA-ASTRA is NOT registered for auto-start.")
        print(f"   Run: py install_service.py")


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    elif "--status" in sys.argv:
        status()
    else:
        install()
