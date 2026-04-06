"""
Runs all 4 specialist agents in parallel using ThreadPoolExecutor,
collects their AgentResults, and makes a final Groq synthesis call
to produce a ranked differential diagnosis report.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from dotenv import load_dotenv
from groq import Groq

from agents.symptom_agent    import SymptomAgent
from agents.case_study_agent import CaseStudyAgent
from agents.genetics_agent   import GeneticsAgent
from agents.lab_agent        import LabAgent
from agents.base_agent       import AgentResult

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# Final report container
# ---------------------------------------------------------------------------

@dataclass
class DiagnosticReport:
    query:           str
    symptom_result:  AgentResult | None = None
    case_result:     AgentResult | None = None
    genetics_result: AgentResult | None = None
    lab_result:      AgentResult | None = None
    synthesis:       str = ""
    errors:          list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query":    self.query,
            "agents": {
                "symptom":    self.symptom_result.to_dict()  if self.symptom_result  else None,
                "case_study": self.case_result.to_dict()     if self.case_result     else None,
                "genetics":   self.genetics_result.to_dict() if self.genetics_result else None,
                "lab":        self.lab_result.to_dict()      if self.lab_result      else None,
            },
            "synthesis": self.synthesis,
            "errors":    self.errors,
        }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._groq   = Groq(api_key=os.environ["GROQ_API_KEY"])

        # instantiate all 4 agents once — reused across calls
        self._agents = {
            "symptom":    SymptomAgent(verbose=verbose),
            "case_study": CaseStudyAgent(verbose=verbose),
            "genetics":   GeneticsAgent(verbose=verbose),
            "lab":        LabAgent(verbose=verbose),
        }

    # public API 

    def run(self, query: str) -> DiagnosticReport:
        self._log(f"Starting orchestration for: {query[:80]}...")
        report = DiagnosticReport(query=query)

        # ── Step 1: run all 4 agents in parallel ─────────────────────────
        results = self._run_parallel(query)

        report.symptom_result  = results.get("symptom")
        report.case_result     = results.get("case_study")
        report.genetics_result = results.get("genetics")
        report.lab_result      = results.get("lab")

        # collect any agent errors
        for name, result in results.items():
            if result and result.error:
                report.errors.append(f"{name}: {result.error}")

        # ── Step 2: synthesise all results into ranked differential ───────
        self._log("All agents done. Running synthesis...")
        report.synthesis = self._synthesise(query, results)
        self._log("Synthesis complete.")

        return report

    #parallel execution

    def _run_parallel(self, query: str) -> dict[str, AgentResult]:
        results = {}

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(agent.run, query): name
                for name, agent in self._agents.items()
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                    self._log(f"[{name}] finished.")
                except Exception as exc:
                    self._log(f"[{name}] failed: {exc}")
                    results[name] = AgentResult(
                        agent_name=name,
                        query=query,
                        answer="",
                        error=str(exc),
                    )

        return results

    # synthesis call

    def _synthesise(self, query: str, results: dict[str, AgentResult]) -> str:
        """
        Single Groq call that reads all 4 agent answers and produces
        a ranked differential diagnosis report.
        """

        def agent_block(name: str, result: AgentResult | None) -> str:
            if result is None or result.error:
                return f"### {name.upper()} AGENT\nNo results (error: {result.error if result else 'unknown'})\n"
            return f"### {name.upper()} AGENT\n{result.answer}\n"

        combined = "\n".join([
            agent_block("Symptom",    results.get("symptom")),
            agent_block("Case Study", results.get("case_study")),
            agent_block("Genetics",   results.get("genetics")),
            agent_block("Lab",        results.get("lab")),
        ])

        synthesis_prompt = f"""You are a senior rare disease diagnostician synthesising findings from 4 specialist agents.

Patient presentation:
{query}

Specialist agent findings:
{combined}

Based on all the above evidence, produce a ranked differential diagnosis report in this exact format:

RANKED DIFFERENTIAL DIAGNOSIS
==============================

1. [Disease Name] (OrphaCode: XXXXXX) — Confidence: High/Medium/Low
   Evidence for:
   - [symptom/lab/genetic/case evidence supporting this diagnosis]
   Evidence against / gaps:
   - [anything that doesn't fit or is missing]
   Recommended next steps:
   - [confirmatory tests or referrals]

2. [Disease Name] ...

(include 3-5 candidates ranked by strength of evidence)

CLINICAL SUMMARY
================
[2-3 sentence summary of the most likely diagnosis and immediate recommended action]

DISCLAIMER
==========
This report is AI-generated for decision support only. All findings must be verified by a qualified clinician before any diagnostic or treatment decision is made."""

        response = self._groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "user", "content": synthesis_prompt}
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[Orchestrator] {msg}")


# ---------------------------------------------------------------------------
# Test query
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    orchestrator = Orchestrator(verbose=True)

    query = (
        "A 12-year-old boy with progressive proximal muscle weakness, "
        "difficulty climbing stairs, waddling gait, calf pseudohypertrophy, "
        "and elevated CK at 12,000 U/L. No family history of muscle disease. "
        "EMG shows myopathic pattern."
    )

    print(f"\nQuery: {query}\n{'='*70}")
    report = orchestrator.run(query)

    print("\n\n" + "="*70)
    print("FINAL SYNTHESIS REPORT")
    print("="*70)
    print(report.synthesis)

    if report.errors:
        print(f"\nAgent errors: {report.errors}")