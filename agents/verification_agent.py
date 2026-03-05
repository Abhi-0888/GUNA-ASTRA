"""
Agent 10: Verification Agent
Validates outputs for correctness, safety, and completeness.
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
