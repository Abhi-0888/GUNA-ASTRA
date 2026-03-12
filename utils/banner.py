"""
GUNA-ASTRA Banner — startup display with mode and version info.
Box-drawing font for GUNA/ASTRA — renders cleanly in all terminals.
"""

import re
import shutil
import sys
from datetime import datetime

# Force UTF-8 stdout to correctly display Sanskrit and symbols on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ── ANSI ─────────────────────────────────────────────────────────────────────
R = "\033[0m"
CYAN = "\033[96m"
TEAL = "\033[36m"
PUR = "\033[35m"
BPUR = "\033[95m"
GOLD = "\033[38;5;220m"
ORANGE = "\033[38;5;214m"
GRAY = "\033[90m"
DGRAY = "\033[38;5;238m"
LGRAY = "\033[38;5;244m"
MGRAY = "\033[37m"
GREEN = "\033[92m"
YELLOW = "\033[93m"


def _vis(s):
    """Visible length (strips ANSI codes)."""
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def _center(text, width):
    v = _vis(text)
    p = max(0, width - v)
    return " " * (p // 2) + text + " " * (p - p // 2)


# ═════════════════════════════════════════════════════════════════════════════
#  GUNA  —  box-drawing block font (with extra spacing for clarity)
# ═════════════════════════════════════════════════════════════════════════════
GUNA_ART = [
    f"{CYAN} ██████╗  ██╗   ██╗ ███╗   ██╗  █████╗ {R}",
    f"{CYAN}██╔════╝  ██║   ██║ ████╗  ██║ ██╔══██╗{R}",
    f"{TEAL}██║  ███╗ ██║   ██║ ██╔██╗ ██║ ███████║{R}",
    f"{TEAL}██║   ██║ ██║   ██║ ██║╚██╗██║ ██╔══██║{R}",
    f"{CYAN}╚██████╔╝ ╚██████╔╝ ██║ ╚████║ ██║  ██║{R}",
    f"{CYAN} ╚═════╝   ╚═════╝  ╚═╝  ╚═══╝ ╚═╝  ╚═╝{R}",
]

# ═════════════════════════════════════════════════════════════════════════════
#  ASTRA  —  box-drawing block font (with extra spacing for clarity)
# ═════════════════════════════════════════════════════════════════════════════
ASTRA_ART = [
    f"{BPUR} █████╗  ███████╗ ████████╗ ██████╗   █████╗ {R}",
    f"{BPUR}██╔══██╗ ██╔════╝ ╚══██╔══╝ ██╔══██╗ ██╔══██╗{R}",
    f"{PUR}███████║ ███████╗    ██║    ██████╔╝ ███████║{R}",
    f"{PUR}██╔══██║ ╚════██║    ██║    ██╔══██╗ ██╔══██║{R}",
    f"{BPUR}██║  ██║ ███████║    ██║    ██║  ██║ ██║  ██║{R}",
    f"{BPUR}╚═╝  ╚═╝ ╚══════╝    ╚═╝    ╚═╝  ╚═╝ ╚═╝  ╚═╝{R}",
]

GUNA_VIS = max(_vis(l) for l in GUNA_ART)
ASTRA_VIS = max(_vis(l) for l in ASTRA_ART)
ART_VIS = max(GUNA_VIS, ASTRA_VIS)


# ═════════════════════════════════════════════════════════════════════════════
#  MERKABA  —  Star Tetrahedron / Merkaba
# ═════════════════════════════════════════════════════════════════════════════

_S = MGRAY  # solid lines (bright gray)
_D = LGRAY  # dashed lines (dim gray)

MERKABA_ROWS = [
    f"{_S}           /\\           {R}",
    f"{_S}          /  \\          {R}",
    f"{_S}         /    \\         {R}",
    f"{_D} . . . . /. . .\\ . . .  {R}",
    f"{_S}       / /      \\ \\     {R}",
    f"{_S}      / /        \\ \\    {R}",
    f"{_D} . . / /. . . . ..\\ \\ . {R}",
    f"{_S}    / /    /\\      \\ \\  {R}",
    f"{_S}   / /    /  \\      \\ \\ {R}",
    f"{_D}-/ /.---/----\\------\\ /-{R}",
    f"{_S}   \\ \\    \\  /      / / {R}",
    f"{_S}    \\ \\    \\/      / /  {R}",
    f"{_D} . . \\ \\ . . . . / / .  {R}",
    f"{_S}      \\ \\        / /    {R}",
    f"{_S}       \\ \\      / /     {R}",
    f"{_D} . . . . \\. . ./. . . . {R}",
    f"{_S}         \\    /         {R}",
    f"{_S}          \\  /          {R}",
    f"{_S}           \\/           {R}",
]

MERKABA_VIS = 25


# ═════════════════════════════════════════════════════════════════════════════
#  BANNER
# ═════════════════════════════════════════════════════════════════════════════


def print_banner():
    cols = shutil.get_terminal_size((120, 24)).columns
    time_now = datetime.now().strftime("%H:%M:%S")

    gap = 4
    show_geo = cols >= (2 * (MERKABA_VIS + gap) + ART_VIS)
    side_w = MERKABA_VIS + gap

    # ── Decoration symbols ────────────────────────────────────────────────
    om = f"{PUR}ॐ{R}"
    swas = f"{ORANGE}卐{R}"
    dot1 = f"{ORANGE}•{R}"
    dot2 = f"{BPUR}◆{R}"

    top_sym = (
        f"  {om}  "
        f"{dot1} {dot1}  {dot1} {dot1}  {dot1}  "
        f"{swas}  "
        f"{dot1}  {dot1} {dot1}  {dot1} {dot1}"
        f"  {om}  "
    )
    bot_sym = (
        f"  {om}  "
        f"{dot2} {dot2}  {dot2}  "
        f"{swas}  "
        f"{dot2}  {dot2} {dot2}"
        f"  {om}  "
    )

    # Sanskrit
    # अहम् यत्र तत्र सर्वत्र
    sanskrit = f"{GOLD}  अहम् यत्र तत्र सर्वत्र  {R}"

    # ── Build art block (center column) ──────────────────────────────────
    art_block = (
        [""]
        + [top_sym]
        + [""]
        + GUNA_ART
        + [""]
        + ASTRA_ART
        + [""]
        + [sanskrit]
        + [""]
        + [bot_sym]
        + [""]
    )

    # ── Align Merkaba vertically centered vs art block ────────────────────
    geo_h = len(MERKABA_ROWS)
    art_h = len(art_block)
    geo_top = max(0, (art_h - geo_h) // 2)

    def get_geo(i):
        j = i - geo_top
        return MERKABA_ROWS[j] if 0 <= j < geo_h else (" " * MERKABA_VIS)

    # ── Print ─────────────────────────────────────────────────────────────
    print()
    for i, art in enumerate(art_block):
        av = _vis(art)
        lpad = max(0, (ART_VIS - av) // 2)
        rpad = max(0, ART_VIS - av - lpad)
        astr = " " * lpad + art + " " * rpad

        if show_geo:
            gl = get_geo(i)
            glv = _vis(gl)
            left = gl + " " * max(0, side_w - glv)
            right = " " * max(0, side_w - glv) + gl
            total = side_w * 2 + ART_VIS
            outer = max(0, (cols - total) // 2)
            print(" " * outer + left + astr + right)
        else:
            print(_center(astr, cols))

    # ── Info box ──────────────────────────────────────────────────────────
    box_w = min(66, cols - 2)
    iw = box_w - 2

    def bline(txt, c=DGRAY):
        v = _vis(txt)
        return f"{GRAY}║{R}{c}{txt}{' ' * max(0, iw - v)}{R}{GRAY}║{R}"

    print()
    print(" " + GRAY + "╔" + "═" * (box_w - 2) + "╗" + R)
    print(
        bline(
            f"  {YELLOW}⚡ NORMAL MODE {GRAY} │ {R}Fast direct OS control (default)      "
        )
    )
    print(
        bline(
            f"  {CYAN}🤖 WORKING MODE{GRAY} │ {R}Full 11-agent pipeline for complex tasks"
        )
    )
    print(" " + GRAY + "╠" + "═" * (box_w - 2) + "╣" + R)
    print(bline(f"  {DGRAY}Quick Start:", DGRAY))
    print(
        bline(f'  {DGRAY}• Type any command naturally  (e.g. "open chrome")    ', DGRAY)
    )
    print(
        bline(
            f'  {DGRAY}• "mode working" → switch to full AI pipeline          ', DGRAY
        )
    )
    print(
        bline(
            f'  {DGRAY}• "help" → all commands   •   "status" → system health ', DGRAY
        )
    )
    print(
        bline(
            f'  {DGRAY}• "exit" → quit                                        ', DGRAY
        )
    )
    print(" " + GRAY + "╚" + "═" * (box_w - 2) + "╝" + R)
    print()
    print(f"  {GRAY}Started at {time_now}{R}\n")


if __name__ == "__main__":
    print_banner()
