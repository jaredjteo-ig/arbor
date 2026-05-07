"""Backfill: seed engagement-survey demo data for the killer flow (M6 T60).

Round-3 expansion: 6 prior closed pulses + 1 open pulse + 1 accepted
EngagementAction with linked Goal. Designed so:

- Trend hero shows 6 pulses with Engineering descending (3.8 → 3.2).
- Action panel "Already accepted" section shows the L&D pilot action.
- Loop-closing card on Lily's view shows "growth → L&D pilot".
- Cross-stage panel (P2) finds the 3 RESIGNED employees with low Likert
  scores tied to the growth theme.

Idempotent — skip when prior demo seed rows already exist.

Usage:
    python scripts/backfill_demo_engagement_surveys.py
    ARBOR_DEMO_COMPANY_ID=1 python scripts/backfill_demo_engagement_surveys.py
"""

from __future__ import annotations

import json
import logging
import os
import random
import secrets
import sys
from datetime import datetime, timedelta, timezone
from hashlib import sha256

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_COMPANY_ID = int(os.environ.get("ARBOR_DEMO_COMPANY_ID", "1"))
RNG_SEED = 20260507  # fixed for reproducible demo data


def _get_database_url() -> str:
    try:
        from dotenv import load_dotenv

        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        load_dotenv(env_path)
    except ImportError:
        pass
    url = os.environ.get("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL is not set.")
        sys.exit(1)
    return url


# ──────────────────────────────────────────────────────────────────────
# Templates (subset of what the lazy-seeder ships — used here for the
# inserted snapshot per survey)
# ──────────────────────────────────────────────────────────────────────


GALLUP_Q12_SECTIONS = [
    {
        "title": "Basic needs",
        "questions": [
            {"id": "q1", "text": "I know what is expected of me at work.", "type": "likert5", "is_required": True},
            {"id": "q2", "text": "I have the materials I need to do my work well.", "type": "likert5", "is_required": True},
        ],
    },
    {
        "title": "Management support",
        "questions": [
            {"id": "q3", "text": "I have the opportunity to do what I do best every day.", "type": "likert5", "is_required": True},
            {"id": "q4", "text": "In the last 6 months, someone has talked to me about my growth.", "type": "likert5", "is_required": True},
            {"id": "q5", "text": "My manager seems to care about me as a person.", "type": "likert5", "is_required": True},
            {"id": "q6", "text": "There is someone at work who encourages my development.", "type": "likert5", "is_required": True},
        ],
    },
    {
        "title": "Teamwork",
        "questions": [
            {"id": "q7", "text": "At work, my opinions seem to count.", "type": "likert5", "is_required": True},
            {"id": "q8", "text": "The mission of the company makes my job feel important.", "type": "likert5", "is_required": True},
            {"id": "q9", "text": "My coworkers are committed to doing quality work.", "type": "likert5", "is_required": True},
            {"id": "q10", "text": "I have a best friend at work.", "type": "likert5", "is_required": True},
        ],
    },
    {
        "title": "Growth",
        "questions": [
            {"id": "q11", "text": "I have had opportunities at work to learn and grow.", "type": "likert5", "is_required": True},
            {"id": "q12", "text": "Someone at work talks to me about my progress.", "type": "likert5", "is_required": True},
        ],
    },
]


def _hmac_pseudonym(secret_hex: str, employee_id: int, survey_id: int) -> str:
    """Mirror services/engagement_pseudonym.compute_pseudonym for seeding."""
    import hashlib
    import hmac

    secret_bytes = bytes.fromhex(secret_hex)
    msg = f"{employee_id}|{survey_id}".encode("utf-8")
    return hmac.new(secret_bytes, msg, hashlib.sha256).hexdigest()


