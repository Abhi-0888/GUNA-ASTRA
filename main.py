"""
GUNA-ASTRA v2.0
Main entry point — CLI interactive mode and background service mode.
Includes startup health checks and auto-installation of missing packages.
"""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ── Auto-Install Missing Packages ─────────────────────────────────────────────

REQUIRED_PACKAGES = {
    "requests": "requests",
    "pymongo": "pymongo",
    "PIL": "Pillow",
    "bs4": "beautifulsoup4",
}

OPTIONAL_PACKAGES = {
    "pyautogui": "pyautogui",
    "psutil": "psutil",
    "pyperclip": "pyperclip",
}


def install_missing_packages():
    """Check and install required packages. Warn about optional ones."""
    missing_required = []
    missing_optional = []

    for module, pkg in REQUIRED_PACKAGES.items():
        try:
            __import__(module)
        except ImportError:
            missing_required.append(pkg)

    for module, pkg in OPTIONAL_PACKAGES.items():
        try:
            __import__(module)
        except ImportError:
            missing_optional.append(pkg)

    if missing_required:
        print(f"\033[93m[Setup] Installing missing required packages: {', '.join(missing_required)}\033[0m")
        import subprocess
        for pkg in missing_required:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])
        print(f"\033[92m[Setup] ✅ Required packages installed.\033[0m")

    if missing_optional:
        print(f"\033[90m[Setup] Optional packages not installed: {', '.join(missing_optional)}\033[0m")
        print(f"\033[90m        Install with: pip install {' '.join(missing_optional)}\033[0m")


# ── Health Check ───────────────────────────────────────────────────────────────

def run_health_check():
    """Run system health check at startup."""
    from utils.llm_client import check_ollama_health
    from utils.memory_db import MONGO_AVAILABLE

    checks = []

    # Ollama
    if check_ollama_health():
        checks.append("  ✅ Ollama — Online")
    else:
        checks.append("  ❌ Ollama — Offline (run: ollama serve)")

    # MongoDB
    if MONGO_AVAILABLE:
        checks.append("  ✅ MongoDB — Connected")
    else:
        checks.append("  ⚠️  MongoDB — Offline (using in-memory fallback)")

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(f"  ✅ Python {py_ver}")

    # Optional packages
    for name, pkg in [("pyautogui", "pyautogui"), ("psutil", "psutil")]:
        try:
            __import__(name)
            checks.append(f"  ✅ {pkg} — Available")
        except ImportError:
            checks.append(f"  ⚠️  {pkg} — Not installed")

    print("\n\033[96m[Health Check]\033[0m")
    for c in checks:
        print(c)
    print()


# ── Main CLI Entry ─────────────────────────────────────────────────────────────

def main_cli():
    """Interactive CLI mode."""
    import argparse
    from utils.banner import print_banner
    from core.orchestrator import GUNAASTRAOrchestrator
    
    parser = argparse.ArgumentParser(description="GUNA-ASTRA AI Assistant")
    parser.add_argument("--voice", action="store_true", help="Start the background Voice Listener on boot")
    args = parser.parse_args()

    # Startup sequence
    install_missing_packages()
    print_banner()
    run_health_check()

    # Run orchestrator
    orchestrator = GUNAASTRAOrchestrator()
    
    if args.voice:
        import config.settings
        config.settings.VOICE_MODE_ENABLED = True
        orchestrator.start_voice_service()
        
    orchestrator.run()


# ── Background Service Mode ───────────────────────────────────────────────────

def main_service():
    """Run as FastAPI background service."""
    try:
        from api.server import start_api_server
        start_api_server()
    except ImportError:
        print("\033[91m[Error] API server module not found. Run in CLI mode instead.\033[0m")
        print("\033[90m  python main.py\033[0m")
        sys.exit(1)


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--service" in sys.argv or "--api" in sys.argv:
        main_service()
    else:
        main_cli()
