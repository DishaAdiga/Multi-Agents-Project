"""
Case Study Agent
Searches 1,171 PubMed case report abstracts to find real published
cases that match the current patient's presentation.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent, AgentResult
from tools.retriever_tools import search_case_reports, search_disease_profiles


class CaseStudyAgent(BaseAgent):
    AGENT_NAME = "Case Study Agent"

    ALLOWED_TOOLS = [search_case_reports, search_disease_profiles]

    SYSTEM_PROMPT = """You are a rare disease case study analyst with expertise in medical literature.

    For each matching case report in your answer, include:
    - PMID for verification
    - How the published presentation matches the current patient
    - What diagnosis was confirmed and how
    - Any relevant treatment or outcome information

    Never fabricate PMIDs or case details."""


# ---------------------------------------------------------------------------
# Test query
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent = CaseStudyAgent(verbose=True)
    result: AgentResult = agent.run(
        "A 38-year-old woman with progressive proximal muscle weakness, "
        "dyspnoea on exertion, and elevated CK. EMG shows myopathic pattern. "
        "No family history of muscle disease."
    )
    print("\n--- CaseStudyAgent Result ---")
    print(f"Tools used : {result.tools_used}")
    print(f"Rounds     : {result.rounds}")
    print(f"Answer     :\n{result.answer}")