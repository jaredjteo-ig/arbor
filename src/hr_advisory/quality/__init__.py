"""Automated quality rubric scoring system for HR advisory responses.

Scores responses across 8 dimensions (1-5 each). Overall score uses the
weakest-link principle: min across all dimensions.

Dimensions:
1. Legal Accuracy (LLM-as-judge)
2. Contextual Relevance (LLM-as-judge)
3. Conversational Coherence (LLM-as-judge)
4. Actionability (LLM-as-judge)
5. Risk Awareness (automated + LLM)
6. Citation Quality (automated)
7. Language Understanding (LLM-as-judge)
8. Completeness (LLM-as-judge)
"""

from hr_advisory.quality.rubric import QualityRubric, RubricResult, score_batch
from hr_advisory.quality.automated_checks import AutomatedChecks
from hr_advisory.quality.adversarial_runner import AdversarialRunner, ADVERSARIAL_SCENARIOS

__all__ = [
    "QualityRubric",
    "RubricResult",
    "AutomatedChecks",
    "score_batch",
    "AdversarialRunner",
    "ADVERSARIAL_SCENARIOS",
]
