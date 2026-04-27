"""Unit tests for recruitment demo data seeding.

Tests the _seed_demo_recruitment_data() function that populates the
recruitment pipeline with realistic demo candidates, interviews,
feedback, and offers across seeded job listings.

All tests use mocks for dataflow_crud since this is Tier 1 (unit).
"""

import pytest
from unittest.mock import patch, MagicMock, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Auto-incrementing ID generator for mock creates
def _make_id_counter(start=100):
    """Return a side_effect function that returns incrementing IDs."""
    counter = {"val": start}

    def _create(model_name, data):
        result = {**data, "id": counter["val"]}
        counter["val"] += 1
        return result

    return _create


# ---------------------------------------------------------------------------
# 1. Idempotency — skip if candidates already exist
# ---------------------------------------------------------------------------


class TestRecruitmentSeedingIdempotency:
    """Seeding must be idempotent — no duplicates on repeat calls."""

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_skips_when_candidates_already_exist(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        mock_crud.list_records.return_value = [{"id": 1, "name": "Existing"}]

        result = _seed_demo_recruitment_data(company_id=1)

        assert result["skipped"] is True
        assert "already exist" in result["reason"]
        mock_crud.create.assert_not_called()

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_proceeds_when_no_candidates_exist(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        # First call: no candidates; subsequent calls: return job listings
        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        result = _seed_demo_recruitment_data(company_id=1)

        assert "skipped" not in result
        assert mock_crud.create.called


# ---------------------------------------------------------------------------
# 2. Candidate creation
# ---------------------------------------------------------------------------


class TestCandidateCreation:
    """Candidates are created with realistic Singapore data."""

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_creates_candidates_for_both_jobs(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        result = _seed_demo_recruitment_data(company_id=1)

        # Should create candidates across both job listings
        candidate_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "Candidate"
        ]
        assert len(candidate_creates) >= 8, (
            f"Expected at least 8 candidates, got {len(candidate_creates)}"
        )

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_candidate_fields_are_complete(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        _seed_demo_recruitment_data(company_id=1)

        candidate_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "Candidate"
        ]
        required_fields = {
            "company_id", "job_listing_id", "name", "email", "phone",
            "nationality", "citizenship_status", "source", "stage",
            "pdpa_consent", "pdpa_consent_date",
        }
        for create_call in candidate_creates:
            data = create_call[0][1]
            missing = required_fields - set(data.keys())
            assert not missing, (
                f"Candidate {data.get('name', '?')} missing fields: {missing}"
            )

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_candidate_company_id_matches(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        _seed_demo_recruitment_data(company_id=42)

        candidate_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "Candidate"
        ]
        for create_call in candidate_creates:
            data = create_call[0][1]
            assert data["company_id"] == 42, (
                f"Candidate {data['name']} has wrong company_id: {data['company_id']}"
            )

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_candidate_stages_are_distributed(self, mock_crud):
        """Job 1 should have all pipeline stages covered."""
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        _seed_demo_recruitment_data(company_id=1)

        candidate_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "Candidate"
        ]
        stages = {c[0][1]["stage"] for c in candidate_creates}
        expected_stages = {"new", "screening", "interview", "offered", "hired", "rejected"}
        assert expected_stages.issubset(stages), (
            f"Missing stages: {expected_stages - stages}"
        )

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_candidate_pdpa_consent_is_true(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        _seed_demo_recruitment_data(company_id=1)

        candidate_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "Candidate"
        ]
        for create_call in candidate_creates:
            data = create_call[0][1]
            assert data["pdpa_consent"] is True, (
                f"Candidate {data['name']} does not have PDPA consent"
            )
            assert data["pdpa_consent_date"], (
                f"Candidate {data['name']} missing pdpa_consent_date"
            )


# ---------------------------------------------------------------------------
# 3. Interview creation
# ---------------------------------------------------------------------------


class TestInterviewCreation:
    """Interviews should be created for candidates at the 'interview' stage."""

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_creates_interviews_for_interview_stage_candidates(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        _seed_demo_recruitment_data(company_id=1)

        interview_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "InterviewSchedule"
        ]
        assert len(interview_creates) >= 2, (
            f"Expected at least 2 interviews, got {len(interview_creates)}"
        )

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_interview_fields_are_complete(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        _seed_demo_recruitment_data(company_id=1)

        interview_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "InterviewSchedule"
        ]
        required_fields = {
            "candidate_id", "company_id", "interview_type",
            "scheduled_at", "duration_minutes", "status",
        }
        for create_call in interview_creates:
            data = create_call[0][1]
            missing = required_fields - set(data.keys())
            assert not missing, (
                f"Interview missing fields: {missing}"
            )


# ---------------------------------------------------------------------------
# 4. Feedback creation
# ---------------------------------------------------------------------------


class TestFeedbackCreation:
    """Feedback should be created for completed interviews."""

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_creates_feedback_for_completed_interviews(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        _seed_demo_recruitment_data(company_id=1)

        feedback_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "InterviewFeedback"
        ]
        assert len(feedback_creates) >= 2, (
            f"Expected at least 2 feedback records, got {len(feedback_creates)}"
        )

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_feedback_has_ratings_and_recommendations(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        _seed_demo_recruitment_data(company_id=1)

        feedback_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "InterviewFeedback"
        ]
        for create_call in feedback_creates:
            data = create_call[0][1]
            assert data["overall_rating"] > 0, "Feedback must have a rating"
            assert data["recommendation"], "Feedback must have a recommendation"
            assert data["strengths"], "Feedback must have strengths"


# ---------------------------------------------------------------------------
# 5. Offer creation
# ---------------------------------------------------------------------------


class TestOfferCreation:
    """An offer should be created for the candidate at 'offered' stage."""

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_creates_offer_for_offered_candidate(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        _seed_demo_recruitment_data(company_id=1)

        offer_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "Offer"
        ]
        assert len(offer_creates) == 1, (
            f"Expected exactly 1 offer, got {len(offer_creates)}"
        )

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_offer_fields_are_complete(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        _seed_demo_recruitment_data(company_id=1)

        offer_creates = [
            c for c in mock_crud.create.call_args_list
            if c[0][0] == "Offer"
        ]
        required_fields = {
            "candidate_id", "job_listing_id", "company_id",
            "salary", "currency", "salary_period", "start_date",
            "position_title", "employment_type", "probation_months",
            "notice_period_days", "benefits_summary", "status",
            "created_by",
        }
        data = offer_creates[0][0][1]
        missing = required_fields - set(data.keys())
        assert not missing, f"Offer missing fields: {missing}"
        assert data["salary"] > 0, "Offer salary must be positive"
        assert data["currency"] == "SGD", "Offer currency must be SGD"
        assert data["status"] == "sent", "Offer status must be 'sent'"


# ---------------------------------------------------------------------------
# 6. Summary / return value
# ---------------------------------------------------------------------------


class TestSeedingSummary:
    """The return value should summarise everything that was created."""

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_returns_creation_counts(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return [
                    {"id": 10, "title": "Senior Software Engineer"},
                    {"id": 20, "title": "HR Executive"},
                ]
            return []

        mock_crud.list_records.side_effect = list_side_effect
        mock_crud.create.side_effect = _make_id_counter(100)

        result = _seed_demo_recruitment_data(company_id=1)

        assert "created" in result
        created = result["created"]
        assert created["candidates"] >= 8
        assert created["interviews"] >= 2
        assert created["feedback"] >= 2
        assert created["offers"] == 1


# ---------------------------------------------------------------------------
# 7. Edge case: no job listings exist
# ---------------------------------------------------------------------------


class TestNoJobListings:
    """If no job listings exist, seeding should handle it gracefully."""

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    def test_returns_error_when_no_job_listings(self, mock_crud):
        from hr_advisory.services.company_seeding import _seed_demo_recruitment_data

        def list_side_effect(model_name, filter_dict=None, **kwargs):
            if model_name == "Candidate":
                return []
            if model_name == "JobListing":
                return []  # No job listings
            return []

        mock_crud.list_records.side_effect = list_side_effect

        result = _seed_demo_recruitment_data(company_id=1)

        assert result["skipped"] is True
        assert "job listing" in result["reason"].lower()
        mock_crud.create.assert_not_called()


# ---------------------------------------------------------------------------
# 8. Integration with seed_company_defaults
# ---------------------------------------------------------------------------


class TestIntegrationWithSeedCompanyDefaults:
    """_seed_demo_recruitment_data should be registered in seed_company_defaults."""

    @patch("hr_advisory.services.company_seeding.dataflow_crud")
    @patch("hr_advisory.services.company_seeding._execute_node")
    def test_recruitment_data_is_in_seed_list(self, mock_exec, mock_crud):
        from hr_advisory.services.company_seeding import seed_company_defaults

        # Make all sub-seeders return quickly
        mock_exec.return_value = []
        mock_crud.list_records.return_value = [{"id": 1}]  # Skip everything
        mock_crud.create.return_value = {"id": 1}

        result = seed_company_defaults(company_id=1)

        assert "recruitment_data" in result, (
            "seed_company_defaults must include 'recruitment_data' in its seeding list"
        )
