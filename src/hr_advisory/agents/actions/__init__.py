"""Action agents for the HR advisory pipeline.

Action agents produce artefacts (documents, calculations) rather than
advisory opinions.

  - DocumentGenerationAgent: LLM-powered document generation from templates
  - CalculatorAgent:         Deterministic HR calculations (no LLM)
"""

from hr_advisory.agents.actions.calculator import CalculatorAgent
from hr_advisory.agents.actions.document_gen import DocumentGenerationAgent

__all__ = [
    "DocumentGenerationAgent",
    "CalculatorAgent",
]
