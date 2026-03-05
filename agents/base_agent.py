"""
Base class for all GUNA-ASTRA agents.
Every agent inherits from this.
"""

from utils.llm_client import query_llm
from utils.logger import get_logger
from config.settings import AGENT_MAX_RETRIES


class BaseAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.logger = get_logger(name)

    def think(self, prompt: str) -> str:
        """Send prompt to LLM and return response."""
        self.logger.info(f"Thinking: {prompt[:100]}...")
        for attempt in range(1, AGENT_MAX_RETRIES + 1):
            result = query_llm(prompt, system_prompt=self.system_prompt)
            if result and not result.startswith("ERROR"):
                return result
            self.logger.warning(f"Attempt {attempt} failed. Retrying...")
        return f"[{self.name}] Failed to get a response after {AGENT_MAX_RETRIES} attempts."

    def run(self, task: dict) -> dict:
        """Override this in each agent."""
        raise NotImplementedError(f"{self.name} must implement run()")

    def report(self, status: str, output: str, task: dict) -> dict:
        """Standardized result format."""
        return {
            "agent": self.name,
            "task": task.get("description", ""),
            "status": status,   # "success" | "failed" | "pending_confirmation"
            "output": output
        }
