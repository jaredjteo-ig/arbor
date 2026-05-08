"""Build Xero ManualJournal payloads from PayrollRun aggregates.

Two responsibilities:

1. ``auto_match_accounts`` — fuzzy-matches a Xero chart of accounts to the
   six buckets we need (salary expense, bonus expense, employer CPF expense,
   SDL expense, CPF payable, net pay payable). Used to pre-fill the mapping
   modal on first export.

2. ``build_journal_lines`` — converts a PayrollRun + its mapping into the
   ``journal_data`` shape that ``XeroAdapter.post_payroll_journal`` expects.
   Validates debits == credits before returning.

Xero convention: positive ``amount`` = debit, negative = credit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

logger = logging.getLogger(__name__)


# Six buckets the company must map to Xero account codes before exporting.
MAPPING_FIELDS: tuple[str, ...] = (
    "salary_expense_code",
    "bonus_expense_code",
    "employer_cpf_expense_code",
    "sdl_expense_code",
    "cpf_payable_code",
    "net_pay_payable_code",
)

# Patterns the auto-matcher looks for in Xero account names. Order within a
# bucket is "best signal first." All comparisons are case-insensitive.
_AUTO_MATCH_PATTERNS: dict[str, tuple[str, ...]] = {
    "salary_expense_code": (
        "wages and salaries",
        "salaries and wages",
        "salary expense",
        "wages expense",
        "salaries",
        "wages",
        "payroll expense",
    ),
    "bonus_expense_code": (
        "bonus expense",
        "bonus",
        "incentive",
        "commissions",
    ),
    "employer_cpf_expense_code": (
        "cpf - employer",
        "employer cpf",
        "cpf employer",
        "cpf contribution",
        "cpf expense",
    ),
    "sdl_expense_code": (
        "sdl",
        "skills development levy",
        "skills development",
    ),
    "cpf_payable_code": (
        "cpf payable",
        "cpf - payable",
        "cpf liability",
        "statutory payable",
    ),
    "net_pay_payable_code": (
        "net wages payable",
        "salaries payable",
        "wages payable",
        "payroll clearing",
        "net pay payable",
    ),
}

# Xero "Type" values that count as expense vs liability accounts. Used to
# bias auto-matching when an account name is generic ("CPF" alone could be
# either an expense or a payable).
_EXPENSE_TYPES = {"EXPENSE", "OVERHEADS", "DIRECTCOSTS"}
_LIABILITY_TYPES = {
    "CURRLIAB",
    "LIABILITY",
    "TERMLIAB",
    "PAYG",
    "PAYGLIABILITY",
}


@dataclass(frozen=True)
class XeroAccount:
    """Trimmed view of a Xero chart-of-accounts entry."""

    code: str
    name: str
    type: str = ""
    system_account: str = ""

    @classmethod
    def from_dict(cls, raw: dict) -> "XeroAccount":
        return cls(
            code=str(raw.get("Code") or raw.get("code") or "").strip(),
            name=str(raw.get("Name") or raw.get("name") or "").strip(),
            type=str(raw.get("Type") or raw.get("type") or "").strip().upper(),
            system_account=str(
                raw.get("SystemAccount") or raw.get("system_account") or ""
            ).strip(),
        )


def _normalize(name: str) -> str:
    return " ".join(name.lower().split())


def _bucket_is_liability(bucket: str) -> bool:
    return bucket in {"cpf_payable_code", "net_pay_payable_code"}


def auto_match_accounts(
    accounts: Iterable[dict | XeroAccount],
) -> dict[str, str]:
    """Suggest a code for each of the six buckets.

    Returns a dict keyed by bucket name (e.g. "salary_expense_code") with
    values that are Xero account codes. Buckets without a confident match
    are returned as empty strings — the user fills them in manually.
    """
    parsed: list[XeroAccount] = []
    for raw in accounts:
        if isinstance(raw, XeroAccount):
            parsed.append(raw)
        else:
            parsed.append(XeroAccount.from_dict(raw))

    suggestions: dict[str, str] = {field: "" for field in MAPPING_FIELDS}

    for bucket, patterns in _AUTO_MATCH_PATTERNS.items():
        want_liability = _bucket_is_liability(bucket)
        for pattern in patterns:
            for account in parsed:
                if not account.code or not account.name:
                    continue
                # Skip Xero system accounts (DEBTORS, CREDITORS, BANK,
                # GST, etc.) — they reject ManualJournal posts with a
                # ValidationException. Auto-match must not pick them.
                if account.system_account:
                    continue
                normalized_name = _normalize(account.name)
                if pattern not in normalized_name:
                    continue
                # Type guard: skip an expense account when we want a
                # liability bucket (and vice versa) IF the type is known.
                if account.type:
                    is_liability = account.type in _LIABILITY_TYPES
                    is_expense = account.type in _EXPENSE_TYPES
                    if want_liability and is_expense:
                        continue
                    if not want_liability and is_liability:
                        continue
                suggestions[bucket] = account.code
                break
            if suggestions[bucket]:
                break

    return suggestions


def mapping_is_complete(mapping: dict) -> bool:
    """True iff all six bucket codes are present and non-empty."""
    return all(str(mapping.get(field) or "").strip() for field in MAPPING_FIELDS)


def missing_buckets(mapping: dict) -> list[str]:
    """Bucket field names that are not yet mapped."""
    return [
        field
        for field in MAPPING_FIELDS
        if not str(mapping.get(field) or "").strip()
    ]


def _round2(value: float) -> float:
    return round(float(value), 2)


def build_journal_lines(
    *,
    payroll_run: dict,
    mapping: dict,
    bonus_total: float = 0.0,
    narration: str | None = None,
) -> dict:
    """Construct the journal_data payload for ``post_payroll_journal``.

    The payroll equation we encode (Singapore SME convention):

        Dr  Salary Expense           = total_gross - bonus_total
        Dr  Bonus Expense            = bonus_total
        Dr  Employer CPF Expense     = total_employer_cpf
        Dr  SDL Expense (+ FWL)      = total_sdl + total_fwl
            Cr  CPF & Statutory Payable
                = total_employer_cpf + total_employee_cpf
                  + total_sdl + total_fwl + total_shg
            Cr  Net Pay Payable      = total_net

    Invariant: ``total_gross - total_net == total_employee_cpf + total_shg``
    (employee-borne deductions take gross → net). FWL is bundled into the
    SDL expense line; SHG is bundled into the CPF payable line — both are
    minor for most SG SMEs and folding them keeps the mapping at six
    buckets instead of nine.

    Args:
        payroll_run: dict-shaped PayrollRun row.
        mapping: dict-shaped XeroAccountMapping row (must be complete).
        bonus_total: portion of total_gross paid as bonus, if tracked
            separately. 0.0 means "all gross is salary."
        narration: free-text memo for the Xero journal. Defaults to a
            descriptor including the period.

    Returns:
        Dict with keys ``narration``, ``date``, ``lines`` — exactly the
        shape ``XeroAdapter.post_payroll_journal`` consumes.

    Raises:
        ValueError: if mapping is incomplete or the lines do not balance.
    """
    if not mapping_is_complete(mapping):
        missing = ", ".join(missing_buckets(mapping))
        raise ValueError(
            f"Xero account mapping incomplete. Missing: {missing}"
        )

    gross = float(payroll_run.get("total_gross") or 0.0)
    net = float(payroll_run.get("total_net") or 0.0)
    employer_cpf = float(payroll_run.get("total_employer_cpf") or 0.0)
    employee_cpf = float(payroll_run.get("total_employee_cpf") or 0.0)
    sdl = float(payroll_run.get("total_sdl") or 0.0)
    fwl = float(payroll_run.get("total_fwl") or 0.0)
    shg = float(payroll_run.get("total_shg") or 0.0)
    bonus = max(0.0, float(bonus_total))
    if bonus > gross:
        raise ValueError(
            f"bonus_total ({bonus:.2f}) cannot exceed total_gross "
            f"({gross:.2f})."
        )
    salary = gross - bonus

    period_label = (
        f"{payroll_run.get('period_start', '')} → "
        f"{payroll_run.get('period_end', '')}"
    ).strip(" →")

    pay_date = (
        payroll_run.get("pay_date")
        or payroll_run.get("period_end")
        or ""
    )

    lines: list[dict] = []

    # Debits — expense accounts (positive amounts)
    if salary > 0:
        lines.append(
            {
                "account_code": mapping["salary_expense_code"],
                "description": f"Salaries — {period_label}".strip(" —"),
                "amount": _round2(salary),
                "tax_type": "BASEXCLUDED",
            }
        )
    if bonus > 0:
        lines.append(
            {
                "account_code": mapping["bonus_expense_code"],
                "description": f"Bonus — {period_label}".strip(" —"),
                "amount": _round2(bonus),
                "tax_type": "BASEXCLUDED",
            }
        )
    if employer_cpf > 0:
        lines.append(
            {
                "account_code": mapping["employer_cpf_expense_code"],
                "description": f"Employer CPF — {period_label}".strip(" —"),
                "amount": _round2(employer_cpf),
                "tax_type": "BASEXCLUDED",
            }
        )
    sdl_plus_fwl = sdl + fwl
    if sdl_plus_fwl > 0:
        sdl_label = (
            "SDL + FWL" if (sdl > 0 and fwl > 0)
            else ("FWL" if fwl > 0 else "SDL")
        )
        lines.append(
            {
                "account_code": mapping["sdl_expense_code"],
                "description": f"{sdl_label} — {period_label}".strip(" —"),
                "amount": _round2(sdl_plus_fwl),
                "tax_type": "BASEXCLUDED",
            }
        )

    # Credits — liability accounts (negative amounts)
    cpf_payable = employer_cpf + employee_cpf + sdl + fwl + shg
    if cpf_payable > 0:
        lines.append(
            {
                "account_code": mapping["cpf_payable_code"],
                "description": f"CPF & statutory payable — {period_label}".strip(" —"),
                "amount": -_round2(cpf_payable),
                "tax_type": "BASEXCLUDED",
            }
        )
    if net > 0:
        lines.append(
            {
                "account_code": mapping["net_pay_payable_code"],
                "description": f"Net wages payable — {period_label}".strip(" —"),
                "amount": -_round2(net),
                "tax_type": "BASEXCLUDED",
            }
        )

    if not lines:
        raise ValueError(
            "Payroll run has no monetary totals — nothing to export."
        )

    # Defensive balance check before we hand off to the Xero adapter
    # (which also validates, but a clearer error here helps debugging).
    total = round(sum(line["amount"] for line in lines), 2)
    if abs(total) > 0.01:
        raise ValueError(
            f"Journal does not balance: total={total:.2f}. "
            "Debits must equal credits. Check that net + cpf_payable "
            "equals gross + employer_cpf + sdl."
        )

    journal_narration = narration or (
        f"Payroll {period_label}".strip()
        if period_label
        else "Payroll journal"
    )

    return {
        "narration": journal_narration,
        "date": pay_date,
        # SG GST-registered companies must not have salary journals
        # affect their GST F5. NoTax + per-line BASEXCLUDED keeps the
        # journal entirely out of scope for GST.
        "line_amount_types": "NoTax",
        "lines": lines,
    }
