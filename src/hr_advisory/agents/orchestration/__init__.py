"""Orchestration-tier agents for the HR advisory pipeline.

The primary advisory path is AdvisoryEngine (advisory_engine.py) — a
ReAct loop where the LLM decides what tools to call. No keyword routing.

ResponseSynthesizerAgent is still used as a fallback synthesis path.
The other agents (QueryAnalyzer, DispatchRouter, OrchestratorAgent,
QueryClarifier) are from the old Kaizen pipeline and are kept for
reference but NOT used in the active advisory path.
"""

from hr_advisory.agents.orchestration.query_clarifier import QueryClarifier
from hr_advisory.agents.orchestration.response_synthesizer import (
    ResponseSynthesizerAgent,
)

__all__ = [
    "QueryClarifier",
    "ResponseSynthesizerAgent",
]
