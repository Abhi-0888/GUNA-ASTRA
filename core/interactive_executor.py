"""
GUNA-ASTRA Interactive Executor
Human-in-the-loop code execution for Working Mode.
Shows code to user, asks for confirmation, then runs if approved.
"""

from core.interpreter_engine import InterpreterEngine
from utils.logger import get_logger

logger = get_logger("InteractiveExecutor")


class InteractiveExecutor:
    """Confirm-and-run executor for Working Mode code."""

    def __init__(self, engine: InterpreterEngine = None):
        self.engine = engine or InterpreterEngine()

    def confirm_and_run(
        self, code: str, language: str = "python", context: str = ""
    ) -> dict:
        """
        Show code to user, ask for confirmation, then run if approved.
        Options: [Y] Run, [N] Skip, [E] Edit, [C] Copy to clipboard
        """
        print("\n" + "─" * 60)
        print(f"\033[95m[GUNA-ASTRA] Generated {language.upper()} Code:\033[0m")
        print("─" * 60)

        # Show code with line numbers
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            print(f"\033[90m{i:3}│\033[0m \033[93m{line}\033[0m")

        print("─" * 60)
        if context:
            print(f"\033[96mContext: {context[:100]}\033[0m")

        print("\n\033[93mShould I run this code?\033[0m")
        print("  [Y] Yes, run it")
        print("  [N] No, skip")
        print("  [E] Edit first")
        print("  [C] Copy to clipboard")

        try:
            choice = input("\nYour choice (Y/N/E/C): ").strip().upper()
        except EOFError:
            choice = "N"

        if choice == "Y" or choice == "":
            return self.engine.execute_with_retry(code, context, language)

        elif choice == "E":
            print(
                "\nPaste your edited code below. Type '###END###' on a new line when done:"
            )
            edited_lines = []
            try:
                while True:
                    line = input()
                    if line.strip() == "###END###":
                        break
                    edited_lines.append(line)
            except EOFError:
                pass

            if edited_lines:
                edited_code = "\n".join(edited_lines)
                return self.engine.execute_with_retry(edited_code, context, language)
            else:
                return {
                    "success": False,
                    "output": "No code provided after editing.",
                    "action": "skip",
                }

        elif choice == "C":
            try:
                import pyperclip

                pyperclip.copy(code)
                print("\033[92m✅ Code copied to clipboard.\033[0m")
            except ImportError:
                # Fallback for Windows
                try:
                    import subprocess

                    process = subprocess.Popen(
                        ["powershell", "-Command", "Set-Clipboard"],
                        stdin=subprocess.PIPE,
                        text=True,
                    )
                    process.communicate(input=code)
                    print("\033[92m✅ Code copied to clipboard.\033[0m")
                except Exception:
                    print("\033[91mCould not copy to clipboard.\033[0m")
            return {
                "success": True,
                "output": "Code copied to clipboard.",
                "action": "copy",
            }

        else:  # N or anything else
            return {
                "success": True,
                "output": "Code execution skipped by user.",
                "action": "skip",
            }
