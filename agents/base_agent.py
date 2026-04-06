"""
Base Agent
Shared agentic loop using bind_tools + manual loop for Groq compatibility.
create_react_agent has a tool registration bug with Groq — bind_tools is reliable.

Tested with:
    langgraph==1.1.6  |  langchain-groq==1.1.2  |  langchain-core==1.2.26
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq

from tools.retriever_tools import ALL_TOOLS

load_dotenv()

GROQ_MODEL      = "llama-3.3-70b-versatile"
MAX_TOOL_ROUNDS = 6


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    agent_name: str
    query:      str
    answer:     str
    tools_used: list[str] = field(default_factory=list)
    rounds:     int = 0
    error:      str | None = None

    def to_dict(self) -> dict:
        return {
            "agent":      self.agent_name,
            "query":      self.query,
            "answer":     self.answer,
            "tools_used": self.tools_used,
            "rounds":     self.rounds,
            "error":      self.error,
        }


# ---------------------------------------------------------------------------
# Base agent
# ---------------------------------------------------------------------------

class BaseAgent:
    AGENT_NAME:    str  = "Base Agent"
    SYSTEM_PROMPT: str  = "You are a rare-disease diagnostic assistant."
    ALLOWED_TOOLS: list = ALL_TOOLS

    def __init__(self, verbose: bool = False) -> None:
        self.verbose   = verbose
        self._tool_map = {t.name: t for t in self.ALLOWED_TOOLS}

        llm = ChatGroq(
            model=GROQ_MODEL,
            temperature=0.2,
            api_key=os.environ["GROQ_API_KEY"],
        )
        # bind_tools is reliable with Groq; create_react_agent has a tool
        # registration bug that causes 400 errors on certain queries
        self._llm = llm.bind_tools(self.ALLOWED_TOOLS)

    def run(self, query: str) -> AgentResult:
        self._log(f"Starting — {query[:80]}...")

        result = AgentResult(
            agent_name=self.AGENT_NAME,
            query=query,
            answer="",
        )

        # build message history
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=query),
        ]

        tools_used = set()

        try:
            for round_num in range(1, MAX_TOOL_ROUNDS + 1):
                self._log(f"Round {round_num} — calling LLM")
                response: AIMessage = self._llm.invoke(messages)
                messages.append(response)

                # no tool calls → final answer
                if not response.tool_calls:
                    result.answer     = response.content
                    result.rounds     = round_num
                    result.tools_used = list(tools_used)
                    self._log(f"Done. Tools: {result.tools_used}")
                    return result

                # dispatch each tool call
                for tc in response.tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["args"]
                    tool_id   = tc["id"]
                    tools_used.add(tool_name)

                    self._log(f"Tool called: {tool_name}({tool_args})")

                    try:
                        tool_fn = self._tool_map[tool_name]
                        output  = tool_fn.invoke(tool_args)
                    except Exception as exc:
                        output = json.dumps({"error": str(exc)})

                    messages.append(
                        ToolMessage(content=output, tool_call_id=tool_id)
                    )

            # max rounds hit — force final answer without tools
            self._log("Max rounds reached — forcing final answer.")
            from langchain_groq import ChatGroq as _ChatGroq
            bare_llm  = _ChatGroq(
                model=GROQ_MODEL,
                temperature=0.2,
                api_key=os.environ["GROQ_API_KEY"],
            )
            messages.append(HumanMessage(
                content="Summarise your findings so far. Do not call any more tools."
            ))
            final          = bare_llm.invoke(messages)
            result.answer  = final.content
            result.rounds  = MAX_TOOL_ROUNDS
            result.tools_used = list(tools_used)

        except Exception as exc:
            result.error  = str(exc)
            result.answer = f"[Agent failed: {exc}]"

        return result

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[{self.AGENT_NAME}] {msg}")


# ---------------------------------------------------------------------------
# Test query
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent  = BaseAgent(verbose=True)
    result = agent.run(
        "What rare diseases cause progressive muscle weakness and respiratory failure?"
    )
    print("\n--- AgentResult ---")
    print(f"Agent      : {result.agent_name}")
    print(f"Rounds     : {result.rounds}")
    print(f"Tools used : {result.tools_used}")
    print(f"Answer     :\n{result.answer}")