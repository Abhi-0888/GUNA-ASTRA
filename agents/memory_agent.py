"""
Agent 3: Memory Agent
The ONLY agent that reads/writes to MongoDB.
v2: Also supports simple execute() interface for direct remember/recall.
"""

import utils.memory_db as db
from agents.base_agent import BaseAgent


class MemoryAgent(BaseAgent):
    def __init__(self):
        super().__init__("MemoryAgent", "You are the memory manager for GUNA-ASTRA.")

    def execute(self, task: str) -> str:
        """v2 interface: simple string-based memory operations."""
        t = task.lower()
        if "remember" in t or "save" in t or "store" in t:
            db.save_task({"goal": task[:200], "status": "memorized"})
            return f"✅ Saved to memory: {task[:100]}"
        if "recall" in t or "what did" in t or "do you remember" in t:
            recent = db.get_recent_tasks(5)
            if recent:
                return "Recent memory:\n" + "\n".join(f"• {r.get('goal', '?')}" for r in recent)
            return "Nothing in memory yet."
        return self._ask("You manage memory. Answer the user's memory-related request.", task)

    def run(self, task: dict) -> dict:
        action = task.get("action", "save")
        data = task.get("data", {})

        if action == "save_task":
            db.save_task(data)
            return self.report("success", "Task saved to memory.", task)

        elif action == "save_log":
            db.save_log(data.get("agent", "unknown"), data.get("message", ""), data.get("level", "INFO"))
            return self.report("success", "Log saved.", task)

        elif action == "save_conversation":
            db.save_conversation(data.get("role", "user"), data.get("content", ""), data.get("session_id", "default"))
            return self.report("success", "Conversation saved.", task)

        elif action == "get_history":
            history = db.get_recent_tasks(limit=data.get("limit", 10))
            return self.report("success", str(history), task)

        elif action == "get_conversation":
            conv = db.get_conversation_history(data.get("session_id", "default"))
            return self.report("success", str(conv), task)

        elif action == "summarize":
            history = db.get_recent_tasks(20)
            if not history:
                return self.report("success", "No task history found.", task)
            summary_prompt = f"Summarize what this AI system has been doing recently:\n{history}"
            summary = self.think(summary_prompt)
            return self.report("success", summary, task)

        else:
            return self.report("failed", f"Unknown action: {action}", task)
