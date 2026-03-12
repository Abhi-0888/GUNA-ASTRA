"""
Agent 5: Coding Agent
Writes, reviews, and debugs Python code and scripts.
"""

import re

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the Coding Agent for GUNA-ASTRA.

Your job:
1. Write clean, working Python code for the given task.
2. Always include comments explaining the code.
3. Handle errors gracefully with try/except.
4. When writing scripts, include a if __name__ == "__main__": block.
5. Return ONLY the code block — nothing else unless asked.

If asked to debug, identify the issue clearly, then provide the fixed code.
If generating a file (like PPT, Excel, PDF), use appropriate Python libraries:
- PowerPoint: python-pptx
- Excel: openpyxl
- PDF: reportlab
- Email: smtplib
"""


class CodingAgent(BaseAgent):
    def __init__(self):
        super().__init__("CodingAgent", SYSTEM_PROMPT)

    def run(self, task: dict) -> dict:
        description = task.get("description", "")
        context = task.get("context", "")

        self.logger.info(f"Writing code for: {description[:80]}")

        prompt = description
        if context:
            prompt = f"Context from previous steps:\n{context}\n\nTask: {description}"

        response = self.think(prompt)

        # Extract code block if wrapped in markdown
        code = self._extract_code(response)

        self.logger.info("Code generation complete.")
        return self.report("success", code or response, task)

    def _extract_code(self, text: str) -> str:
        """Extract code from markdown code fences if present."""
        pattern = r"```(?:python)?\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def fix_code(self, original_code: str, error_message: str) -> str:
        """
        Fix broken code using LLM. Returns ONLY the corrected code.
        Used by InterpreterEngine's self-correction loop.
        """
        self.logger.info(f"Fixing code error: {error_message[:100]}...")

        fix_prompt = f"""Fix this code that produced the following error:

CODE:
{original_code}

ERROR:
{error_message}

Return ONLY the fixed Python code. No explanation. No markdown fences. Just the working code."""

        # Use a focused system prompt for fixing
        old_prompt = self.system_prompt
        self.system_prompt = (
            "You are fixing broken Python code. Return ONLY the corrected code. "
            "No explanation. No markdown. Just the working Python code."
        )

        response = self.think(fix_prompt)
        self.system_prompt = old_prompt

        fixed = self._extract_code(response)
        self.logger.info("Code fix generated.")
        return fixed

    def generate_with_libraries(self, task: str, libraries: list) -> str:
        """
        Generate code with awareness of available libraries.
        """
        self.logger.info(f"Generating code with libraries: {libraries}")

        prompt = f"""Write Python code to: {task}
Available libraries: {', '.join(libraries)}
Use these libraries. Include pip install instructions as comments if needed.
Return ONLY the code."""

        response = self.think(prompt)
        return self._extract_code(response)
