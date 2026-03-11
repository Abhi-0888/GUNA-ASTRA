"""
Agent 10: Verification Agent
Validates outputs for correctness, safety, and completeness.
v2: Short results pass through without LLM verification for speed.
"""

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the Verification Agent for GUNA-ASTRA.

Your job is to be the final quality checker before results reach the user.

You verify:
1. Is the output correct and accurate?
2. Is it safe? (No harmful content, no dangerous commands)
3. Is it complete? (Does it fully answer the goal?)
4. Are there any red flags or things the user should know?

Respond with:
- VERIFIED: YES / NO / PARTIAL
- SAFETY: SAFE / CAUTION / UNSAFE
- COMPLETENESS: COMPLETE / PARTIAL / INCOMPLETE
- NOTES: (Any important observations)
- FINAL VERDICT: APPROVED / NEEDS REVISION / REJECTED

If UNSAFE or REJECTED, explain clearly why.
"""


class VerificationAgent(BaseAgent):
    def __init__(self):
        super().__init__("VerificationAgent", SYSTEM_PROMPT)

    def execute(self, task: str) -> str:
        """v2 interface: pass through short results, verify long ones."""
        # For short/simple results, just pass through
        if len(task) < 300:
            if "RESULT:" in task:
                return task.split("RESULT:", 1)[1].strip()
            return task
        return self._ask(
            "You are a quality checker. Given a task and its result, verify the result is "
            "correct, safe, and addresses the original task. If it's good, return it as-is. "
            "If not, improve it. Return only the final response, no meta-commentary.",
            task
        )

    def run(self, task: dict) -> dict:
        goal = task.get("original_goal", "")
        outputs = task.get("outputs", "")

        self.logger.info("Verifying outputs...")

        prompt = f"""Original user goal:
{goal}

Collected outputs from all agents:
{outputs}

Please verify whether the goal has been met correctly and safely."""

        response = self.think(prompt)

        # Determine status from response
        if "REJECTED" in response.upper() or "UNSAFE" in response.upper():
            status = "failed"
        elif "PARTIAL" in response.upper():
            status = "partial"
        else:
            status = "success"

        self.logger.info(f"Verification: {status}")
        return self.report(status, response, task)
