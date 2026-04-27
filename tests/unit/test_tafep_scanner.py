"""Unit tests for TAFEP fair recruitment language scanner.

Tests T-R029 — scan job descriptions for discriminatory language
that may violate TAFEP's Tripartite Guidelines on Fair Employment
Practices (TGFEP).

Covers:
1. Age-related discriminatory patterns
2. Gender-related discriminatory patterns
3. Race/language-related discriminatory patterns
4. Nationality-related discriminatory patterns
5. Marital/family status discriminatory patterns
6. Religion-related discriminatory patterns
7. Clean descriptions pass with no findings
8. Multiple findings in a single description
9. Case insensitivity
10. Position tracking accuracy
"""

import pytest

from hr_advisory.services.tafep_scanner import scan_job_description


# ---------------------------------------------------------------------------
# 1. Age-related patterns
# ---------------------------------------------------------------------------


class TestAgeDiscrimination:
    """Detect age-related discriminatory language."""

    def test_young_detected(self):
        findings = scan_job_description("Looking for young and dynamic team members")
        assert len(findings) >= 1
        age_findings = [f for f in findings if f["category"] == "age"]
        assert len(age_findings) >= 1
        assert any("young" in f["matched_text"] for f in age_findings)

    def test_fresh_graduates_only_detected(self):
        findings = scan_job_description("Fresh graduates only need apply")
        assert len(findings) >= 1
        age_findings = [f for f in findings if f["category"] == "age"]
        assert len(age_findings) >= 1

    def test_below_age_detected(self):
        findings = scan_job_description("Candidates below 30 years preferred")
        assert len(findings) >= 1
        age_findings = [f for f in findings if f["category"] == "age"]
        assert len(age_findings) >= 1

    def test_above_age_detected(self):
        findings = scan_job_description("Must be above 25 years")
        assert len(findings) >= 1
        age_findings = [f for f in findings if f["category"] == "age"]
        assert len(age_findings) >= 1

    def test_specific_age_detected(self):
        findings = scan_job_description("Applicants age 30 and above")
        assert len(findings) >= 1
        age_findings = [f for f in findings if f["category"] == "age"]
        assert len(age_findings) >= 1


# ---------------------------------------------------------------------------
# 2. Gender-related patterns
# ---------------------------------------------------------------------------


class TestGenderDiscrimination:
    """Detect gender-related discriminatory language."""

    def test_female_only_detected(self):
        findings = scan_job_description("Female only candidates may apply")
        assert len(findings) >= 1
        gender_findings = [f for f in findings if f["category"] == "gender"]
        assert len(gender_findings) >= 1

    def test_male_preferred_detected(self):
        findings = scan_job_description("Male candidates preferred for this role")
        assert len(findings) >= 1
        gender_findings = [f for f in findings if f["category"] == "gender"]
        assert len(gender_findings) >= 1

    def test_preferably_female_detected(self):
        findings = scan_job_description("Preferably female for receptionist role")
        assert len(findings) >= 1
        gender_findings = [f for f in findings if f["category"] == "gender"]
        assert len(gender_findings) >= 1


# ---------------------------------------------------------------------------
# 3. Race/language-related patterns
# ---------------------------------------------------------------------------


class TestRaceLanguageDiscrimination:
    """Detect race and language-related discriminatory language."""

    def test_chinese_speaking_detected(self):
        findings = scan_job_description("Must be Chinese-speaking")
        assert len(findings) >= 1
        rl_findings = [f for f in findings if f["category"] == "race_language"]
        assert len(rl_findings) >= 1

    def test_mandarin_speaking_detected(self):
        findings = scan_job_description("Mandarin speaking required")
        assert len(findings) >= 1
        rl_findings = [f for f in findings if f["category"] == "race_language"]
        assert len(rl_findings) >= 1

    def test_malay_speaking_detected(self):
        findings = scan_job_description("Malay speaking candidates preferred")
        assert len(findings) >= 1
        rl_findings = [f for f in findings if f["category"] == "race_language"]
        assert len(rl_findings) >= 1

    def test_tamil_speaking_detected(self):
        findings = scan_job_description("Tamil speaking is a must")
        assert len(findings) >= 1
        rl_findings = [f for f in findings if f["category"] == "race_language"]
        assert len(rl_findings) >= 1

    def test_race_only_detected(self):
        findings = scan_job_description("Chinese only need apply")
        assert len(findings) >= 1
        race_findings = [f for f in findings if f["category"] == "race"]
        assert len(race_findings) >= 1

    def test_race_preferred_detected(self):
        findings = scan_job_description("Malay preferred for this position")
        assert len(findings) >= 1
        race_findings = [f for f in findings if f["category"] == "race"]
        assert len(race_findings) >= 1


# ---------------------------------------------------------------------------
# 4. Nationality-related patterns
# ---------------------------------------------------------------------------


