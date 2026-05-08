"""Unit tests for the Xero payroll-journal builder + auto-matcher.

Pure-logic tests — no DB, no HTTP. Cover:
- auto_match_accounts: name-based matching, type guard, no-match fallback
- mapping_is_complete / missing_buckets
- build_journal_lines: balance invariant, realistic SG payroll, FWL+SHG,
  bonus split, error cases (incomplete mapping, bonus > gross, unbalanced
  inputs, zero-total run)
"""

from __future__ import annotations

import pytest

from hr_advisory.services.xero_payroll_journal import (
    MAPPING_FIELDS,
    auto_match_accounts,
    build_journal_lines,
    mapping_is_complete,
    missing_buckets,
)


# A typical SG SME chart of accounts after Xero default + payroll setup.
_SG_CHART = [
    {"Code": "477", "Name": "Wages and Salaries", "Type": "EXPENSE"},
    {"Code": "480", "Name": "Bonus Expense", "Type": "EXPENSE"},
    {"Code": "481", "Name": "CPF - Employer", "Type": "EXPENSE"},
    {"Code": "482", "Name": "SDL Expense", "Type": "EXPENSE"},
    {"Code": "825", "Name": "CPF Payable", "Type": "CURRLIAB"},
    {"Code": "814", "Name": "Net Wages Payable", "Type": "CURRLIAB"},
    {"Code": "200", "Name": "Sales", "Type": "REVENUE"},
    {"Code": "310", "Name": "Cost of Goods Sold", "Type": "DIRECTCOSTS"},
]


def _complete_mapping() -> dict:
    return {
        "salary_expense_code": "477",
        "bonus_expense_code": "480",
        "employer_cpf_expense_code": "481",
        "sdl_expense_code": "482",
        "cpf_payable_code": "825",
        "net_pay_payable_code": "814",
    }


def _balanced_run(**overrides) -> dict:
    """A payroll run where gross - net == employee_cpf + shg."""
    base = {
        "period_start": "2026-04-01",
        "period_end": "2026-04-30",
        "pay_date": "2026-05-01",
        "total_gross": 10000.0,
        "total_net": 8000.0,
        "total_employer_cpf": 1700.0,
        "total_employee_cpf": 2000.0,
        "total_sdl": 25.0,
        "total_fwl": 0.0,
        "total_shg": 0.0,
    }
    base.update(overrides)
    return base


# ────────────────────────────────────────────────────────────────────
# auto_match_accounts
# ────────────────────────────────────────────────────────────────────


def test_auto_match_finds_all_six_in_typical_sg_chart():
    result = auto_match_accounts(_SG_CHART)
    assert result == _complete_mapping()


def test_auto_match_returns_empty_string_for_unmatched_bucket():
    # Chart with no SDL account at all
    chart = [
        a for a in _SG_CHART if "sdl" not in a["Name"].lower()
    ]
    result = auto_match_accounts(chart)
    assert result["sdl_expense_code"] == ""
    # The other five should still be found
    for field in MAPPING_FIELDS:
        if field != "sdl_expense_code":
            assert result[field] != ""


def test_auto_match_type_guard_skips_expense_for_liability_bucket():
    # An "expense" account literally named "CPF Payable" should NOT be
    # picked for the cpf_payable_code bucket (which wants a liability).
    chart = [
        {"Code": "999", "Name": "CPF Payable", "Type": "EXPENSE"},
        {"Code": "825", "Name": "CPF Payable", "Type": "CURRLIAB"},
    ]
    result = auto_match_accounts(chart)
    assert result["cpf_payable_code"] == "825"


def test_auto_match_handles_lowercase_dict_keys():
    # Adapter sometimes returns lower-case keys; matcher should normalize.
    chart = [
        {"code": "477", "name": "Wages and Salaries", "type": "expense"},
    ]
    result = auto_match_accounts(chart)
    assert result["salary_expense_code"] == "477"


def test_auto_match_empty_chart_returns_all_empty():
    result = auto_match_accounts([])
    assert result == {field: "" for field in MAPPING_FIELDS}


# ────────────────────────────────────────────────────────────────────
# mapping_is_complete / missing_buckets
# ────────────────────────────────────────────────────────────────────


def test_mapping_is_complete_true_for_full_mapping():
    assert mapping_is_complete(_complete_mapping())
    assert missing_buckets(_complete_mapping()) == []


def test_mapping_is_complete_false_with_empty_field():
    m = _complete_mapping()
    m["sdl_expense_code"] = ""
    assert not mapping_is_complete(m)
    assert missing_buckets(m) == ["sdl_expense_code"]


def test_mapping_is_complete_treats_whitespace_as_empty():
    m = _complete_mapping()
    m["cpf_payable_code"] = "   "
    assert not mapping_is_complete(m)


