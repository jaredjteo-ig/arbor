"""Kaizen agent team for HR advisory.

Exports orchestration agents, domain specialists, action agents,
memory infrastructure, and a factory function that wires the complete
orchestration pipeline.
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
    DispatchPlan,
    DispatchRouter,
    OrchestratorAgent,
    QueryAnalyzerAgent,
    ResponseSynthesizerAgent,
)
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

__all__ = [
    # Orchestration agents
    "QueryAnalyzerAgent",
    "DispatchRouter",
    "DispatchPlan",
    "OrchestratorAgent",  # DEPRECATED -- kept for reference
    "ResponseSynthesizerAgent",
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
    # Factory
    "create_orchestration_pipeline",
]


def create_orchestration_pipeline(
    max_turns: int = 20,
):
    """Create the full orchestration pipeline with shared memory.

    Returns a dict containing the query analyzer, deterministic dispatch
    router, response synthesizer, and memory infrastructure, pre-wired
    to share a single SharedMemoryPool.

    Usage::

        pipeline = create_orchestration_pipeline()
        analysis = pipeline["query_analyzer"].analyze("How do I calculate CPF?")
        plan = pipeline["dispatch_router"].route(analysis)
        # ... specialists write to pipeline["shared_pool"] ...
        response = pipeline["response_synthesizer"].synthesize(
            specialist_outputs=pipeline["shared_pool"].read_all_specialist_outputs(),
            risk_tier=analysis["risk_tier"],
        )
    """
    shared_pool = HRSharedMemoryPool()
    kaizen_pool = shared_pool.inner_pool  # underlying Kaizen SharedMemoryPool

    query_analyzer = QueryAnalyzerAgent(shared_memory=kaizen_pool)
    dispatch_router = DispatchRouter()
    response_synthesizer = ResponseSynthesizerAgent(shared_memory=kaizen_pool)

    short_term = ShortTermMemory(max_turns=max_turns)
    long_term = LongTermMemory()

    return {
        "query_analyzer": query_analyzer,
        "dispatch_router": dispatch_router,
        "response_synthesizer": response_synthesizer,
        "shared_pool": shared_pool,
        "short_term_memory": short_term,
        "long_term_memory": long_term,
    }