def _build_response_attrs(emp_row: dict) -> str:
    """Mirror routers/engagement_surveys._build_response_cohort_attributes."""
    department = emp_row.get("department", "") or ""
    pass_type = emp_row.get("pass_type", "") or ""
    start_date = emp_row.get("start_date") or ""
    today = datetime.now(timezone.utc).date()
    tenure_band = "unknown"
    if start_date:
        try:
            sd = datetime.fromisoformat(str(start_date).split("T")[0]).date()
            days = (today - sd).days
            tenure_band = "0-1y" if days < 365 else "1-3y" if days < 365 * 3 else "3+y"
        except ValueError:
            pass
    manager_id = emp_row.get("reporting_manager_id") or 0
    manager_hash = (
        sha256(f"mgr:{int(manager_id)}".encode("utf-8")).hexdigest()[:16]
        if manager_id
        else ""
    )
    return json.dumps(
        {
            "department": department,
            "pass_type": pass_type,
            "tenure_band": tenure_band,
            "manager_id_hashed": manager_hash,
        },
        sort_keys=True,
    )


def _consent_version() -> str:
    return "v1:" + sha256(b"engagement-default-notice").hexdigest()[:8]


def run() -> None:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        logger.error("psycopg2 required.")
        sys.exit(1)

    rng = random.Random(RNG_SEED)
    conn = psycopg2.connect(_get_database_url())
    conn.autocommit = False
    company_id = DEFAULT_COMPANY_ID
    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            # ─── Schema sanity checks ─────────────────────────────────
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'engagement_surveys'"
            )
            if not cur.fetchone():
                logger.warning("engagement_surveys table not present — run migrations first.")
                return

            # ─── Idempotency check ────────────────────────────────────
            cur.execute(
                "SELECT COUNT(*) AS n FROM engagement_surveys WHERE company_id = %s",
                (company_id,),
            )
            existing = cur.fetchone()["n"]
            if existing >= 6:
                logger.info(
                    "Engagement demo data already seeded for company %s "
                    "(found %s surveys); skipping.",
                    company_id,
                    existing,
                )
                return

            # ─── Resolve employees ────────────────────────────────────
            cur.execute(
                "SELECT id, user_id, department, pass_type, start_date, reporting_manager_id, "
                " is_active "
                "FROM employees WHERE company_id = %s ORDER BY id",
                (company_id,),
            )
            employees = [dict(r) for r in cur.fetchall()]
            if len(employees) < 5:
                logger.warning(
                    "Need ≥5 employees for the engagement demo seed; found %s. "
                    "Run scripts/seed_demo_data.py first.",
                    len(employees),
                )
                return

            active_employees = [e for e in employees if e["is_active"]]
            if len(active_employees) < 5:
                logger.warning(
                    "Need ≥5 active employees; found %s.",
                    len(active_employees),
                )
                return

            # ─── Pseudonym secret ─────────────────────────────────────
            cur.execute(
                "SELECT engagement_secret_v1 FROM companies WHERE id = %s",
                (company_id,),
            )
            row = cur.fetchone()
            stored_v1 = row.get("engagement_secret_v1") if row else ""

            # B4 (red-team): the secret MUST round-trip through
            # encrypt_field/decrypt_field. The earlier version stored
            # hex-plaintext and only "worked" because decrypt_field
            # silently returned bad ciphertext as-is. If anyone fixes
            # decrypt_field to fail-closed, all seeded pseudonyms break.
            from hr_advisory.security.encryption import (
                decrypt_field,
                encrypt_field,
            )

            if stored_v1:
                # Try to decrypt. If it fails (e.g. legacy plaintext from
                # an earlier broken seed), regenerate.
                try:
                    secret_v1 = decrypt_field(stored_v1)
                    # Sanity-check it's the expected hex shape.
                    if (
                        not isinstance(secret_v1, str)
                        or len(secret_v1) != 64
                        or any(c not in "0123456789abcdef" for c in secret_v1)
                    ):
                        raise ValueError("Decrypted secret is not 64-char hex.")
                except Exception:
                    logger.warning(
                        "Stored engagement_secret_v1 is not decryptable "
                        "(likely legacy plaintext); regenerating."
                    )
                    secret_v1 = ""
            else:
                secret_v1 = ""

            if not secret_v1:
                secret_v1 = secrets.token_hex(32)
                encrypted = encrypt_field(secret_v1)
                cur.execute(
                    "UPDATE companies SET engagement_secret_v1 = %s, "
                    "engagement_secret_active_version = 1 WHERE id = %s",
                    (encrypted, company_id),
                )
                logger.info(
                    "Generated + encrypted engagement_secret_v1 for "
                    "company %s.",
                    company_id,
                )

            # ─── Templates: ensure shipped library exists ─────────────
            cur.execute(
                "SELECT id, name, methodology FROM engagement_survey_templates "
                "WHERE company_id = %s AND is_archived = false",
                (company_id,),
            )
            existing_templates = [dict(r) for r in cur.fetchall()]
            template_by_method = {t["methodology"]: t for t in existing_templates}
            q12 = template_by_method.get("gallup_q12")
            if not q12:
                cur.execute(
                    "INSERT INTO engagement_survey_templates "
                    "(company_id, name, description, methodology, sections, "
                    " is_archived, created_by, created_at, updated_at) "
                    "VALUES (%s, %s, %s, 'gallup_q12', %s, false, 0, %s, %s) "
                    "RETURNING id, name, methodology",
                    (
                        company_id,
                        "Gallup Q12 (paraphrased)",
                        "Quarterly Q12 — research-backed engagement statements.",
                        json.dumps(GALLUP_Q12_SECTIONS),
                        now,
                        now,
                    ),
                )
                q12 = dict(cur.fetchone())
                logger.info("Seeded gallup_q12 template (id=%s).", q12["id"])

            # ─── 6 prior closed pulses (M6 T60) ───────────────────────
            #
            # Engineering trends 3.8 → 3.7 → 3.5 → 3.3 → 3.2 → 3.2.
            # Sales stays around 4.4. Other departments around 3.7-4.0.
            # All pseudonymous tier so the demo shows the trend without
            # revealing identities.
            consent_version = _consent_version()
            sections_snapshot = json.dumps(GALLUP_Q12_SECTIONS)
            engineering_trend = [3.8, 3.7, 3.5, 3.3, 3.2, 3.2]
            seeded_survey_ids: list[int] = []

            # 3 employees who resigned — give them low growth scores
            # consistently across pulses, matching the exit-interview seed
            # where 2 cited "growth".
            cur.execute(
                "SELECT employee_id FROM employment_events "
                "WHERE company_id = %s AND event_type IN "
                "('RESIGNED', 'resigned', 'TERMINATED', 'terminated') "
                "ORDER BY id LIMIT 3",
                (company_id,),
            )
            resigned_ids = [r["employee_id"] for r in cur.fetchall()]

            for i, eng_target in enumerate(engineering_trend):
                # Spread the 6 pulses across last ~7 months, one per ~30 days.
                offset_days = (5 - i) * 30 + 25
                launched = now - timedelta(days=offset_days + 14)
                closes = now - timedelta(days=offset_days)
                closed = closes  # closed exactly at closes_at for demo

                pulse_name = f"H{(2026 if i >= 4 else 2025) - 0} Pulse — {launched.strftime('%b %Y')}"
                cur.execute(
                    "INSERT INTO engagement_surveys "
                    "(company_id, template_id, template_sections_snapshot, "
                    " cohort_id, cohort_filter_spec, name, anonymity_tier, "
                    " schedule_id, launched_at, closes_at, closed_at, "
                    " target_count, voided_count, consent_notice_version, "
                    " email_delivery_status, is_archived, created_by, "
                    " created_at, updated_at) "
                    "VALUES (%s, %s, %s, 0, %s, %s, 'pseudonymous', 0, %s, %s, %s, "
                    " %s, 0, %s, 'complete', false, 0, %s, %s) "
                    "RETURNING id",
                    (
                        company_id,
                        q12["id"],
                        sections_snapshot,
                        json.dumps({"all_active": True}),
                        pulse_name,
                        launched,
                        closes,
                        closed,
                        len(active_employees),
                        consent_version,
                        launched,
                        launched,
                    ),
                )
                survey_id = cur.fetchone()["id"]
                seeded_survey_ids.append(survey_id)

                # Insert one response per active employee, with score
                # weighted by department to produce the trend.
                for emp in active_employees:
                    dept = (emp.get("department") or "").lower()
                    is_resigner = emp["id"] in resigned_ids
                    if dept.startswith("eng"):
                        target_avg = eng_target
                        # The resigners scored extra-low on growth questions
                        # (q4, q11, q12).
                        growth_avg = (
                            max(1.5, eng_target - 1.5)
                            if is_resigner
                            else max(1.0, eng_target - 0.4)
                        )
                    elif dept.startswith("sales"):
                        target_avg = 4.4
                        growth_avg = 4.2
                    else:
                        target_avg = 3.8
                        growth_avg = 3.7

                    likert_scores: dict[str, int] = {}
                    growth_qs = {"q4", "q11", "q12"}
                    for s in GALLUP_Q12_SECTIONS:
                        for q in s["questions"]:
                            qid = q["id"]
                            base = growth_avg if qid in growth_qs else target_avg
                            v = max(1, min(5, int(round(rng.gauss(base, 0.5)))))
                            likert_scores[qid] = v

                    submitted_at = closes - timedelta(
                        hours=rng.randint(2, 13 * 24)
                    )
                    pseudo = _hmac_pseudonym(secret_v1, emp["id"], survey_id)
                    payload = {qid: v for qid, v in likert_scores.items()}
                    themes_for_response: list[str] = []
                    if is_resigner or growth_avg < 3:
                        themes_for_response.append("growth")
                    if dept.startswith("eng") and target_avg < 3.5:
                        themes_for_response.append("manager")
                    cohort_attrs = _build_response_attrs(emp)

                    cur.execute(
                        "INSERT INTO engagement_survey_responses "
                        "(company_id, survey_id, employee_id, "
                        " employee_pseudonym, pseudonym_version, "
                        " survey_payload, likert_scores, themes, enps_score, "
                        " response_cohort_attributes, idempotency_key, "
                        " submitted_at, triggered_at, consent_notice_version, "
                        " is_void, is_archived, created_at, updated_at) "
                        "VALUES (%s, %s, 0, %s, 1, %s, %s, %s, NULL, %s, '', "
                        " %s, %s, %s, false, false, %s, %s)",
                        (
                            company_id,
                            survey_id,
                            pseudo,
                            json.dumps(payload),
                            json.dumps(likert_scores),
                            json.dumps(sorted(set(themes_for_response))),
                            cohort_attrs,
                            submitted_at,
                            launched,
                            consent_version,
                            launched,
                            submitted_at,
                        ),
                    )

            logger.info(
                "Seeded %s prior closed pulses with response distributions.",
                len(seeded_survey_ids),
            )

            # ─── Open pulse — Lily hasn't yet responded ──────────────
            open_launched = now - timedelta(days=7)
            open_closes = now + timedelta(days=7)
            open_name = f"H1 2026 Pulse — {open_launched.strftime('%b %Y')}"
            cur.execute(
                "INSERT INTO engagement_surveys "
                "(company_id, template_id, template_sections_snapshot, "
                " cohort_id, cohort_filter_spec, name, anonymity_tier, "
                " schedule_id, launched_at, closes_at, closed_at, "
                " target_count, voided_count, consent_notice_version, "
                " email_delivery_status, is_archived, created_by, "
                " created_at, updated_at) "
                "VALUES (%s, %s, %s, 0, %s, %s, 'pseudonymous', 0, %s, %s, NULL, "
                " %s, 0, %s, 'pending', false, 0, %s, %s) "
                "RETURNING id",
                (
                    company_id,
                    q12["id"],
                    sections_snapshot,
                    json.dumps({"all_active": True}),
                    open_name,
                    open_launched,
                    open_closes,
                    len(active_employees),
                    consent_version,
                    open_launched,
                    open_launched,
                ),
            )
            open_survey_id = cur.fetchone()["id"]

            # Find Lily by name (or fall back to first active employee)
            cur.execute(
                "SELECT e.id, e.user_id FROM employees e "
                "JOIN users u ON u.id = e.user_id "
                "WHERE e.company_id = %s AND u.name ILIKE %s LIMIT 1",
                (company_id, "%lily%"),
            )
            lily_row = cur.fetchone()
            lily_id = lily_row["id"] if lily_row else active_employees[0]["id"]

            for emp in active_employees:
                if emp["id"] == lily_id:
                    # Pending — created but NOT submitted.
                    cur.execute(
                        "INSERT INTO engagement_survey_responses "
                        "(company_id, survey_id, employee_id, "
                        " employee_pseudonym, pseudonym_version, "
                        " survey_payload, likert_scores, themes, enps_score, "
                        " response_cohort_attributes, idempotency_key, "
                        " submitted_at, triggered_at, consent_notice_version, "
                        " is_void, is_archived, created_at, updated_at) "
                        "VALUES (%s, %s, %s, '', 0, '', '', '', NULL, '', '', "
                        " NULL, %s, %s, false, false, %s, %s)",
                        (
                            company_id,
                            open_survey_id,
                            emp["id"],
                            open_launched,
                            consent_version,
                            open_launched,
                            open_launched,
                        ),
                    )
                    continue
                # Other employees submitted (around 22 of 28 → ~78%)
                if rng.random() > 0.78:
                    # Skip — they haven't submitted yet.
                    cur.execute(
                        "INSERT INTO engagement_survey_responses "
                        "(company_id, survey_id, employee_id, "
                        " employee_pseudonym, pseudonym_version, "
                        " survey_payload, likert_scores, themes, enps_score, "
                        " response_cohort_attributes, idempotency_key, "
                        " submitted_at, triggered_at, consent_notice_version, "
                        " is_void, is_archived, created_at, updated_at) "
                        "VALUES (%s, %s, %s, '', 0, '', '', '', NULL, '', '', "
                        " NULL, %s, %s, false, false, %s, %s)",
                        (
                            company_id,
                            open_survey_id,
                            emp["id"],
                            open_launched,
                            consent_version,
                            open_launched,
                            open_launched,
                        ),
                    )
                    continue

                dept = (emp.get("department") or "").lower()
                target_avg = (
                    3.2 if dept.startswith("eng") else 4.4 if dept.startswith("sales") else 3.8
                )
                likert_scores = {}
                for s in GALLUP_Q12_SECTIONS:
                    for q in s["questions"]:
                        v = max(1, min(5, int(round(rng.gauss(target_avg, 0.6)))))
                        likert_scores[q["id"]] = v
                submitted_at = open_launched + timedelta(
                    hours=rng.randint(1, 6 * 24)
                )
                pseudo = _hmac_pseudonym(secret_v1, emp["id"], open_survey_id)
                payload = {qid: v for qid, v in likert_scores.items()}
                cohort_attrs = _build_response_attrs(emp)
                cur.execute(
                    "INSERT INTO engagement_survey_responses "
                    "(company_id, survey_id, employee_id, "
                    " employee_pseudonym, pseudonym_version, "
                    " survey_payload, likert_scores, themes, enps_score, "
                    " response_cohort_attributes, idempotency_key, "
                    " submitted_at, triggered_at, consent_notice_version, "
                    " is_void, is_archived, created_at, updated_at) "
                    "VALUES (%s, %s, 0, %s, 1, %s, %s, %s, NULL, %s, '', "
                    " %s, %s, %s, false, false, %s, %s)",
                    (
                        company_id,
                        open_survey_id,
                        pseudo,
                        json.dumps(payload),
                        json.dumps(likert_scores),
                        json.dumps([]),
                        cohort_attrs,
                        submitted_at,
                        open_launched,
                        consent_version,
                        open_launched,
                        submitted_at,
                    ),
                )
            logger.info("Seeded open pulse (id=%s) — Lily pending.", open_survey_id)

            # ─── Accepted action + linked Goal (M6 T60 round-3) ──────
            # Tied to the most recent CLOSED Engineering-low pulse.
            most_recent_closed = seeded_survey_ids[-1]
            # Pick HR's first user as the action author / goal owner.
            cur.execute(
                "SELECT id, user_id FROM employees WHERE company_id = %s "
                "AND department ILIKE 'hr%%' ORDER BY id LIMIT 1",
                (company_id,),
            )
            hr_row = cur.fetchone()
            if not hr_row:
                cur.execute(
                    "SELECT id, user_id FROM employees WHERE company_id = %s "
                    "ORDER BY id LIMIT 1",
                    (company_id,),
                )
                hr_row = cur.fetchone()
            hr_employee_id = hr_row["id"]
            hr_user_id = hr_row["user_id"]

            cur.execute(
                "SELECT 1 FROM engagement_actions WHERE company_id = %s "
                "AND survey_id = %s",
                (company_id, most_recent_closed),
            )
            if not cur.fetchone():
                # Create the linked Goal first.
                goal_title = "Q2 Engineering L&D — every IC has approved budget by end of Q2"
                cur.execute(
                    "INSERT INTO goals "
                    "(company_id, employee_id, manager_id, period_id, "
                    " title, description, metric, target_value, "
                    " start_date, due_date, status, progress_pct, "
                    " is_archived, created_at, updated_at) "
                    "VALUES (%s, %s, 0, 0, %s, %s, '', '', '', '', "
                    " 'active', 25, false, %s, %s) "
                    "RETURNING id",
                    (
                        company_id,
                        hr_employee_id,
                        goal_title,
                        "Auto-created from engagement pulse — Engineering "
                        "scored 2.1 on growth question. L&D pilot is the "
                        "agreed action.",
                        now,
                        now,
                    ),
                )
                linked_goal_id = cur.fetchone()["id"]

                cur.execute(
                    "INSERT INTO engagement_actions "
                    "(company_id, survey_id, cohort_label, finding_summary, "
                    " suggested_action_text, status, linked_goal_id, "
                    " next_pulse_question, next_pulse_survey_id, "
                    " resolved_at, resolved_score_delta, created_by, "
                    " created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, 'accepted', %s, %s, 0, "
                    " NULL, NULL, %s, %s, %s)",
                    (
                        company_id,
                        most_recent_closed,
                        "Engineering",
                        "Engineering scored 2.1 / 5 on growth (Q4, Q11, Q12). "
                        "Of the 3 who resigned this quarter, 2 cited growth.",
                        "Launch L&D pilot with a per-head learning budget for the cohort",
                        linked_goal_id,
                        "I have had opportunities at work to learn and grow.",
                        hr_user_id,
                        now - timedelta(days=5),
                        now - timedelta(days=5),
                    ),
                )
                logger.info(
                    "Seeded EngagementAction + linked Goal #%s.",
                    linked_goal_id,
                )

            conn.commit()
            logger.info(
                "Engagement-survey demo seed complete for company %s. "
                "Trend hero, action panel, and loop-closing card now have data.",
                company_id,
            )

    except Exception as exc:
        conn.rollback()
        logger.error("Seed failed: %s", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
