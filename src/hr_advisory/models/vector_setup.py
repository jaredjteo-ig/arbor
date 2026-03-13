"""pgvector setup for semantic search over provisions.

Adds a vector embedding column to the provisions table and creates
an HNSW index for fast cosine similarity search.
"""

import os

from dataflow.adapters import PostgreSQLVectorAdapter

VECTOR_DIMENSIONS = 1536  # OpenAI text-embedding-3-small


def get_vector_adapter() -> PostgreSQLVectorAdapter:
    """Create the pgvector adapter for provision embeddings."""
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://aite:aite@localhost:5432/aite",
    )
    return PostgreSQLVectorAdapter(
        database_url,
        vector_dimensions=VECTOR_DIMENSIONS,
        default_distance="cosine",
    )


async def setup_vector_search(adapter: PostgreSQLVectorAdapter) -> None:
    """Initialize pgvector extension, column, and index.

    Safe to call multiple times — uses IF NOT EXISTS semantics.
    """
    await adapter.ensure_pgvector_extension()

    await adapter.create_vector_column(
        table_name="provisions",
        column_name="embedding",
        dimensions=VECTOR_DIMENSIONS,
    )

    await adapter.create_vector_index(
        table_name="provisions",
        column_name="embedding",
        index_type="hnsw",
        distance="cosine",
        m=16,
        ef_construction=64,
    )
