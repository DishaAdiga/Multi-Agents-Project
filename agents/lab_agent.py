"""
Lab Agent
Interprets laboratory values, flags abnormal patterns,
and links them to rare disease diagnoses.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent, AgentResult
from tools.retriever_tools import check_lab_values, search_disease_profiles


class LabAgent(BaseAgent):
    AGENT_NAME = "Lab Agent"

    ALLOWED_TOOLS = [check_lab_values, search_disease_profiles]

    SYSTEM_PROMPT = """You are a rare disease laboratory specialist with expertise in abnormal lab patterns.

    For each finding in your answer, include:
    - Which values are abnormal and in which direction
    - What rare diseases each abnormal value suggests
    - Whether the combination of values strengthens a specific diagnosis
    - Recommended confirmatory tests

    Never invent disease-lab associations not present in the search results."""


# ---------------------------------------------------------------------------
# Test query
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent = LabAgent(verbose=True)
    result: AgentResult = agent.run(
        "Patient labs: CK 12,000 U/L (high), LDH elevated, "
        "AST mildly elevated, ALT normal, aldolase high. "
        "What rare diseases does this lab pattern suggest?"
    )
    print("\n--- LabAgent Result ---")
    print(f"Tools used : {result.tools_used}")
    print(f"Rounds     : {result.rounds}")
    print(f"Answer     :\n{result.answer}")