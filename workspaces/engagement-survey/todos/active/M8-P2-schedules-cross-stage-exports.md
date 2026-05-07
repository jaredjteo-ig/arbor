# M8 — P2: schedules + cross-stage + full cohort builder + exports

**Source plan:** `02-plans/03-frontend-and-phasing.md` §P2, plus
`02-plans/04-product-revision-round3.md` (cross-stage moved P3 → P2).

Ships after P1 is live and stable. P2 now combines the three things
HR needs after the basics work: recurring cadence, the cross-stage
USP demo, and the full cohort filter for power users.

## T80 — `EngagementSurveySchedule` cron tick

- **What:** Cron entry `engagement_pulse_tick.sh` running daily at 02:00 SGT inside `arbor-backend` via docker exec (P16).
- **Tick logic** (unchanged from prior round):
  ```python
  def run_tick(now: datetime, company_id: int | None = None):
      schedules = list_records("EngagementSurveySchedule", {"is_active": True})
      for sched in schedules:
          if not sched["next_launch_at"] or sched["next_launch_at"] > now:
              continue
          last = sched.get("last_launched_survey_id", 0)
          if last:
              prior = read("EngagementSurvey", last)
              if prior and not prior.get("closed_at"):
                  update_schedule(sched["id"], {"last_skipped_at": now})
                  alert_admin(sched, prior)
                  continue
          new_survey_id = launch_from_schedule(sched)
          update_schedule(sched["id"], {
              "last_launched_survey_id": new_survey_id,
              "next_launch_at": next_cadence_tick(now, sched["cadence"]),
          })
  ```
- **Cadence math** (Z22 month-end clamp):
  - weekly: +7d
  - biweekly: +14d
  - monthly: +1mo, anchored to launch date day-of-month, clamped to last day of month if shorter (Jan 31 → Feb 28/29)
  - quarterly: +3mo, same clamp rule
- **Auto-close cron (Z23):** separate daily tick at 02:30 SGT scans `closes_at < now AND closed_at IS NULL`, sets `closed_at = now`, fires close notification to HR via existing `Notification` feed. Idempotent.
- **Acceptance:** schedule with `cadence=monthly`, `next_launch_at=yesterday`, `last_launched=closed` → cron creates new survey, bumps next_launch_at correctly. Schedule anchored Jan 31 → fires Feb 28. Auto-close cron closes overdue surveys.

## T81 — Schedule UI under `/engagement` Schedules tab

- **What:** List, create, pause, resume, archive schedules.
- **Create form:** template + cohort + cadence + open_window_days + anonymity_tier. Pre-populates next_launch_at = now + cadence.
- **Pause / resume:** POST `/schedules/{id}/pause` / `/resume`.
- **Skip indicator:** if `last_skipped_at` non-null, render yellow card with reason ("Last tick skipped — prior survey still open").
- **Acceptance:** admin creates monthly schedule, sees it tick in test mode (manual cron run), pauses it, sees `next_launch_at` freeze.

## T82 — Trust Index pillars template

- **What:** Add to seeded library a `trust_index_pillars` template — 5 sections (Credibility, Respect, Fairness, Pride, Camaraderie), 6 Likert each, 2 free-text closing.
- **Wording:** paraphrased — not Great Place to Work's licensed text. Document IP boundary in methodology metadata.
- **Run past `sg-employment-law-expert`** before shipping (S2 from round-1 redteam).
- **Acceptance:** template appears in library; can be cloned for company-specific edits.

## T83 — Singapore SME quarterly template

- **What:** Add to library `singapore_sme_quarterly` — 8 Likert + 2 free-text with PDPA / FWA / TAFEP / CPF context.
- **Question content** (unchanged from prior round):
  - "How clearly are flexible-work arrangements applied across the team?" (FWA mandate)
  - "How comfortable are you raising fair-employment concerns?" (TAFEP)
  - "How well does your manager explain CPF / payroll?" (CPF + EA)
  - "How fair is the recognition you receive?"
  - "How clear is your career path here?"
  - "How well does the company live up to its stated values?"
  - "How realistic is your workload?"
  - "How likely are you to recommend this company?" (eNPS variant)
  - Free-text: "What's one thing this company does well?"
  - Free-text: "What's one thing the company should change?"