# ────────────────────────────────────────────────────────────────────
# build_journal_lines
# ────────────────────────────────────────────────────────────────────


def test_build_journal_balances_for_realistic_sg_payroll():
    result = build_journal_lines(
        payroll_run=_balanced_run(),
        mapping=_complete_mapping(),
        bonus_total=1000.0,
    )
    total = round(sum(line["amount"] for line in result["lines"]), 2)
    assert total == 0.0
    # 6 lines: salary, bonus, employer cpf, sdl, cpf payable, net
    assert len(result["lines"]) == 6


def test_build_journal_includes_fwl_and_shg():
    run = _balanced_run(
        total_fwl=50.0,
        total_shg=100.0,
        total_net=7900.0,  # net is reduced by SHG deduction (employee-borne)
    )
    result = build_journal_lines(
        payroll_run=run, mapping=_complete_mapping(), bonus_total=0.0
    )
    total = round(sum(line["amount"] for line in result["lines"]), 2)
    assert total == 0.0
    # SDL line should be sdl + fwl = 75
    sdl_line = next(
        line for line in result["lines"] if line["account_code"] == "482"
    )
    assert sdl_line["amount"] == 75.0
    assert "FWL" in sdl_line["description"]


def test_build_journal_skips_zero_bonus_line():
    result = build_journal_lines(
        payroll_run=_balanced_run(),
        mapping=_complete_mapping(),
        bonus_total=0.0,
    )
    # No bonus line emitted when bonus_total == 0
    bonus_codes = [
        line for line in result["lines"] if line["account_code"] == "480"
    ]
    assert bonus_codes == []


def test_build_journal_raises_on_incomplete_mapping():
    incomplete = _complete_mapping()
    incomplete["sdl_expense_code"] = ""
    with pytest.raises(ValueError, match="incomplete"):
        build_journal_lines(
            payroll_run=_balanced_run(),
            mapping=incomplete,
            bonus_total=0.0,
        )


def test_build_journal_raises_when_bonus_exceeds_gross():
    with pytest.raises(ValueError, match="bonus_total"):
        build_journal_lines(
            payroll_run=_balanced_run(total_gross=500.0),
            mapping=_complete_mapping(),
            bonus_total=1000.0,
        )


def test_build_journal_raises_on_imbalanced_input():
    # gross - net != employee_cpf + shg → unbalanced journal
    bad = _balanced_run(total_net=7000.0)  # employee_cpf says 2000, but gross-net=3000
    with pytest.raises(ValueError, match="balance"):
        build_journal_lines(
            payroll_run=bad,
            mapping=_complete_mapping(),
            bonus_total=0.0,
        )


def test_build_journal_raises_on_zero_total_run():
    empty = {
        "period_start": "2026-04-01",
        "period_end": "2026-04-30",
        "pay_date": "2026-05-01",
        "total_gross": 0.0,
        "total_net": 0.0,
        "total_employer_cpf": 0.0,
        "total_employee_cpf": 0.0,
        "total_sdl": 0.0,
        "total_fwl": 0.0,
        "total_shg": 0.0,
    }
    with pytest.raises(ValueError, match="no monetary totals"):
        build_journal_lines(
            payroll_run=empty,
            mapping=_complete_mapping(),
            bonus_total=0.0,
        )


def test_build_journal_uses_pay_date_falls_back_to_period_end():
    run = _balanced_run(pay_date="")
    result = build_journal_lines(
        payroll_run=run, mapping=_complete_mapping(), bonus_total=0.0
    )
    assert result["date"] == "2026-04-30"


def test_build_journal_custom_narration_overrides_default():
    result = build_journal_lines(
        payroll_run=_balanced_run(),
        mapping=_complete_mapping(),
        bonus_total=0.0,
        narration="Custom memo for April",
    )
    assert result["narration"] == "Custom memo for April"


def test_every_line_has_basexcluded_tax_type():
    """SG GST-registered companies (>S$1M turnover) must mark salary
    journals as out-of-scope (BASEXCLUDED) for IRAS GST F5. Without
    this, the customer's GST return is silently wrong — they will
    blame Arbor.
    """
    result = build_journal_lines(
        payroll_run=_balanced_run(total_fwl=50.0, total_shg=100.0, total_net=7900.0),
        mapping=_complete_mapping(),
        bonus_total=1000.0,
    )
    for line in result["lines"]:
        assert line.get("tax_type") == "BASEXCLUDED", (
            f"line missing BASEXCLUDED tax_type: {line}"
        )


def test_journal_data_marks_no_tax_at_journal_level():
    """At the journal level, line_amount_types must be NoTax so Xero
    doesn't try to apply tax to the gross amounts."""
    result = build_journal_lines(
        payroll_run=_balanced_run(),
        mapping=_complete_mapping(),
        bonus_total=0.0,
    )
    assert result.get("line_amount_types") == "NoTax"
