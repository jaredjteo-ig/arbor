"""HR advisory agents.

The primary advisory path is the Delegate engine (delegate/arbor_loop.py) —
a TAOD loop where the LLM decides what tools to call via 208+ registered tools.

Action agents (CalculatorAgent, DocumentGenerationAgent) are still used as
tool backends by the Delegate.

Memory classes (HRSharedMemoryPool, ShortTermMemory, LongTermMemory) are
used by the advisory router for conversation context.
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

__all__ = [
    # Action agents
    "DocumentGenerationAgent",
    "CalculatorAgent",
    # Memory
    "HRSharedMemoryPool",
    "ShortTermMemory",
    "LongTermMemory",
]
