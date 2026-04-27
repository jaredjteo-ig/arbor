"""Integration tests for T008 — Company and User DataFlow models.

Tests run against real PostgreSQL.
Docker must be running: docker compose -f docker-compose.dev.yml up -d
"""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")


@pytest.fixture(scope="module")
def db_instance():
    from hr_advisory.models import db

    return db


# ---------------------------------------------------------------------------
# Model registration
# ---------------------------------------------------------------------------


class TestModelRegistration:
    def test_all_six_models_registered(self, db_instance):
        names = set(db_instance.get_models().keys())
        expected = {
            "Company",
            "User",
            "Conversation",
            "AdvisorySession",
            "ContentUpdate",
            "Template",
        }
        assert expected.issubset(names)


# ---------------------------------------------------------------------------
# Company CRUD
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="No DB")
class TestCompanyCRUD:
    def test_create_company_with_headcounts(self, db_instance):
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()
        wf = WorkflowBuilder()
        wf.add_node(
            "CompanyCreateNode",
            "create",
            {
                "name": "Acme Pte Ltd",
                "uen": "202012345A",
                "sector": "Technology",
                "sub_sector": "Software Development",
                "headcount_local": 15,
                "headcount_pr": 3,
                "headcount_ep": 5,
                "headcount_sp": 2,
                "headcount_wp": 0,
                "salary_ranges": {"min": 3000, "max": 15000, "median": 6500},
                "profile_completeness_score": 0.85,
            },
        )
        results, _ = runtime.execute(wf.build())
        company = results["create"]
        assert company["id"] is not None
        assert company["name"] == "Acme Pte Ltd"
        assert company["uen"] == "202012345A"
        assert company["headcount_local"] == 15
        assert company["headcount_ep"] == 5

    def test_total_headcount_calculable(self, db_instance):
        """Company headcount fields allow calculating total workforce and foreign ratios."""
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()
        wf = WorkflowBuilder()
        wf.add_node(
            "CompanyCreateNode",
            "create",
            {
                "name": "Headcount Test Co",
                "headcount_local": 10,
                "headcount_pr": 5,
                "headcount_ep": 3,
                "headcount_sp": 2,
                "headcount_wp": 4,
            },
        )
        results, _ = runtime.execute(wf.build())
        c = results["create"]
        total = (
            c["headcount_local"]
            + c["headcount_pr"]
            + c["headcount_ep"]
            + c["headcount_sp"]
            + c["headcount_wp"]
        )
        assert total == 24
        foreign = c["headcount_ep"] + c["headcount_sp"] + c["headcount_wp"]
        assert foreign == 9


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="No DB")
class TestUserCRUD:
    def test_create_user_with_preferences(self, db_instance):
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()

        # Create company first
        wf_co = WorkflowBuilder()
        wf_co.add_node("CompanyCreateNode", "co", {"name": "User Test Co"})
        r_co, _ = runtime.execute(wf_co.build())

        wf = WorkflowBuilder()
        wf.add_node(
            "UserCreateNode",
            "create",
            {
                "email": "boss@example.com",
                "name": "John Tan",
                "company_id": r_co["co"]["id"],
                "role": "owner",
                "preferences": {"text_size": "normal", "language": "en", "notifications": True},
            },
        )
        results, _ = runtime.execute(wf.build())
        user = results["create"]
        assert user["email"] == "boss@example.com"
        assert user["role"] == "owner"



