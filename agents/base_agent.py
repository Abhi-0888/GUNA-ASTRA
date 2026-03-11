"""
Base class for all GUNA-ASTRA agents.
Every agent inherits from this.

Supports two calling patterns:
  - v1: agent.run(task_dict) → returns dict with status/output
  - v2: agent.execute(task_str) → returns string result directly
"""

from utils.llm_client import query_llm
from utils.logger import get_logger
from config.settings import AGENT_MAX_RETRIES


class BaseAgent:
    def __init__(self, name: str = None, system_prompt: str = ""):
        self.name = name or self.__class__.__name__
        self.system_prompt = system_prompt
        self.logger = get_logger(self.name)
        # v2 compat: llm and memory can be set by v2 orchestrator
        self.llm = None
        self.memory = None

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

    def execute(self, task: str) -> str:
        """v2 interface: takes a string task, returns a string result.
        Delegates to run() by wrapping in a dict, then extracts output."""
        try:
            result = self.run({"description": task, "original_goal": task})
            return result.get("output", str(result))
        except NotImplementedError:
            return self._ask(self.system_prompt, task)

    def _ask(self, system: str, user: str) -> str:
        """v2 LLM helper: try v2 LLMClient first, fallback to query_llm."""
        try:
            if self.llm is not None:
                return self.llm.ask(system=system, user=user)
            return query_llm(user, system_prompt=system)
        except Exception as e:
            return f"[{self.name}] LLM error: {e}"

    def report(self, status: str, output: str, task: dict) -> dict:
        """Standardized result format."""
        return {
            "agent": self.name,
            "task": task.get("description", ""),
            "status": status,   # "success" | "failed" | "pending_confirmation"
            "output": output
        }
