"""Knowledge Base Content Pipeline and Tooling.

Provides modules for populating and managing the regulatory knowledge base:

- pipeline: Core content loading orchestrator (KBContentPipeline)
- validator: Content quality and integrity validation (KBContentValidator)
- embeddings: pgvector embedding generation (EmbeddingPipeline)
- admin: CLI-style KB management functions
"""

from hr_advisory.kb.pipeline import KBContentPipeline
from hr_advisory.kb.validator import KBContentValidator
from hr_advisory.kb.embeddings import EmbeddingPipeline
from hr_advisory.kb.admin import add_provision, update_provision, get_kb_stats, search_provisions

__all__ = [
    "KBContentPipeline",
    "KBContentValidator",
    "EmbeddingPipeline",
    "add_provision",
    "update_provision",
    "get_kb_stats",
    "search_provisions",
]
