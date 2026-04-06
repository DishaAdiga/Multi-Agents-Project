"""
Symptom Agent
Searches the Orphanet disease store and maps clinical symptoms
to ranked candidate rare diseases with structured phenotype matching.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent, AgentResult
from tools.retriever_tools import search_disease_profiles, get_hpo_terms


class SymptomAgent(BaseAgent):
    AGENT_NAME = "Symptom Agent"

    ALLOWED_TOOLS = [search_disease_profiles, get_hpo_terms]

    SYSTEM_PROMPT = """You are a rare disease symptom analyst with expertise in clinical phenotyping.

    For each candidate disease in your answer, include:
    - Disease name and OrphaCode
    - Which symptoms match and which don't
    - Key features to confirm or rule it out
    - Associated genes if available

    Be precise. Never include diseases not supported by the search results."""


# ---------------------------------------------------------------------------
# Test query
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent = SymptomAgent(verbose=True)
    result: AgentResult = agent.run(
        "A 12-year-old boy with progressive proximal muscle weakness, "
        "difficulty climbing stairs, waddling gait, and calf pseudohypertrophy. "
        "No family history. CK elevated at 12,000 U/L."
    )
    print("\n--- SymptomAgent Result ---")
    print(f"Tools used : {result.tools_used}")
    print(f"Rounds     : {result.rounds}")
    print(f"Answer     :\n{result.answer}")