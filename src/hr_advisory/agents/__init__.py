"""HR advisory agents.

The primary advisory path is AdvisoryEngine (advisory_engine.py) — a
ReAct loop where the LLM decides what tools to call.

ResponseSynthesizerAgent is used as a fallback synthesis path.
Domain specialists are available for direct use but are NOT part of
the active advisory pipeline (the LLM handles domain routing).

The old Kaizen-based agents (OrchestratorAgent, QueryAnalyzerAgent,
DispatchRouter) are kept for reference and testing but are NOT part
of the active advisory path.
"""

from hr_advisory.agents.actions import (
    CalculatorAgent,
    DocumentGenerationAgent,
)
from hr_advisory.agents.memory import (
    HRSharedMemoryPool,
    LongTermMemory,
    ShortTermMemory,
)
from hr_advisory.agents.orchestration import (
    ResponseSynthesizerAgent,
)
from hr_advisory.agents.orchestration.dispatch_router import DispatchRouter
from hr_advisory.agents.orchestration.orchestrator import OrchestratorAgent
from hr_advisory.agents.orchestration.query_analyzer import QueryAnalyzerAgent
from hr_advisory.agents.specialists import (
    ComplianceAgent,
    CPFAgent,
    EmploymentActAgent,
    FairEmploymentAgent,
    ForeignManpowerAgent,
    PDPAAgent,
    TaxAgent,
    WSHAgent,
)


def create_orchestration_pipeline() -> dict:
    """Factory for the old Kaizen-based orchestration pipeline.

    Returns a dict of named components for the query -> analyze ->
    orchestrate -> synthesize pipeline.  Kept for integration tests.
    """
    shared_pool = HRSharedMemoryPool()
    short_term = ShortTermMemory()
    long_term = LongTermMemory()

    qa = QueryAnalyzerAgent(shared_memory=shared_pool)
    router = DispatchRouter()
    synth = ResponseSynthesizerAgent(shared_memory=shared_pool)

    return {
        "query_analyzer": qa,
        "dispatch_router": router,
        "response_synthesizer": synth,
        "shared_pool": shared_pool,
        "short_term_memory": short_term,
        "long_term_memory": long_term,
    }


__all__ = [
    # Orchestration
    "ResponseSynthesizerAgent",
    "OrchestratorAgent",
    "QueryAnalyzerAgent",
    "DispatchRouter",
    "create_orchestration_pipeline",
    # Domain specialist agents
    "EmploymentActAgent",
    "CPFAgent",
    "ForeignManpowerAgent",
    "FairEmploymentAgent",
    "TaxAgent",
    "WSHAgent",
    "PDPAAgent",
    "ComplianceAgent",
    # Action agents
    "DocumentGenerationAgent",
    "CalculatorAgent",
    # Memory
    "HRSharedMemoryPool",
    "ShortTermMemory",
    "LongTermMemory",
]
