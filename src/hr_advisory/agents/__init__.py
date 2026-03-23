"""HR advisory agents.

The primary advisory path is AdvisoryEngine (advisory_engine.py) — a
ReAct loop where the LLM decides what tools to call.

ResponseSynthesizerAgent is used as a fallback synthesis path.
Domain specialists are available for direct use but are NOT part of
the active advisory pipeline (the LLM handles domain routing).
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
    # Orchestration
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
]