# ---------------------------------------------------------------------------
# Conversation + Advisory Session
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="No DB")
class TestConversationFlow:
    def test_full_advisory_flow(self, db_instance):
        """Create company → user → conversation → advisory session (full chain)."""
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()

        # Company
        wf1 = WorkflowBuilder()
        wf1.add_node("CompanyCreateNode", "co", {"name": "Advisory Flow Co"})
        r1, _ = runtime.execute(wf1.build())
        company_id = r1["co"]["id"]

        # User
        wf2 = WorkflowBuilder()
        wf2.add_node(
            "UserCreateNode",
            "user",
            {
                "email": "hr@advisoryflow.sg",
                "name": "Ming Wei",
                "company_id": company_id,
                "role": "hr_manager",
            },
        )
        r2, _ = runtime.execute(wf2.build())
        user_id = r2["user"]["id"]

        # Conversation
        wf3 = WorkflowBuilder()
        wf3.add_node(
            "ConversationCreateNode",
            "conv",
            {
                "user_id": user_id,
                "company_id": company_id,
                "title": "Sick leave encashment policy",
            },
        )
        r3, _ = runtime.execute(wf3.build())
        conv_id = r3["conv"]["id"]
        assert conv_id is not None

        # Advisory session
        wf4 = WorkflowBuilder()
        wf4.add_node(
            "AdvisorySessionCreateNode",
            "session",
            {
                "conversation_id": conv_id,
                "user_id": user_id,
                "company_id": company_id,
                "query_text": "Can we reimburse unused sick leave as cash to employees?",
                "response_text": "No. Under the Employment Act, sick leave cannot be encashed...",
                "provisions_cited": {"provision_ids": [1], "sections": ["EA s88A"]},
                "agents_involved": {
                    "agents": ["QueryAnalyzer", "LegalSpecialist", "ResponseSynthesizer"]
                },
                "confidence_score": 0.95,
                "risk_tier": "red",
                "trust_lineage": {
                    "supervisor": "OrchestratorAgent",
                    "delegates": ["LegalSpecialist"],
                },
                "genesis_record": {"query_hash": "abc123", "timestamp": "2026-03-11T12:00:00"},
            },
        )
        r4, _ = runtime.execute(wf4.build())
        session = r4["session"]
        assert session["risk_tier"] == "red"
        assert abs(session["confidence_score"] - 0.95) < 0.01
        assert session["conversation_id"] == conv_id

    def test_feedback_on_session(self, db_instance):
        """User can give feedback on an advisory session."""
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()

        # Minimal chain: user → conv → session
        wf1 = WorkflowBuilder()
        wf1.add_node("UserCreateNode", "u", {"email": "fb@test.sg", "name": "FB User"})
        r1, _ = runtime.execute(wf1.build())

        wf2 = WorkflowBuilder()
        wf2.add_node("ConversationCreateNode", "c", {"user_id": r1["u"]["id"], "title": "Test"})
        r2, _ = runtime.execute(wf2.build())

        wf3 = WorkflowBuilder()
        wf3.add_node(
            "AdvisorySessionCreateNode",
            "s",
            {
                "conversation_id": r2["c"]["id"],
                "user_id": r1["u"]["id"],
                "query_text": "Test query",
            },
        )
        r3, _ = runtime.execute(wf3.build())
        session_id = r3["s"]["id"]

        # Update with feedback
        wf4 = WorkflowBuilder()
        wf4.add_node(
            "AdvisorySessionUpdateNode",
            "fb",
            {
                "conditions": {"id": session_id},
                "updates": {"feedback_rating": "down", "feedback_text": "Answer was too vague"},
            },
        )
        r4, _ = runtime.execute(wf4.build())

        # Read back
        wf5 = WorkflowBuilder()
        wf5.add_node("AdvisorySessionReadNode", "read", {"conditions": {"id": session_id}})
        r5, _ = runtime.execute(wf5.build())
        assert r5["read"]["feedback_rating"] == "down"
        assert r5["read"]["feedback_text"] == "Answer was too vague"


# ---------------------------------------------------------------------------
# Content Update + Template
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="No DB")
class TestContentAndTemplates:
    def test_create_content_update(self, db_instance):
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()
        wf = WorkflowBuilder()
        wf.add_node(
            "ContentUpdateCreateNode",
            "cu",
            {
                "source_url": "https://www.mom.gov.sg/newsroom/2026-cpf-changes",
                "change_summary": "CPF contribution rates increasing from 1 Jan 2027 for employees aged 55-70",
                "affected_domains": {"domain_ids": [1, 2], "names": ["CPF", "Compensation"]},
                "urgency": "high",
                "status": "published",
            },
        )
        results, _ = runtime.execute(wf.build())
        cu = results["cu"]
        assert cu["urgency"] == "high"
        assert cu["status"] == "published"

    def test_create_template(self, db_instance):
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()
        wf = WorkflowBuilder()
        wf.add_node(
            "TemplateCreateNode",
            "tpl",
            {
                "name": "FWA Request Form",
                "template_type": "form",
                "content": "# Flexible Work Arrangement Request\n\nEmployee Name: ___\nRequested arrangement: ___",
                "template_version": 1,
                "linked_provision_ids": {"provision_ids": [10, 11]},
            },
        )
        results, _ = runtime.execute(wf.build())
        tpl = results["tpl"]
        assert tpl["name"] == "FWA Request Form"
        assert tpl["template_type"] == "form"
        assert tpl["template_version"] == 1
