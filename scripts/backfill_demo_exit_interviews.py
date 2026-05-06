"""Backfill: seed two completed exit interviews — one anonymous, one named.

Phase 2 P2-EX-4 (obayashi).

  - Anonymous, negative sentiment, manager-related themes.
  - Named, positive sentiment, retirement reason.

Both are pre-submitted (i.e. survey_payload + themes filled, submitted_at
set) so the admin Themes view has data on demo day.

Idempotent.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_COMPANY_ID = int(os.environ.get("ARBOR_DEMO_COMPANY_ID", "1"))


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


def run() -> None:
    try:
        import psycopg2
    except ImportError:
        logger.error("psycopg2 required.")
        sys.exit(1)

    conn = psycopg2.connect(_get_database_url())
    conn.autocommit = False
    company_id = DEFAULT_COMPANY_ID
    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'exit_interviews'"
            )
            if not cur.fetchone():
                logger.warning("exit_interviews table not present.")
                return

            cur.execute(
                "SELECT 1 FROM exit_interviews WHERE company_id = %s LIMIT 1",
                (company_id,),
            )
            interviews_already_seeded = bool(cur.fetchone())

            cur.execute(
                "SELECT id FROM employees WHERE company_id = %s "
                "AND is_active = true ORDER BY id LIMIT 2",
                (company_id,),
            )
            employees = [r[0] for r in cur.fetchall()]
            if len(employees) < 2:
                logger.warning("Need ≥2 active employees in company %s.", company_id)
                return

            seeds = [
                {
                    "employee_id": employees[0],
                    "is_anonymous": True,
                    "submitted_offset_days": 12,
                    "payload": {
                        "q1_overall": 2,
                        "q2_fairness": 2,
                        "q3_reasons": ["manager", "workload", "growth"],
                        "q4_what_worked": "Camaraderie with my team.",
                        "q5_what_to_change": "Direct manager wasn't supportive; workload was unsustainable for months.",
                        "q6_recommend_why": "No — depends on the manager you get.",
                    },
                    "themes": ["growth", "manager", "workload"],
                },
                {
                    "employee_id": employees[1],
                    "is_anonymous": False,
                    "submitted_offset_days": 5,
                    "payload": {
                        "q1_overall": 5,
                        "q2_fairness": 5,
                        "q3_reasons": ["retirement"],
                        "q4_what_worked": "Strong ownership of the work; great peers.",
                        "q5_what_to_change": "Nothing major — happy with how it ended.",
                        "q6_recommend_why": "Yes — supportive manager and clear expectations.",
                    },
                    "themes": ["retirement"],
                },
            ]
            if not interviews_already_seeded:
                for s in seeds:
                    triggered = now - timedelta(days=s["submitted_offset_days"] + 7)
                    submitted = now - timedelta(days=s["submitted_offset_days"])
                    cur.execute(
                        "INSERT INTO exit_interviews "
                        "(company_id, employee_id, triggered_at, "
                        " triggered_by_event_id, survey_payload, themes, "
                        " is_anonymous, submitted_at, is_archived, "
                        " created_at, updated_at) "
                        "VALUES (%s,%s,%s,0,%s,%s,%s,%s,false,%s,%s)",
                        (
                            company_id,
                            s["employee_id"],
                            triggered,
                            json.dumps(s["payload"]),
                            json.dumps(s["themes"]),
                            s["is_anonymous"],
                            submitted,
                            triggered,
                            submitted,
                        ),
                    )
                logger.info("Seeded 2 exit interviews (one anonymous, one named).")
            else:
                logger.info(
                    "Exit interviews already seeded for company %s — "
                    "skipping interview rows but still checking the "
                    "EmploymentEvent backfill below.",
                    company_id,
                )

            # Round-2 redteam H4: seed matching EmploymentEvent rows so the
            # Lifecycle dashboard's S8 panel shows non-zero churn YTD instead
            # of contradicting the visible exit interviews. Use RESIGNED for
            # the negative-sentiment leaver and RETIRED for the positive one.
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'employment_events'"
            )
            if cur.fetchone():
                cur.execute(
                    "SELECT COUNT(*) FROM employment_events "
                    "WHERE company_id = %s AND event_type IN ('RESIGNED', 'RETIRED', 'TERMINATED', 'RETRENCHED')",
                    (company_id,),
                )
                (existing_exits,) = cur.fetchone()
                if existing_exits == 0:
                    for s in seeds:
                        triggered = now - timedelta(
                            days=s["submitted_offset_days"] + 7
                        )
                        event_type = (
                            "RETIRED"
                            if "retirement" in s["themes"]
                            else "RESIGNED"
                        )
                        cur.execute(
                            "INSERT INTO employment_events "
                            "(company_id, employee_id, event_type, "
                            " event_date, effective_date, description, "
                            " old_value, new_value, approved_by, notes, "
                            " created_at, updated_at) "
                            "VALUES (%s,%s,%s,%s,%s,%s,'{}','{}',0,'',%s,%s)",
                            (
                                company_id,
                                s["employee_id"],
                                event_type,
                                triggered.date().isoformat(),
                                triggered.date().isoformat(),
                                f"Demo exit ({event_type.lower()}) seeded for lifecycle dashboard.",
                                triggered,
                                triggered,
                            ),
                        )
                    logger.info("Seeded 2 EmploymentEvent exits (RESIGNED + RETIRED).")

            # R2-M finding: hero churn_yoy_delta read 0.0 because seed had
            # no last-year exits either. Seed 1 RESIGNED 14 months ago to
            # give the YoY delta a real number to display.
            cur.execute(
                "SELECT COUNT(*) FROM employment_events "
                "WHERE company_id = %s AND event_type IN "
                "('RESIGNED', 'RETIRED', 'TERMINATED', 'RETRENCHED', "
                " 'resigned', 'retired', 'terminated', 'retrenched') "
                "AND created_at < %s",
                (company_id, now.replace(year=now.year - 1, month=12, day=31)),
            )
            (last_year_exits,) = cur.fetchone()
            if last_year_exits == 0:
                cur.execute(
                    "SELECT id FROM employees WHERE company_id = %s "
                    "AND is_active = false ORDER BY id DESC LIMIT 1",
                    (company_id,),
                )
                inactive_row = cur.fetchone()
                # Fall back to a high-id employee if none inactive — the demo
                # cares about the count, not who left.
                if not inactive_row:
                    cur.execute(
                        "SELECT id FROM employees WHERE company_id = %s "
                        "ORDER BY id DESC LIMIT 1 OFFSET 4",
                        (company_id,),
                    )
                    inactive_row = cur.fetchone()
                if inactive_row:
                    last_year_dt = now - timedelta(days=420)  # ~14 months ago
                    cur.execute(
                        "INSERT INTO employment_events "
                        "(company_id, employee_id, event_type, "
                        " event_date, effective_date, description, "
                        " old_value, new_value, approved_by, notes, "
                        " created_at, updated_at) "
                        "VALUES (%s,%s,'RESIGNED',%s,%s,%s,'{}','{}',0,'',%s,%s)",
                        (
                            company_id,
                            inactive_row[0],
                            last_year_dt.date().isoformat(),
                            last_year_dt.date().isoformat(),
                            "Demo exit seeded for last-year churn baseline.",
                            last_year_dt,
                            last_year_dt,
                        ),
                    )
                    logger.info(
                        "Seeded 1 last-year RESIGNED event for YoY churn delta."
                    )
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
