"""
Genetics Agent
Searches ClinVar genetic variant data and links gene markers
to rare diseases with clinical significance.
"""

from __future__ import annotations

from agents.base_agent import BaseAgent, AgentResult
from tools.retriever_tools import lookup_genetic_data, search_disease_profiles


class GeneticsAgent(BaseAgent):
    AGENT_NAME = "Genetics Agent"

    ALLOWED_TOOLS = [lookup_genetic_data, search_disease_profiles]

    SYSTEM_PROMPT = """You are a rare disease genetics specialist with expertise in clinical genomics.

    For each genetic finding in your answer, include:
    - Gene symbol and associated conditions
    - Clinical significance of variants found
    - Which rare diseases the gene links to with OrphaCodes
    - Whether inheritance pattern matches the patient's family history

Never invent variant classifications not present in the search results."""


# ---------------------------------------------------------------------------
# Test query
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent = GeneticsAgent(verbose=True)
    result: AgentResult =  agent.run(
    "Patient has a pathogenic variant in the GAA gene. "
    "What rare disease does this confirm and what are the clinical implications?"
    )
    print("\n--- GeneticsAgent Result ---")
    print(f"Tools used : {result.tools_used}")
    print(f"Rounds     : {result.rounds}")
    print(f"Answer     :\n{result.answer}")