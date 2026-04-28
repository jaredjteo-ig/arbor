"""Unit tests for the ScorecardAgent (T-R054).

Tier 1: Fast, isolated, no external dependencies.
Uses ``llm_provider="mock"`` plus ``patch.object`` over ``run`` so no real
LLM call is made.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from hr_advisory.agents.scorecard_agent import (
    ScorecardAgent,
    ScorecardAgentConfig,
    ScorecardSignature,
    VALID_DECISIONS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config() -> ScorecardAgentConfig:
    """Config that uses the mock provider so no real API call happens."""
    return ScorecardAgentConfig(llm_provider="mock", model="mock-model")


@pytest.fixture
def agent(mock_config: ScorecardAgentConfig) -> ScorecardAgent:
    return ScorecardAgent(config=mock_config)


@pytest.fixture
def sample_candidate() -> dict:
    return {
        "id": 101,
        "name": "Alex Tan",
        "email": "alex@example.com",
        "current_role": "Senior Backend Engineer",
        "experience_summary": (
            "8 years building Python distributed systems; led migration "
            "from monolith to microservices at a Series-B SaaS startup."
        ),
        "skills": ["Python", "PostgreSQL", "Kafka", "AWS", "Kubernetes"],
        "education": "B.Eng (Computer Science), NUS",
        "resume_excerpt": (
            "Designed and shipped event-driven order pipeline handling "
            "10M events/day. Mentored four juniors."
        ),
    }


@pytest.fixture
def sample_job() -> dict:
    return {
        "id": 7,
        "title": "Staff Backend Engineer",
        "department": "Engineering",
        "employment_type": "full_time",
        "description": (
            "Own the core orders platform end-to-end. Drive technical "
            "direction across two squads."
        ),
        "requirements": (
            "7+ years backend Python; deep PostgreSQL; event-driven "
            "architectures; mentoring; production-grade observability."
        ),
    }


@pytest.fixture
def sample_template() -> dict:
    return {
        "id": 3,
        "name": "Senior Engineering Scorecard",
        "description": "Used for IC4+ engineering hires",
        "criteria": [
            {"name": "Technical depth", "weight": 0.4},
            {"name": "System design", "weight": 0.3},
            {"name": "Communication", "weight": 0.15},
            {"name": "Mentorship", "weight": 0.15},
        ],
    }


@pytest.fixture
def sample_feedback() -> list[dict]:
    return [
        {
            "id": 11,
            "interview_id": 21,
            "overall_rating": 4,
            "strengths": "Strong systems thinking; clear trade-off articulation.",
            "weaknesses": "Light on observability tooling specifics.",
            "notes": "Walked through Kafka rebalancing in detail.",
            "recommendation": "proceed",
        },
        {
            "id": 12,
            "interview_id": 22,
            "overall_rating": 4,
            "strengths": "Good mentor stories; calm under pressure.",
            "weaknesses": "Did not lead architectural debate proactively.",
            "notes": "Behavioural round with hiring manager.",
            "recommendation": "proceed",
        },
    ]


def _llm_response(
    overall_fit: str = "4.2",
    decision: str = "proceed",
    ratings: dict | None = None,
) -> dict:
    """Build a fake LLM response shaped like the agent's signature."""
    if ratings is None:
        ratings = {
            "Technical depth": 5,
            "System design": 4,
            "Communication": 4,
            "Mentorship": 4,
        }
    return {
        "overall_fit": overall_fit,
        "competency_ratings": ratings,
        "strengths": [
            "Deep distributed-systems experience.",
            "Track record mentoring juniors.",
        ],
        "concerns": [
            "Less direct experience with company's specific observability stack.",
        ],
        "recommended_decision": decision,
        "narrative": (
            "Alex's eight years on event-driven systems align well with "
            "the staff role's scope. Interview feedback was consistent on "
            "technical strength; the only minor gap is observability tooling, "
            "which is coachable. Recommend moving forward."
        ),
    }


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestInitialisation:
    def test_agent_constructs_with_mock_provider(self, agent: ScorecardAgent) -> None:
        assert agent is not None
        assert agent.domain == "scorecard"
        assert agent.config.llm_provider == "mock"

    def test_default_signature_is_scorecard_signature(self, agent: ScorecardAgent) -> None:
        sig = agent._default_signature()
        assert isinstance(sig, ScorecardSignature)

    def test_system_prompt_contains_protected_attributes_rule(
        self, agent: ScorecardAgent,
    ) -> None:
        prompt = agent._generate_system_prompt()
        assert "protected attributes" in prompt.lower()
        assert "1-5" in prompt


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestGenerateHappyPath:
    def _patched_run(
        self,
        agent: ScorecardAgent,
        fake_result: dict,
    ):
        # Mock both run() and the extract_* helpers so we can drive the
        # agent without exercising Kaizen's dict/JSON-aware extractors.
        return [
            patch.object(agent, "run", return_value=fake_result),
            patch.object(
                agent,
                "extract_str",
                side_effect=lambda r, k, default="": r.get(k, default)
                if isinstance(r.get(k, default), str)
                else str(r.get(k, default)),
            ),
            patch.object(
                agent,
                "extract_dict",
                side_effect=lambda r, k, default=None: r.get(
                    k, default if default is not None else {},
                ),
            ),
            patch.object(
                agent,
                "extract_list",
                side_effect=lambda r, k, default=None: r.get(
                    k, default if default is not None else [],
                ),
            ),
        ]

    def test_returns_structured_scorecard_dict(
        self,
        agent: ScorecardAgent,
        sample_candidate: dict,
        sample_job: dict,
        sample_template: dict,
        sample_feedback: list[dict],
    ) -> None:
        fake = _llm_response()
        patches = self._patched_run(agent, fake)
        for p in patches:
            p.start()
        try:
            output = agent.generate(
                candidate_profile=sample_candidate,
                job_listing=sample_job,
                scorecard_template=sample_template,
                interview_feedback=sample_feedback,
            )
        finally:
            for p in patches:
                p.stop()

        assert "scorecard" in output
        assert output["degraded"] is False
        sc = output["scorecard"]
        assert sc["template_id"] == 3
        assert sc["template_name"] == "Senior Engineering Scorecard"
        assert sc["overall_fit"] == 4.2
        assert sc["recommended_decision"] == "proceed"
        assert sc["recommended_decision"] in VALID_DECISIONS
        assert isinstance(sc["competency_ratings"], dict)
        assert set(sc["competency_ratings"].keys()) == {
            "Technical depth",
            "System design",
            "Communication",
            "Mentorship",
        }
        assert all(1 <= v <= 5 for v in sc["competency_ratings"].values())
        assert isinstance(sc["strengths"], list)
        assert isinstance(sc["concerns"], list)
        assert sc["strengths"]
        assert sc["narrative"]
        assert sc["criteria"][0]["name"] == "Technical depth"

    def test_run_is_called_with_json_serialised_inputs(
        self,
        agent: ScorecardAgent,
        sample_candidate: dict,
        sample_job: dict,
        sample_template: dict,
        sample_feedback: list[dict],
    ) -> None:
        fake = _llm_response()
        patches = self._patched_run(agent, fake)
        for p in patches:
            p.start()
        try:
            agent.generate(
                candidate_profile=sample_candidate,
                job_listing=sample_job,
                scorecard_template=sample_template,
                interview_feedback=sample_feedback,
            )
            run_mock = agent.run  # type: ignore[assignment]
            assert run_mock.called
            kwargs = run_mock.call_args.kwargs
            for key in (
                "candidate_profile",
                "job_listing",
                "scorecard_template",
                "interview_feedback",
            ):
                assert isinstance(kwargs[key], str)
            # Round-trip a couple to confirm valid JSON.
            import json
            assert json.loads(kwargs["candidate_profile"])["name"] == "Alex Tan"
            assert json.loads(kwargs["scorecard_template"])["criteria"][0][
                "name"
            ] == "Technical depth"
            assert isinstance(json.loads(kwargs["interview_feedback"]), list)
        finally:
            for p in patches:
                p.stop()

    def test_no_feedback_defaults_to_empty_list(
        self,
        agent: ScorecardAgent,
        sample_candidate: dict,
        sample_job: dict,
        sample_template: dict,
    ) -> None:
        fake = _llm_response()
        patches = self._patched_run(agent, fake)
        for p in patches:
            p.start()
        try:
            agent.generate(
                candidate_profile=sample_candidate,
                job_listing=sample_job,
                scorecard_template=sample_template,
                interview_feedback=None,
            )
            kwargs = agent.run.call_args.kwargs  # type: ignore[attr-defined]
            assert kwargs["interview_feedback"] == "[]"
        finally:
            for p in patches:
                p.stop()


