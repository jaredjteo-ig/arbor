"""Advisory response streaming helpers (T057).

Provides Server-Sent Events (SSE) streaming infrastructure for
advisory responses, enabling <3 second first-token delivery.

In production, integrates with Kaizen agent streaming output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import AsyncIterator, Optional


class ChunkType(str, Enum):
    """Type of stream chunk."""

    TEXT = "text"  # Advisory response text
    CITATION = "citation"  # Source citation reference
    DISCLAIMER = "disclaimer"  # Risk-tier disclaimer
    CALCULATOR = "calculator"  # Calculator result
    ACTION = "action"  # Suggested action item
    STATUS = "status"  # Processing status update
    DONE = "done"  # Stream complete signal


@dataclass
class StreamChunk:
    """A single chunk in an SSE advisory response stream."""

    chunk_type: ChunkType
    content: str
    metadata: dict[str, str] = field(default_factory=dict)
    sequence: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        import json

        data = {
            "type": self.chunk_type.value,
            "content": self.content,
            "sequence": self.sequence,
        }
        if self.metadata:
            data["metadata"] = self.metadata
        return f"data: {json.dumps(data)}\n\n"


async def advisory_stream(
    session_id: str,
    response_text: str,
    citations: Optional[list[dict[str, str]]] = None,
    disclaimer_text: str = "",
    risk_tier: str = "green",
) -> AsyncIterator[StreamChunk]:
    """Stream an advisory response as SSE chunks.

    Breaks the response into chunks for streaming delivery:
    1. Status chunk (processing started)
    2. Disclaimer chunk (if risk tier requires it)
    3. Text chunks (advisory content, sentence by sentence)
    4. Citation chunks (source references)
    5. Done chunk (stream complete)

    In production, this wraps the Kaizen agent's streaming output
    and adds citation/disclaimer/trust metadata.
    """
    seq = 0

    # 1. Status: processing started
    yield StreamChunk(
        chunk_type=ChunkType.STATUS,
        content="Generating advisory response...",
        metadata={"session_id": session_id, "risk_tier": risk_tier},
        sequence=seq,
    )
    seq += 1

    # 2. Disclaimer (if needed)
    if disclaimer_text:
        yield StreamChunk(
            chunk_type=ChunkType.DISCLAIMER,
            content=disclaimer_text,
            metadata={"risk_tier": risk_tier},
            sequence=seq,
        )
        seq += 1

    # 3. Text chunks — split by sentence for streaming effect
    sentences = _split_sentences(response_text)
    for sentence in sentences:
        yield StreamChunk(
            chunk_type=ChunkType.TEXT,
            content=sentence,
            sequence=seq,
        )
        seq += 1

    # 4. Citations
    for citation in citations or []:
        yield StreamChunk(
            chunk_type=ChunkType.CITATION,
            content=citation.get("label", ""),
            metadata=citation,
            sequence=seq,
        )
        seq += 1

    # 5. Done
    yield StreamChunk(
        chunk_type=ChunkType.DONE,
        content="",
        metadata={"total_chunks": str(seq)},
        sequence=seq,
    )


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence-like chunks for streaming.

    Simple splitter that preserves meaning while enabling
    progressive rendering.
    """
    if not text:
        return []

    # Split on sentence-ending punctuation followed by space
    chunks: list[str] = []
    current: list[str] = []

    for char in text:
        current.append(char)
        if char in ".!?" and len(current) > 20:
            chunks.append("".join(current))
            current = []

    if current:
        chunks.append("".join(current))

    return [c for c in chunks if c.strip()]
