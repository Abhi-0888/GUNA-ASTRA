"""
Agent 9: Testing Agent
Tests code and scripts produced by the Coding Agent.
"""

import os
import subprocess
import sys
import tempfile

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the Testing Agent for GUNA-ASTRA.

Your job:
1. Review code for syntax errors, logical bugs, and edge cases.
2. Write unit tests when appropriate.
3. Predict what will happen when the code runs.
4. Report: PASS or FAIL with clear reasons.

Structure your response:
- REVIEW: (what you checked)
- ISSUES FOUND: (list any bugs or concerns, or "None")
- TEST RESULT: PASS / FAIL / NEEDS REVIEW
- SUGGESTION: (how to fix if failed)
"""


class TestingAgent(BaseAgent):
    def __init__(self):
        super().__init__("TestingAgent", SYSTEM_PROMPT)

    def run(self, task: dict) -> dict:
        code = task.get("code", task.get("output", ""))
        description = task.get("description", "Test the provided code")

        self.logger.info(f"Testing: {description[:60]}")

        # 1. LLM code review
        review_prompt = f"Review and test this code:\n\n{code}\n\nTask it was meant to do: {description}"
        review = self.think(review_prompt)

        # 2. Try running it if it looks like Python
        run_result = ""
        if code and ("def " in code or "import " in code or "print(" in code):
            run_result = self._try_run(code)

        final_output = review
        if run_result:
            final_output += f"\n\n--- EXECUTION RESULT ---\n{run_result}"

        status = "success" if "PASS" in review.upper() else "failed"
        self.logger.info(f"Test result: {status}")
        return self.report(status, final_output, task)

    def _try_run(self, code: str) -> str:
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                path = f.name

            result = subprocess.run(
                [sys.executable, path], capture_output=True, text=True, timeout=15
            )
            os.unlink(path)
            return result.stdout or result.stderr or "(no output)"
        except subprocess.TimeoutExpired:
            return "ERROR: Script timed out (15s)."
        except Exception as e:
            return f"ERROR: {e}"
