"""
Agent 2: Task Dispatcher
Routes tasks to the correct execution agent.
"""

from agents.base_agent import BaseAgent
from utils.logger import get_logger

logger = get_logger("TaskDispatcher")

# Map agent names to their module paths (loaded lazily to avoid circular imports)
AGENT_REGISTRY = {
    "ResearchAgent": "agents.research_agent.ResearchAgent",
    "CodingAgent": "agents.coding_agent.CodingAgent",
    "SystemAgent": "agents.system_agent.SystemAgent",
    "DataAgent": "agents.data_agent.DataAgent",
    "CyberAgent": "agents.cyber_agent.CyberAgent",
    "MemoryAgent": "agents.memory_agent.MemoryAgent",
}


def _load_agent(agent_name: str):
    """Dynamically load an agent class by name."""
    import importlib

    path = AGENT_REGISTRY.get(agent_name)
    if not path:
        raise ValueError(f"Unknown agent: {agent_name}")
    module_path, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


class TaskDispatcher(BaseAgent):
    def __init__(self):
        super().__init__("TaskDispatcher", "")

    def dispatch(self, task: dict) -> dict:
        """
        Dispatch a single task to its assigned agent.
        Returns the agent's result.
        """
        agent_name = task.get("agent", "")
        description = task.get("description", "")

        if not agent_name:
            logger.error(f"Task has no assigned agent: {task}")
            return {
                "agent": "TaskDispatcher",
                "status": "failed",
                "output": "No agent assigned.",
            }

        logger.info(f"Dispatching task to {agent_name}: {description[:80]}")

        try:
            agent = _load_agent(agent_name)
            return agent.run(task)
        except Exception as e:
            logger.error(f"Dispatch error for {agent_name}: {e}")
            return {
                "agent": agent_name,
                "task": description,
                "status": "failed",
                "output": str(e),
            }
