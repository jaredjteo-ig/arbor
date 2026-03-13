"""Orchestration-tier agents for the HR advisory pipeline.

QueryClarifier      -- lightweight pre-classification ambiguity detector
QueryAnalyzerAgent  -- classifies and routes queries
DispatchRouter      -- deterministic specialist dispatch (replaces OrchestratorAgent)
OrchestratorAgent   -- plans specialist dispatch (DEPRECATED -- kept for reference)
ResponseSynthesizerAgent -- synthesizes final response
kb_retriever        -- KB retrieval for specialist dispatch (T064)
"""

from hr_advisory.agents.orchestration.dispatch_router import DispatchPlan, DispatchRouter
from hr_advisory.agents.orchestration.kb_retriever import (
    retrieve_provisions_for_specialist,
    format_provisions_for_prompt,
    provisions_to_dicts,
    DOMAIN_KEY_TO_KB_NAME,
)
from hr_advisory.agents.orchestration.orchestrator import OrchestratorAgent
from hr_advisory.agents.orchestration.query_analyzer import QueryAnalyzerAgent
from hr_advisory.agents.orchestration.query_clarifier import QueryClarifier
from hr_advisory.agents.orchestration.response_synthesizer import (
    ResponseSynthesizerAgent,
)

__all__ = [
    "QueryClarifier",
    "QueryAnalyzerAgent",
    "DispatchRouter",
    "DispatchPlan",
    "OrchestratorAgent",
    "ResponseSynthesizerAgent",
    "retrieve_provisions_for_specialist",
    "format_provisions_for_prompt",
    "provisions_to_dicts",
    "DOMAIN_KEY_TO_KB_NAME",
]