- **Pre-ship review:** S2 — `sg-employment-law-expert` reviews each question for TAFEP / FWA neutrality.
- **Acceptance:** template appears in library with `methodology=custom` and Singapore tag/badge.

## T84 — CSV export

- **Endpoint:** `GET /engagement-surveys/surveys/{id}/export?format=csv`.
- **Output shape:**
  - One row per response. Columns: respondent_label (per anonymity tier), department, submitted_at, then one column per question.
  - Likert as int, text as quoted string, multi-select as semicolon-joined.
  - Suppress columns + rows where anonymity gates trip (per M3 T33).
- **CSV cell sanitiser (Z24):** every cell passes through `sanitizeCsvCell()` — `=`, `+`, `-`, `@`, tab, CR prefixes escaped with `'`.
- **PDPA log (Z16):** every export logs `_log_pdpa_access()` with purpose `engagement_admin_export` for each non-anonymous row.
- **Acceptance:** CSV opens cleanly in Excel + Sheets; no formula injection; suppressed rows clearly marked or omitted; PDPA log row written.

## T85 — PDF export

- **Endpoint:** `GET /engagement-surveys/surveys/{id}/export?format=pdf`.
- **Layout:** cover (survey name + period + response %), aggregate page (per-question distribution as bar chart), eNPS card, theme tally cloud, by-cohort table.
- **Tooling:** reuse existing payroll-payslip PDF generator (ReportLab path) per `mcp-integrations.md`. Wrap in per-survey template.
- **Acceptance:** PDF renders summary; opens in standard viewers; stamped with company branding + PDPA disclaimer.

## T86 — `POST /surveys/{id}/remind` reminder send

- **What:** Re-enqueue an email reminder for each response with `submitted_at IS NULL` AND `is_void = False`. Also sends in-app `Notification` row with `kind="engagement_reminder"`.
- **Cooldown:** rate-limit to 1 reminder per 24 hours per response.
- **Acceptance:** Grace clicks Send Reminder; non-responders get follow-up email + notification; reminder count visible on detail page.

## T87 — Cross-stage correlation service (PULLED FROM P3)

- **What:** New service `src/hr_advisory/services/lifecycle_correlation.py` exposing `correlate_engagement_to_exit(company_id, since_days=90)`.
- **Computation:**
  - For each `EmploymentEvent` with `event_type IN ('RESIGNED', 'TERMINATED', 'RETRENCHED')` in window:
    - Find employee's last `EngagementSurveyResponse` BEFORE event date — keyed by `employee_id` (identified) OR `employee_pseudonym` (pseudonymous).
    - Find any `ExitInterview` for the same employee.
    - Return: `{employee_name OR pseudonym_slug, event_date, last_engagement_score, last_engagement_themes, exit_themes, theme_overlap, days_between_pulse_and_exit, anonymity_tier}`.
- **Endpoint (Z25):** `GET /strategy/lifecycle/engagement-resignation-correlation?window_days=90` returns:
  ```json
  {
    "window_days": 90,
    "resigned_count": 3,
    "low_engagement_resigned_count": 2,
    "pseudonym_join_strategy": "by_pseudonym|by_employee_id",
    "sample_employees": [
      {
        "display_label": "Rajesh Kumar | Engineering, T-15d",
        "exit_themes": ["growth", "manager"],
        "last_engagement_likert_avg": 2.1,
        "days_between_pulse_and_resignation": 47,
        "anonymity_tier": "pseudonymous"
      }
    ],
    "common_overlapping_themes": [{ "theme": "growth", "count": 2 }]
  }
  ```
- **Anonymity respected:** anonymous responses contribute nothing (intentional). Pseudonymous responses join via pseudonym; identified via id.
- **Suppression:** if fewer than 2 correlated rows, return `{message: "Not enough data for cross-stage correlation"}`.
- **Acceptance:** seeded data (M6 T60 + Z27) produces 3 events, 2 with engagement < 3, common theme = "growth".

## T88 — Lifecycle leading-indicator panel (PULLED FROM P3)

