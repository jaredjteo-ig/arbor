# Recruitment Module — Red Team Fixes

Remaining medium/low severity findings from red team round 1. Organized by effort level.

---

## Quick Fixes (5-10 min each)

### T-RX01: Fix offer currency formatting in email

- **What**: Offer sent email uses hardcoded `$` but default currency is SGD
- **Where**: `src/hr_advisory/api/routers/recruitment.py`, in the `send_offer` endpoint where it builds the email variables
- **Current**: `f"${offer.get('salary', 0):,.2f}/month"`
- **Fix**: Use the actual currency field: `f"{offer.get('currency', 'SGD')} {offer.get('salary', 0):,.2f}/{offer.get('salary_period', 'month')}"`
- **Severity**: LOW

### T-RX02: Enforce PDPA consent re-confirmation on talent pool re-apply

- **What**: When a candidate is re-applied from the talent pool to a new job, the original PDPA consent date is copied without re-confirmation. Consent may have expired.
- **Where**: `src/hr_advisory/api/routers/recruitment.py`, `reapply_candidate` endpoint
- **Fix**: Set `pdpa_consent: False` and `pdpa_consent_date: ""` on the new candidate record, requiring fresh consent. Add a note in the response: `"note": "PDPA consent must be re-confirmed for the new application."`
- **Severity**: MEDIUM (PDPA compliance)

### T-RX03: Enforce required screening questions on public apply