class TestNationalityDiscrimination:
    """Detect nationality-related discriminatory language."""

    def test_singaporeans_only_detected(self):
        findings = scan_job_description("Singaporeans only")
        assert len(findings) >= 1
        nat_findings = [f for f in findings if f["category"] == "nationality"]
        assert len(nat_findings) >= 1

    def test_pr_only_detected(self):
        findings = scan_job_description("PR only need apply")
        assert len(findings) >= 1
        nat_findings = [f for f in findings if f["category"] == "nationality"]
        assert len(nat_findings) >= 1


# ---------------------------------------------------------------------------
# 5. Marital/family status patterns
# ---------------------------------------------------------------------------


class TestMaritalFamilyDiscrimination:
    """Detect marital and family status discriminatory language."""

    def test_single_only_detected(self):
        findings = scan_job_description("Single only need apply")
        assert len(findings) >= 1
        marital_findings = [f for f in findings if f["category"] == "marital"]
        assert len(marital_findings) >= 1

    def test_no_children_detected(self):
        findings = scan_job_description("Candidate must have no children")
        assert len(findings) >= 1
        family_findings = [f for f in findings if f["category"] == "family"]
        assert len(family_findings) >= 1

    def test_unmarried_detected(self):
        findings = scan_job_description("Unmarried individuals preferred")
        assert len(findings) >= 1
        marital_findings = [f for f in findings if f["category"] == "marital"]
        assert len(marital_findings) >= 1


# ---------------------------------------------------------------------------
# 6. Religion-related patterns
# ---------------------------------------------------------------------------


class TestReligionDiscrimination:
    """Detect religion-related discriminatory language."""

    def test_muslim_only_detected(self):
        findings = scan_job_description("Muslim only may apply")
        assert len(findings) >= 1
        religion_findings = [f for f in findings if f["category"] == "religion"]
        assert len(religion_findings) >= 1

    def test_christian_preferred_detected(self):
        findings = scan_job_description("Christian preferred for this church admin role")
        assert len(findings) >= 1
        religion_findings = [f for f in findings if f["category"] == "religion"]
        assert len(religion_findings) >= 1


# ---------------------------------------------------------------------------
# 7. Clean descriptions pass
# ---------------------------------------------------------------------------


class TestCleanDescriptions:
    """Non-discriminatory descriptions should return no findings."""

    def test_clean_job_description(self):
        desc = (
            "We are looking for a motivated software engineer with 3+ years "
            "of experience in Python and cloud technologies. The ideal candidate "
            "is a team player with strong communication skills."
        )
        findings = scan_job_description(desc)
        assert findings == []

    def test_empty_description(self):
        findings = scan_job_description("")
        assert findings == []

    def test_neutral_language(self):
        desc = (
            "All qualified candidates are encouraged to apply. "
            "We offer competitive salary and benefits."
        )
        findings = scan_job_description(desc)
        assert findings == []


# ---------------------------------------------------------------------------
# 8. Multiple findings
# ---------------------------------------------------------------------------


class TestMultipleFindings:
    """Multiple discriminatory patterns in a single description."""

    def test_multiple_categories_detected(self):
        desc = (
            "Looking for young female Chinese-speaking candidates. "
            "Singaporeans only. Single preferred."
        )
        findings = scan_job_description(desc)
        categories = {f["category"] for f in findings}
        assert "age" in categories
        assert "gender" in categories
        assert "race_language" in categories
        assert "nationality" in categories
        assert "marital" in categories
        assert len(findings) >= 5


# ---------------------------------------------------------------------------
# 9. Case insensitivity
# ---------------------------------------------------------------------------


class TestCaseInsensitivity:
    """Patterns should match regardless of case."""

    def test_uppercase_detected(self):
        findings = scan_job_description("YOUNG candidates wanted")
        assert len(findings) >= 1
        assert any(f["category"] == "age" for f in findings)

    def test_mixed_case_detected(self):
        findings = scan_job_description("Mandarin Speaking required")
        assert len(findings) >= 1
        assert any(f["category"] == "race_language" for f in findings)


# ---------------------------------------------------------------------------
# 10. Finding structure
# ---------------------------------------------------------------------------


class TestFindingStructure:
    """Each finding must have the correct structure."""

    def test_finding_has_required_fields(self):
        findings = scan_job_description("Looking for young candidates")
        assert len(findings) >= 1
        finding = findings[0]
        assert "matched_text" in finding
        assert "category" in finding
        assert "suggestion" in finding
        assert "position" in finding

    def test_position_is_correct(self):
        text = "We want young people"
        findings = scan_job_description(text)
        assert len(findings) >= 1
        finding = findings[0]
        # "young" should start at position 8 in the lowered text
        assert finding["position"] == text.lower().index("young")

    def test_suggestion_is_nonempty(self):
        findings = scan_job_description("Fresh graduates only please")
        assert len(findings) >= 1
        for f in findings:
            assert f["suggestion"], f"Finding for '{f['matched_text']}' has empty suggestion"
