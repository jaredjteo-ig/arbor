"""Integration tests for EATP trust lineage in the streaming endpoint.

Verifies that POST /advisory/stream creates the same trust chain
artefacts as POST /advisory/query: GenesisRecord, AgentAttestation,
and TrustChain — all included in the final SSE 'complete' event.
"""

from __future__ import annotations

import json
import uuid

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.requires_postgres

from hr_advisory.api.platform import create_platform
from hr_advisory.config.settings import Settings


@pytest.fixture(scope="module")
def settings() -> Settings:
    """Test settings with development defaults."""
    return Settings(
        app_env="development",
        api_port=8098,
        cors_origins="*",
    )


@pytest.fixture(scope="module")
def platform(settings):
    """Create the Nexus platform once for all tests in this module."""
    return create_platform(settings)


@pytest.fixture(scope="module")
def client(platform) -> TestClient:
    """TestClient backed by the underlying FastAPI app."""
    return TestClient(platform._gateway.app)


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict:
    """Register a test user with company_id=1 and return Authorization headers."""
    email = f"stream_trust_{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "name": "Stream Trust Test User",
            "password": "SecurePass1!",
            "company_id": 1,
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _parse_sse_events(body: str) -> dict[str, list[dict]]:
    """Parse SSE event stream text into a dict keyed by event type."""
    events: dict[str, list[dict]] = {}
    current_event_type = None

    for line in body.splitlines():
        if line.startswith("event: "):
            current_event_type = line[7:].strip()
        elif line.startswith("data: ") and current_event_type:
            data = json.loads(line[6:])
            events.setdefault(current_event_type, []).append(data)
            current_event_type = None

    return events


class TestStreamTrustLineage:
    """Verify the streaming endpoint creates EATP trust lineage."""

    def test_stream_returns_trust_chain_in_complete_event(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """The final 'complete' SSE event must contain a trust_chain object."""
        response = client.post(
            "/advisory/stream",
            json={"query": "What are the overtime rules?", "company_id": 1},
            headers=auth_headers,
        )
        assert response.status_code == 200

        events = _parse_sse_events(response.text)
        assert "complete" in events, "Stream must emit a 'complete' event"

        complete = events["complete"][0]
        assert "trust_chain" in complete, "Complete event must include trust_chain"

    def test_trust_chain_has_required_fields(self, client: TestClient, auth_headers: dict) -> None:
        """Trust chain must contain session_id, genesis_fingerprint, and attestation_count."""
        response = client.post(
            "/advisory/stream",
            json={"query": "Explain CPF contributions", "company_id": 1},
            headers=auth_headers,
        )
        events = _parse_sse_events(response.text)
        trust_chain = events["complete"][0]["trust_chain"]

        assert "session_id" in trust_chain
        assert "genesis_fingerprint" in trust_chain
        assert "attestation_count" in trust_chain
        assert (
            trust_chain["attestation_count"] >= 1
        ), "Trust chain must have at least one attestation"

    def test_trust_chain_has_confidence_and_provisions(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Trust chain must include chain_confidence and provisions_cited."""
        response = client.post(
            "/advisory/stream",
            json={"query": "What is the notice period?", "company_id": 1},
            headers=auth_headers,
        )
        events = _parse_sse_events(response.text)
        trust_chain = events["complete"][0]["trust_chain"]

        assert "chain_confidence" in trust_chain
        assert isinstance(trust_chain["chain_confidence"], float)
        assert (
            trust_chain["chain_confidence"] > 0
        ), "Chain confidence must be positive for a valid query"
        assert "provisions_cited" in trust_chain
        assert isinstance(trust_chain["provisions_cited"], list)

    def test_stream_provisions_include_status_field(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Provisions cited in the stream must include the status field (parity with /query)."""
        response = client.post(
            "/advisory/stream",
            json={"query": "What are the overtime rules?", "company_id": 1},
            headers=auth_headers,
        )
        events = _parse_sse_events(response.text)
        complete = events["complete"][0]
        provisions = complete["provisions_cited"]

        assert len(provisions) > 0, "Must have at least one provision cited"
        for provision in provisions:
            assert (
                "status" in provision
            ), f"Provision {provision.get('provision_id')} missing 'status' field"
            assert "provision_id" in provision
            assert "title" in provision
            assert "authority_level" in provision

    def test_stream_includes_citation_warnings(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Complete event must include citation_warnings (parity with /query)."""
        response = client.post(
            "/advisory/stream",
            json={"query": "CPF contribution rates", "company_id": 1},
            headers=auth_headers,
        )
        events = _parse_sse_events(response.text)
        complete = events["complete"][0]

        assert "citation_warnings" in complete, "Complete event must include citation_warnings"

    def test_stream_trust_chain_matches_query_structure(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Trust chain from /stream must have the same structure as /query."""
        query_text = "What is the notice period for employees?"

        # Call /query
        query_response = client.post(
            "/advisory/query",
            json={"query": query_text, "company_id": 1},
            headers=auth_headers,
        )
        query_data = query_response.json()
        query_trust = query_data["trust_chain"]

        # Call /stream
        stream_response = client.post(
            "/advisory/stream",
            json={"query": query_text, "company_id": 1},
            headers=auth_headers,
        )
        events = _parse_sse_events(stream_response.text)
        stream_trust = events["complete"][0]["trust_chain"]

        # Same keys
        assert set(query_trust.keys()) == set(stream_trust.keys()), (
            f"Trust chain key mismatch. "
            f"Query has: {sorted(query_trust.keys())}, "
            f"Stream has: {sorted(stream_trust.keys())}"
        )

        # Same structure (different session_ids are expected)
        assert stream_trust["attestation_count"] == query_trust["attestation_count"]
        assert stream_trust["verification_depth"] == query_trust["verification_depth"]
        assert stream_trust["human_review_required"] == query_trust["human_review_required"]

    def test_stream_complete_event_includes_company_and_conversation(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Complete event must include company_id and conversation_id (parity with /query)."""
        response = client.post(
            "/advisory/stream",
            json={
                "query": "What are the CPF rates?",
                "company_id": 1,
                "conversation_id": 42,
            },
            headers=auth_headers,
        )
        events = _parse_sse_events(response.text)
        complete = events["complete"][0]

        assert complete.get("company_id") == 1
        assert complete.get("conversation_id") == 42

    def test_stream_requires_auth(self, client: TestClient) -> None:
        """POST /advisory/stream without auth returns 401."""
        response = client.post(
            "/advisory/stream",
            json={"query": "test"},
        )
        assert response.status_code == 401
