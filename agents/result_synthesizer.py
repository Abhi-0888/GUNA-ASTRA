"""
Agent 11: Result Synthesizer
Combines all agent outputs into a clear, user-friendly final response.
Mode-aware: brief responses for Normal Mode, full reports for Working Mode.
"""

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the Result Synthesizer for GUNA-ASTRA.

Your job is to take the outputs from multiple AI agents and produce ONE clear, 
well-organized response for the user.

Rules:
1. Write as if you are the GUNA-ASTRA system speaking directly to the user.
2. Be concise but complete.
3. Use clear sections if needed (e.g., SUMMARY, KEY FINDINGS, OUTPUT FILES).
4. Highlight any important actions taken (files created, URLs opened, etc.).
5. Note any issues or things that need the user's attention.
6. End with a confirmation of what was accomplished.

Tone: professional, helpful, and clear. Never robotic.
"""

SYSTEM_PROMPT_BRIEF = """You are the Result Synthesizer for GUNA-ASTRA.
Provide a very brief, one-line confirmation of what was done.
Be concise — one or two sentences max. Use emojis for clarity.
Examples: "✅ File created: test.py" or "✅ Volume set to 75%."
"""


class ResultSynthesizer(BaseAgent):
    def __init__(self):
        super().__init__("ResultSynthesizer", SYSTEM_PROMPT)

    def run(self, task: dict) -> dict:
        goal = task.get("original_goal", "")
        results = task.get("results", [])
        mode = task.get("mode", "working")

        self.logger.info(f"Synthesizing final response (mode: {mode})...")

        results_text = ""
        for i, r in enumerate(results, 1):
            agent = r.get("agent", "Unknown")
            output = r.get("output", "")
            status = r.get("status", "")
            results_text += f"\n[{i}] {agent} ({status}):\n{output}\n"

        if mode == "normal":
            # Brief synthesis for Normal Mode
            prompt = f"""User's request: {goal}

Results:
{results_text}

Provide a very brief, one-line confirmation of what was done. Use emojis."""

            old_prompt = self.system_prompt
            self.system_prompt = SYSTEM_PROMPT_BRIEF
            response = self.think(prompt)
            self.system_prompt = old_prompt
        else:
            # Full synthesis for Working Mode
            prompt = f"""User's original goal: {goal}

Results from all agents:
{results_text}

Please synthesize this into one clear, final response for the user.
Include sections: SUMMARY, WHAT WAS DONE, KEY OUTPUTS, and NEXT STEPS (if applicable)."""

            response = self.think(prompt)

        self.logger.info("Synthesis complete.")
        return self.report("success", response, task)