- **What:** Add card under Retain stage on `/strategy/lifecycle`. Calls T87.
- **Card content:**
  - Headline: "X of Y who left this quarter showed engagement signals before exit"
  - Body: list bullets, one per event, naming employee (or pseudonym) + last engagement score + theme overlap.
  - "View timeline" link → drill into employee's full lifecycle trace (combined engagement + appraisal + exit interview).
- **Anonymity respect:** pseudonym slug for pseudonymous, name for identified, anonymous excluded.
- **Acceptance:** Grace clicks Lifecycle → sees panel with the killer demo line; click-through opens timeline.

## T89 — Lifecycle activity-feed entries (PULLED FROM P3)

- **What:** Extend `_activity()` in `strategy.py` (round-3 P46 pattern) to emit:
  ```json
  {
    "stage": "reward",
    "kind": "ENGAGEMENT_PULSE",
    "ts": "...",
    "summary": "Engagement pulse submitted",
    "entity_type": "engagement_survey",
    "entity_id": 7
  }
  ```
- Anonymous and pseudonymous: summary = "Engagement pulse submitted" (no name).
- Identified: summary = "Engagement pulse submitted: <name>".
- **Click-through:** existing P46 plumbing routes `engagement_survey` → `/engagement/surveys/{id}`.
- **Acceptance:** activity feed shows entries; click-through works.

## T90 — eNPS hero on lifecycle dashboard (PULLED FROM P3)

- **What:** Add eNPS (latest pulse) tile to lifecycle hero band, next to "Headcount", "Open roles", "Critical roles at risk", "Churn YTD".
- **Data:** average eNPS across most recent closed survey with eNPS question.
- **Acceptance:** tile renders; hover/click → drill into source survey.

## T91 — Full cohort builder UI (DEFERRED FROM P1)

- **What:** Replace the P1 preset+ad-hoc UI with the full filter UI per the original M2 T43 spec.
- **Filter UI controls:**
  - Toggle "All active staff" (overrides others).
  - Multi-select chip: departments.
  - Multi-select: pass_types.
  - Slider/input pair: tenure (min/max days).
  - Multi-select: managers (Employee.reporting_manager_id).
  - "Add specific employees" search-multiselect.
- **Preview panel:** debounced fire to `/cohorts/preview` on every change. Render `matched_count`, sample names, anonymity safety chip, overlap warnings.
- **Migration:** preset-based saved cohorts from P1 stay valid (filter_spec is forward-compatible).
- **Acceptance:** filter changes update preview within 500ms; anonymity-unsafe state shows red chip with explanation.

## T92 — P2 ship

- Same shape as M7 — pre-flight, security review, single bundled commit, server pull + rebuild, live walk verification.
- **Migration check:** new tables/fields for `last_skipped_at`, `EmailDeliveryJob` (already in P1 for exit), check no existing rows break.
- **Cron registration:** add `engagement_pulse_tick.sh` and `engagement_close_tick.sh` to crontab.
- **Walk:** confirm cross-stage panel surfaces the killer demo line on the lifecycle dashboard.
- **Acceptance:** P2 ships green; one tick observed launching a survey end-to-end; CSV + PDF exports validated; cross-stage panel demo'able.

## Dependencies

- T80 ← M3 launch endpoint.
- T81 ← M4 frontend tab pattern.
- T82, T83 ← T16 (templates seed) ← `sg-employment-law-expert`.
- T84, T85 ← M3 aggregator.
- T86 ← T06 email queue.
- T87 ← T03 (pseudonym), T13 (response model), exit_interview model, EmploymentEvent model, Z27 seed.
- T88 ← T87 + lifecycle dashboard router.
- T89 ← T87 + strategy.\_activity().
- T91 ← M2 cohort presets work as foundation.
- T92 ← all of the above.

## Acceptance gate for M8

- Recurring pulses launch automatically and skip on overlap.
- Auto-close cron closes overdue surveys.
- Trust Index + Singapore SME templates ship with legal review on record.
- CSV + PDF exports work and pass anonymity gates.
- Reminder send works with cooldown.
- **Cross-stage correlation runs against seeded data and produces the killer demo line.**
- **Lifecycle leading-indicator panel surfaces it.**
- **eNPS hero tile renders.**
- **Full cohort builder UI replaces preset-only.**
