"""Session management for the HR Advisory platform.

Provides session configuration with company context fields.
Uses Redis in production and in-memory storage in development.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AdvisorySessionContext:
    """Session context carrying company and conversation state.

    Each advisory session tracks the company being served, the user,
    conversation history, and any risk tier escalations that occurred
    during the session.
    """

    session_id: str
    company_id: Optional[int] = None
    user_id: Optional[int] = None
    conversation_history: list = field(default_factory=list)
    risk_tier_escalations: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str) -> None:
        """Append a message to the conversation history."""
        self.conversation_history.append(
            {"role": role, "content": content, "timestamp": time.time()}
        )
        self.last_activity = time.time()

    def escalate_risk(self, from_tier: str, to_tier: str, reason: str) -> None:
        """Record a risk tier escalation event."""
        self.risk_tier_escalations.append(
            {
                "from_tier": from_tier,
                "to_tier": to_tier,
                "reason": reason,
                "timestamp": time.time(),
            }
        )
        self.last_activity = time.time()

    def to_dict(self) -> dict:
        """Serialize session context to a dictionary."""
        return {
            "session_id": self.session_id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "conversation_history": self.conversation_history,
            "risk_tier_escalations": self.risk_tier_escalations,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
        }


class InMemorySessionStore:
    """In-memory session store for development and testing."""

    def __init__(self, ttl_seconds: int = 3600):
        self._sessions: dict[str, AdvisorySessionContext] = {}
        self._ttl = ttl_seconds

    def create(
        self,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> AdvisorySessionContext:
        """Create a new session with optional company context."""
        session_id = str(uuid.uuid4())
        session = AdvisorySessionContext(
            session_id=session_id,
            company_id=company_id,
            user_id=user_id,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        self._cleanup_expired()
        return session

    def get(self, session_id: str) -> Optional[AdvisorySessionContext]:
        """Retrieve a session by ID, or None if expired or missing."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if time.time() - session.last_activity > self._ttl:
            del self._sessions[session_id]
            return None
        return session

    def delete(self, session_id: str) -> bool:
        """Remove a session. Returns True if it existed."""
        return self._sessions.pop(session_id, None) is not None

    def count(self) -> int:
        """Return the number of active sessions."""
        self._cleanup_expired()
        return len(self._sessions)

    def _cleanup_expired(self) -> None:
        """Remove sessions that have exceeded the TTL."""
        now = time.time()
        expired = [
            sid
            for sid, session in self._sessions.items()
            if now - session.last_activity > self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]


class RedisSessionStore:
    """Redis-backed session store for production deployments.

    Stores session data as JSON in Redis with automatic TTL expiry.
    Falls back to in-memory if Redis is unavailable.
    """

    def __init__(self, redis_url: str, ttl_seconds: int = 3600):
        self._ttl = ttl_seconds
        self._redis_url = redis_url
        self._redis: Any = None
        self._fallback = InMemorySessionStore(ttl_seconds=ttl_seconds)
        self._using_fallback = False
        self._connect()

    def _connect(self) -> None:
        """Attempt to connect to Redis."""
        try:
            import redis

            self._redis = redis.from_url(self._redis_url, decode_responses=True)
            self._redis.ping()
            logger.info("Redis session store connected")
        except Exception as exc:
            logger.warning("Redis unavailable (%s), falling back to in-memory sessions", exc)
            self._redis = None
            self._using_fallback = True

    def _key(self, session_id: str) -> str:
        return f"arbor:session:{session_id}"

    def create(
        self,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> AdvisorySessionContext:
        """Create a new session stored in Redis."""
        if self._using_fallback:
            return self._fallback.create(company_id, user_id, metadata)

        session_id = str(uuid.uuid4())
        session = AdvisorySessionContext(
            session_id=session_id,
            company_id=company_id,
            user_id=user_id,
            metadata=metadata or {},
        )
        try:
            import json

            self._redis.setex(self._key(session_id), self._ttl, json.dumps(session.to_dict()))
        except Exception as exc:
            logger.warning("Redis write failed (%s), using in-memory fallback", exc)
            self._using_fallback = True
            return self._fallback.create(company_id, user_id, metadata)
        return session

    def get(self, session_id: str) -> Optional[AdvisorySessionContext]:
        """Retrieve a session from Redis."""
        if self._using_fallback:
            return self._fallback.get(session_id)

        try:
            import json

            data = self._redis.get(self._key(session_id))
            if data is None:
                return None
            d = json.loads(data)
            return AdvisorySessionContext(**d)
        except Exception as exc:
            logger.warning("Redis read failed (%s), checking fallback", exc)
            return self._fallback.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Remove a session from Redis."""
        if self._using_fallback:
            return self._fallback.delete(session_id)

        try:
            return bool(self._redis.delete(self._key(session_id)))
        except Exception:
            return self._fallback.delete(session_id)

    def count(self) -> int:
        """Count active sessions (approximate for Redis)."""
        if self._using_fallback:
            return self._fallback.count()

        try:
            keys = self._redis.keys("arbor:session:*")
            return len(keys)
        except Exception:
            return self._fallback.count()


def create_session_store(settings) -> InMemorySessionStore | RedisSessionStore:
    """Create the appropriate session store based on environment settings.

    Uses Redis in production and in-memory for development.
    """
    if settings.is_production:
        logger.info("Using Redis session store for production")
        return RedisSessionStore(redis_url=settings.redis_url)
    logger.info("Using in-memory session store for development")
    return InMemorySessionStore()
