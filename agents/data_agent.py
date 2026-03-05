"""
Agent 7: Data Analysis Agent
Analyzes datasets, generates statistics, and produces insights.
"""

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the Data Analysis Agent for GUNA-ASTRA.

Your job:
1. Analyze datasets and produce meaningful insights.
2. Suggest appropriate visualizations.
3. Identify patterns, outliers, and key statistics.
4. Write Python code using pandas and matplotlib when needed.

Always structure your analysis:
- DATA OVERVIEW
- KEY STATISTICS
- INSIGHTS
- RECOMMENDATIONS
"""


class DataAgent(BaseAgent):
    def __init__(self):
        super().__init__("DataAgent", SYSTEM_PROMPT)

    def run(self, task: dict) -> dict:
        description = task.get("description", "")
        data_snippet = task.get("data", "")

        self.logger.info(f"Analyzing: {description}")

        if data_snippet:
            prompt = f"Analyze this data:\n{data_snippet}\n\nTask: {description}"
        else:
            prompt = f"Provide a data analysis plan and Python code for: {description}"

        response = self.think(prompt)
        self.logger.info("Analysis complete.")
        return self.report("success", response, task)
