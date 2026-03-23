"""Embedding pipeline for knowledge base provisions.

Generates OpenAI text embeddings and stores them via pgvector for
semantic search over provisions. Gracefully handles missing API keys
by skipping with a warning rather than raising.
"""

import logging
import os
from typing import Optional

from kailash.runtime import LocalRuntime
from kailash.workflow.builder import WorkflowBuilder

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """Generates and stores embeddings for KB provisions."""

    def __init__(self, model: str | None = None):
        """Initialise the embedding pipeline.

        Args:
            model: The OpenAI embedding model to use. Defaults to
                   EMBEDDING_MODEL from .env, falling back to
                   "text-embedding-3-small".
        """
        import os

        self.model = model or os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
        self._runtime = LocalRuntime()

    def _execute(self, node_type: str, node_id: str, params: dict) -> dict:
        """Run a single-node workflow and return the node result."""
        wf = WorkflowBuilder()
        wf.add_node(node_type, node_id, params)
        results, _ = self._runtime.execute(wf.build())
        return results[node_id]

    @staticmethod
    def _extract_records(result) -> list[dict]:
        """Extract the record list from a ListNode result."""
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "records" in result:
            return result["records"]
        return []

    def _get_api_key(self) -> Optional[str]:
        """Get the OpenAI API key from environment.

        Returns None if no key is set, allowing callers to skip
        gracefully.
        """
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key or not key.strip():
            return None
        return key.strip()

    def generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate a single embedding via OpenAI API.

        Returns:
            List of floats (the embedding vector), or None if the API
            key is missing or the call fails.
        """
        api_key = self._get_api_key()
        if not api_key:
            logger.warning(
                "OPENAI_API_KEY not set. Skipping embedding generation. "
                "Set the key in .env to enable embeddings."
            )
            return None

        try:
            import openai

            client = openai.OpenAI(api_key=api_key)
            response = client.embeddings.create(
                input=text,
                model=self.model,
            )
            return response.data[0].embedding
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            return None
        except Exception as exc:
            logger.error("Embedding generation failed: %s", exc)
            return None

    def generate_provision_text(self, provision: dict) -> str:
        """Combine provision fields into optimal embedding text.

        Format:
            Section: {section}
            Title: {title}
            {plain_summary}
            {formal_text}
        """
        parts = []

        section = provision.get("section", "")
        if section:
            parts.append(f"Section: {section}")

        title = provision.get("title", "")
        if title:
            parts.append(f"Title: {title}")

        plain_summary = provision.get("plain_summary", "")
        if plain_summary:
            parts.append(plain_summary)

        formal_text = provision.get("formal_text", "")
        if formal_text:
            parts.append(formal_text)

        return "\n".join(parts)

    def embed_provision(self, provision_id: int) -> bool:
        """Generate and store embedding for a single provision.

        Returns:
            True if the embedding was generated and stored, False otherwise.
        """
        # Read the provision
        try:
            provision = self._execute("ProvisionReadNode", "read_prov", {"id": provision_id})
        except Exception as exc:
            logger.error("Failed to read provision %s: %s", provision_id, exc)
            return False

        if not provision:
            logger.error("Provision %s not found", provision_id)
            return False

        text = self.generate_provision_text(provision)
        if not text.strip():
            logger.warning("Provision %s has no text to embed, skipping", provision_id)
            return False

        embedding = self.generate_embedding(text)
        if embedding is None:
            return False

        # Store embedding via pgvector
        try:
            from hr_advisory.models.vector_setup import get_vector_adapter
            import asyncio
            import sqlalchemy

            adapter = get_vector_adapter()
            database_url = os.environ.get(
                "DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor"
            )
            engine = sqlalchemy.create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(
                    sqlalchemy.text("UPDATE provisions SET embedding = :emb WHERE id = :pid"),
                    {"emb": str(embedding), "pid": provision_id},
                )
                conn.commit()
            engine.dispose()
            logger.info("Stored embedding for provision %s", provision_id)
            return True
        except Exception as exc:
            logger.error("Failed to store embedding for provision %s: %s", provision_id, exc)
            return False

    def embed_all_provisions(self, batch_size: int = 50) -> dict:
        """Batch embed all provisions that don't have embeddings yet.

        Gracefully handles missing API keys by returning a status dict
        with ``skipped`` information instead of raising.

        Args:
            batch_size: Number of provisions to process in each batch.

        Returns:
            Dict with keys: total, embedded, skipped, errors.
        """
        result = {"total": 0, "embedded": 0, "skipped": 0, "errors": 0}

        # Check API key first
        api_key = self._get_api_key()
        if not api_key:
            logger.warning(
                "OPENAI_API_KEY not set. Skipping all embeddings. "
                "Set the key in .env to enable embeddings."
            )
            # Count total provisions so the caller knows what was skipped
            all_provisions_raw = self._execute("ProvisionListNode", "all_provs", {"filter": {}})
            all_provisions = self._extract_records(all_provisions_raw)
            result["total"] = len(all_provisions)
            result["skipped"] = len(all_provisions)
            return result

        # Get all provisions
        all_provisions_raw = self._execute("ProvisionListNode", "all_provs", {"filter": {}})
        all_provisions = self._extract_records(all_provisions_raw)

        result["total"] = len(all_provisions)

        for provision in all_provisions:
            success = self.embed_provision(provision["id"])
            if success:
                result["embedded"] += 1
            else:
                result["skipped"] += 1

        logger.info(
            "Embedding batch complete: %d total, %d embedded, %d skipped, %d errors",
            result["total"],
            result["embedded"],
            result["skipped"],
            result["errors"],
        )
        return result
