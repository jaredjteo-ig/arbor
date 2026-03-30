"""Orchestration-tier agents for the HR advisory pipeline.

The primary advisory path is the Delegate engine (delegate/arbor_loop.py),
which handles all advisory domains via 208+ tools with a TAOD loop.

The old Kaizen-based orchestration agents (QueryAnalyzer, DispatchRouter,
OrchestratorAgent, ResponseSynthesizerAgent, QueryClarifier, KBRetriever)
have been removed.
"""

__all__: list[str] = []