- **What**: Public apply endpoint saves screening responses but doesn't validate that all required questions (`is_required=True`) have been answered, nor checks knockout question responses
- **Where**: `src/hr_advisory/api/routers/recruitment.py`, `public_apply` endpoint, after loading valid question IDs
- **Fix**:
  1. After loading `job_questions`, filter to required ones: `required_ids = {q["id"] for q in job_questions if q.get("is_required")}`
  2. Check all required question IDs have a response: `answered_ids = {r.get("question_id") for r in responses}`
  3. If `required_ids - answered_ids` is non-empty, return 400: "Required screening questions must be answered."
  4. For knockout questions: after saving responses, check if any knockout question got a "false"/"no" response. If so, auto-set a flag or note on the candidate (don't auto-reject — let HR decide)
- **Severity**: MEDIUM

### T-RX04: Remove company name fallback in public jobs endpoint

- **What**: `GET /careers/jobs` falls back from slug to name lookup, enabling company name enumeration
- **Where**: `src/hr_advisory/api/routers/recruitment.py`, `public_list_jobs` endpoint
- **Current**: Tries slug first, then name as fallback
- **Fix**: Remove the name fallback. Only look up by slug. If companies don't have slugs set, add slug generation in company creation (separate todo)
- **Severity**: MEDIUM (information disclosure)

### T-RX05: Fix rate limit timestamp lists to use bounded deque

- **What**: Rate limiter's per-key timestamp lists are unbounded. A burst of requests creates a large list before cleanup runs.
- **Where**: `src/hr_advisory/api/middleware/rate_limit.py`
- **Fix**: Replace `list` with `collections.deque(maxlen=max_requests + 1)` for the timestamp storage. This auto-evicts old entries without needing explicit cleanup.
- **Severity**: LOW

### T-RX06: Mask candidate email in production logs

- **What**: Candidate email addresses (PII under PDPA) are logged in plaintext: `logger.info("Recruitment email sent: template=%s, to=%s", template_name, to)`
- **Where**: `src/hr_advisory/api/routers/recruitment.py`, `_send_recruitment_email` function
- **Fix**: Mask the email in logs: `to_masked = to[:3] + "***" + to[to.index("@"):] if "@" in to else "***"`. Log the masked version.
- **Severity**: LOW

---

## Infrastructure Changes (Need planning)

### T-RX07: Redis-based rate limiting for production

- **What**: Current in-memory rate limiter resets on server restart and doesn't work across multiple workers/containers. Public endpoints are effectively unprotected in production multi-worker deployments.
- **Where**: `src/hr_advisory/api/middleware/rate_limit.py`
- **Details**:
  - Replace `OrderedDict` in-memory store with Redis `INCR` + `EXPIRE` pattern
  - Use `REDIS_URL` from environment (already available — used by the platform)
  - Fallback to in-memory if Redis is unavailable (graceful degradation)
  - Key format: `rate:{action}:{identifier}` with TTL = window_seconds
  - Each rate check: `INCR key`, if result > max_requests raise 429, `EXPIRE key window_seconds` (only on first INCR via `NX` flag)
- **Depends on**: Redis connection available in the backend container (already configured in docker-compose)
- **Severity**: MEDIUM (security — affects public endpoint protection in production)

### T-RX08: Add composite index on Candidate(job_listing_id, email)

- **What**: Duplicate application checking (`add_candidate` and `public_apply`) queries by `job_listing_id + email` without an index. Full table scan per check, exploitable for DoS at scale.
- **Where**: `src/hr_advisory/models/company_user.py`, Candidate class `__dataflow__` indexes
- **Fix**: Add `{"name": "idx_candidate_job_email", "fields": ["job_listing_id", "email"]}` to the Candidate indexes list. Also add a migration script entry for production: `CREATE INDEX IF NOT EXISTS idx_candidate_job_email ON candidates (job_listing_id, email);`
- **Severity**: MEDIUM (performance + DoS prevention)

### T-RX09: Add pagination to list endpoints

- **What**: All list endpoints return ALL matching records with no pagination. Companies with 1000+ candidates will cause high memory usage and slow responses on `list_all_candidates`, `search_talent_pool`, `recruitment_summary`, `list_referrals`.
- **Where**: Multiple endpoints in `src/hr_advisory/api/routers/recruitment.py`
- **Details**:
  - Add `page: int = Query(1, ge=1)` and `page_size: int = Query(50, ge=1, le=200)` params to list endpoints
  - Apply `offset = (page - 1) * page_size` and slice results
  - Return `total`, `page`, `page_size`, `pages` in response alongside records
  - Follow the pattern used in `employees.py` `list_employees` (already has pagination)
  - Priority endpoints to paginate: `list_all_candidates`, `search_talent_pool`, `list_referrals`, `list_offers`
  - Analytics summary can stay as-is (aggregation, not list)
- **Severity**: MEDIUM (performance at scale)

### T-RX10: Add stage transition validation (state machine)

- **What**: `update_candidate` (PATCH) allows setting stage to ANY arbitrary string. No validation against valid stages or allowed transitions. A user can revert a hired candidate to "new" or set stage to nonsense values.
- **Where**: `src/hr_advisory/api/routers/recruitment.py`, `update_candidate` endpoint
- **Details**:
  - Define valid stages: `VALID_STAGES = {"new", "screening", "interview", "offered", "hired", "rejected", "withdrawn"}`
  - Define allowed transitions (forward-only by default, with exceptions):
    ```python
    ALLOWED_TRANSITIONS = {
        "new": {"screening", "interview", "rejected", "withdrawn"},
        "screening": {"interview", "rejected", "withdrawn"},
        "interview": {"offered", "rejected", "withdrawn"},
        "offered": {"hired", "rejected", "withdrawn"},
        # Terminal states — no transitions allowed via PATCH
        "hired": set(),
        "rejected": {"new"},  # Allow re-opening rejected candidates
        "withdrawn": {"new"},  # Allow re-opening withdrawn candidates
    }
    ```
  - In `update_candidate`, if `stage` is in the updates dict:
    1. Validate it's in `VALID_STAGES`
    2. Check current stage allows transition to new stage
    3. If not allowed, return 400 with clear error message
  - The `reject_candidate` and `hire_candidate` dedicated endpoints already handle their own stage changes — this only affects the generic PATCH
- **Severity**: MEDIUM (data integrity)

### T-RX11: Close job cascade — handle active pipeline on job closure

- **What**: Closing a job doesn't reject pending candidates, cancel scheduled interviews, or expire pending offers. Candidates remain in active stages for a closed job indefinitely.
- **Where**: `src/hr_advisory/api/routers/recruitment.py`, `close_job` endpoint
- **Details**:
  - When closing a job, update all candidates in non-terminal stages to "withdrawn" with reason "Job closed"
  - Cancel all scheduled (not completed) interviews for the job's candidates
  - Expire all draft/pending/approved/sent offers for the job
  - Optionally send a notification email to candidates (configurable)
  - Log all changes via `_log_candidate_activity`
  - Add a `cascade` query param (default True) to allow skipping cleanup if HR wants to close without cascading
- **Severity**: MEDIUM (data integrity — orphaned pipeline data)