# ---------------------------------------------------------------------------
# Resilience / degraded paths
# ---------------------------------------------------------------------------


class TestResilience:
    def test_invalid_decision_falls_back_to_further_interview(
        self,
        agent: ScorecardAgent,
        sample_candidate: dict,
        sample_job: dict,
        sample_template: dict,
    ) -> None:
        fake = _llm_response(decision="hire_immediately")
        helpers = TestGenerateHappyPath()._patched_run(agent, fake)
        for p in helpers:
            p.start()
        try:
            output = agent.generate(
                candidate_profile=sample_candidate,
                job_listing=sample_job,
                scorecard_template=sample_template,
            )
        finally:
            for p in helpers:
                p.stop()

        assert output["scorecard"]["recommended_decision"] == "further_interview"
        assert output["degraded"] is True

    def test_unparseable_overall_fit_marks_degraded(
        self,
        agent: ScorecardAgent,
        sample_candidate: dict,
        sample_job: dict,
        sample_template: dict,
    ) -> None:
        fake = _llm_response(overall_fit="excellent")
        helpers = TestGenerateHappyPath()._patched_run(agent, fake)
        for p in helpers:
            p.start()
        try:
            output = agent.generate(
                candidate_profile=sample_candidate,
                job_listing=sample_job,
                scorecard_template=sample_template,
            )
        finally:
            for p in helpers:
                p.stop()

        assert output["degraded"] is True
        assert output["scorecard"]["overall_fit"] == 0.0

    def test_ratings_outside_1_5_are_clamped(
        self,
        agent: ScorecardAgent,
        sample_candidate: dict,
        sample_job: dict,
        sample_template: dict,
    ) -> None:
        fake = _llm_response(
            ratings={
                "Technical depth": 9,  # too high -> 5
                "System design": -2,  # too low -> 1
                "Communication": 3.6,  # rounds -> 4
                "Mentorship": 4,
            },
        )
        helpers = TestGenerateHappyPath()._patched_run(agent, fake)
        for p in helpers:
            p.start()
        try:
            output = agent.generate(
                candidate_profile=sample_candidate,
                job_listing=sample_job,
                scorecard_template=sample_template,
            )
        finally:
            for p in helpers:
                p.stop()

        ratings = output["scorecard"]["competency_ratings"]
        assert ratings["Technical depth"] == 5
        assert ratings["System design"] == 1
        assert ratings["Communication"] == 4
        assert ratings["Mentorship"] == 4

    def test_unknown_rating_keys_are_ignored(
        self,
        agent: ScorecardAgent,
        sample_candidate: dict,
        sample_job: dict,
        sample_template: dict,
    ) -> None:
        fake = _llm_response(
            ratings={
                "Technical depth": 4,
                "Made-up criterion": 5,  # not in template -> dropped
            },
        )
        helpers = TestGenerateHappyPath()._patched_run(agent, fake)
        for p in helpers:
            p.start()
        try:
            output = agent.generate(
                candidate_profile=sample_candidate,
                job_listing=sample_job,
                scorecard_template=sample_template,
            )
        finally:
            for p in helpers:
                p.stop()

        ratings = output["scorecard"]["competency_ratings"]
        assert "Made-up criterion" not in ratings
        assert ratings["Technical depth"] == 4
        # Missing several criteria -> degraded.
        assert output["degraded"] is True

    def test_llm_exception_returns_fallback_scorecard(
        self,
        agent: ScorecardAgent,
        sample_candidate: dict,
        sample_job: dict,
        sample_template: dict,
    ) -> None:
        with patch.object(agent, "run", side_effect=RuntimeError("LLM unavailable")):
            output = agent.generate(
                candidate_profile=sample_candidate,
                job_listing=sample_job,
                scorecard_template=sample_template,
            )

        assert output["degraded"] is True
        sc = output["scorecard"]
        assert sc["recommended_decision"] == "further_interview"
        assert sc["overall_fit"] == 0.0
        assert sc["error"] == "LLM unavailable"
        assert set(sc["competency_ratings"].keys()) == {
            "Technical depth",
            "System design",
            "Communication",
            "Mentorship",
        }
        assert "manually" in sc["narrative"].lower()

    def test_template_with_json_string_criteria_is_parsed(
        self,
        agent: ScorecardAgent,
        sample_candidate: dict,
        sample_job: dict,
    ) -> None:
        import json as _json

        template = {
            "id": 9,
            "name": "Stringified",
            "description": "",
            "criteria": _json.dumps(
                [
                    {"name": "Technical depth", "weight": 0.6},
                    {"name": "Communication", "weight": 0.4},
                ],
            ),
        }
        fake = _llm_response(
            ratings={"Technical depth": 5, "Communication": 4},
        )
        helpers = TestGenerateHappyPath()._patched_run(agent, fake)
        for p in helpers:
            p.start()
        try:
            output = agent.generate(
                candidate_profile=sample_candidate,
                job_listing=sample_job,
                scorecard_template=template,
            )
        finally:
            for p in helpers:
                p.stop()

        sc = output["scorecard"]
        assert sc["criteria"] == [
            {"name": "Technical depth", "weight": 0.6},
            {"name": "Communication", "weight": 0.4},
        ]
        assert set(sc["competency_ratings"].keys()) == {
            "Technical depth",
            "Communication",
        }
