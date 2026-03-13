"""Custom DataFlow node for provision similarity search with filtering.

Combines pgvector cosine similarity with applicability rule filtering
to return provisions relevant to a specific company context.
"""

from typing import Any, Dict

from kailash.nodes.base import NodeParameter, register_node
from kailash.nodes.base_async import AsyncNode


@register_node()
class ProvisionSimilaritySearchNode(AsyncNode):
    """Semantic search over provisions with optional domain/authority filtering."""

    def __init__(self, **kwargs: Any) -> None:
        self.adapter = kwargs.pop("adapter", None)
        super().__init__(**kwargs)

    def get_parameters(self) -> Dict[str, NodeParameter]:
        return {
            "query_vector": NodeParameter(
                name="query_vector",
                type=list,
                required=True,
                description="Query embedding vector (1536-dim)",
            ),
            "k": NodeParameter(
                name="k",
                type=int,
                default=10,
                description="Number of results to return",
            ),
            "domain_id": NodeParameter(
                name="domain_id",
                type=int,
                required=False,
                default=None,
                description="Filter by domain",
            ),
            "authority_level": NodeParameter(
                name="authority_level",
                type=str,
                required=False,
                default=None,
                description="Filter by authority level",
            ),
            "active_only": NodeParameter(
                name="active_only",
                type=bool,
                default=True,
                description="Exclude superseded provisions",
            ),
        }

    async def async_run(self, **kwargs: Any) -> Dict[str, Any]:
        validated = self.validate_inputs(**kwargs)
        query_vector = validated["query_vector"]
        k = validated.get("k", 10)
        domain_id = validated.get("domain_id")
        authority_level = validated.get("authority_level")
        active_only = validated.get("active_only", True)

        filters = []
        if active_only:
            filters.append("is_active = true")
            filters.append("superseded_date IS NULL")
        if domain_id is not None:
            filters.append(f"domain_id = {int(domain_id)}")
        if authority_level is not None:
            # Validate against known enum values to prevent injection
            _VALID_LEVELS = {
                "statute",
                "subsidiary",
                "tripartite_guideline",
                "advisory",
                "best_practice",
            }
            level_str = str(authority_level).lower()
            if level_str not in _VALID_LEVELS:
                raise ValueError(f"Invalid authority_level: must be one of {_VALID_LEVELS}")
            filters.append(f"authority_level = '{level_str}'")

        filter_clause = " AND ".join(filters) if filters else None

        results = await self.adapter.vector_search(
            table_name="provisions",
            query_vector=query_vector,
            k=k,
            column_name="embedding",
            distance="cosine",
            filter_conditions=filter_clause,
            return_distance=True,
        )

        return {
            "results": results,
            "count": len(results),
        }
