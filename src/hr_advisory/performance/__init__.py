"""Performance optimization infrastructure (T057).

Provides:
- Response caching with TTL management
- KB retrieval optimization hints
- Advisory response streaming helpers
- Calculator result caching
"""

from hr_advisory.performance.cache import (
    CacheEntry,
    CacheConfig,
    ResponseCache,
    get_cache,
)
from hr_advisory.performance.streaming import (
    StreamChunk,
    ChunkType,
    advisory_stream,
)

__all__ = [
    "CacheEntry",
    "CacheConfig",
    "ResponseCache",
    "get_cache",
    "StreamChunk",
    "ChunkType",
    "advisory_stream",
]
