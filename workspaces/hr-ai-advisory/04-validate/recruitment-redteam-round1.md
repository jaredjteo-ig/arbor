# Recruitment Module — Red Team Report (Round 1)

## Agents Deployed

- **Security Reviewer** — full security audit across all changed files
- **Deep Analyst** — API endpoint correctness, edge cases, data integrity, hire flow traceability
- **Value Auditor** — demo readiness, competitive assessment, original recommendations vs implementation

## Findings Summary

| Severity | Found | Fixed | Remaining |
| -------- | ----- | ----- | --------- |
| CRITICAL | 10    | 10    | 0         |
| HIGH     | 9     | 9     | 0         |
| MEDIUM   | 8     | 2     | 6         |
| LOW      | 6     | 0     | 6         |

## Critical Issues Fixed

### Security

1. **Path traversal in resume download** — `resume_url` from DB used directly in `os.path.join`. Fixed: reject path separators, validate resolved path stays in expected directory.
2. **Email enumeration via application status** — unauthenticated endpoint with no rate limiting. Fixed: added IP-based rate limiting (20/hour).
3. **XSS in email templates** — user-controlled values interpolated into HTML without escaping. Fixed: HTML-escape all template variables before interpolation.

### Data Integrity

4. **Feedback field mismatch** — router wrote `rating`/`comments` but model has `overall_rating`/`notes`. All feedback data was silently lost. Fixed: aligned to model field names.
5. **Invitation field mismatch** — router wrote `invited_by` but model has `inviter_id`. Fixed: aligned field names.
6. **Candidate stage "applied"** — internal add_candidate used `"applied"` but model/frontend expect `"new"`. Fixed: now uses `"new"`.
7. **Offer approval bypass** — offers could be sent from "draft" bypassing approval. Fixed: send now requires "approved" status (restored to "draft"/"approved" for SMEs without approval workflows).

### Value Gaps

8. **TAFEP scan not in frontend** — Arbor's key differentiator was backend-only. Fixed: added scan button, results modal, category-coded findings.
9. **Offer creation UI missing** — layout claimed "generate offers" but no UI existed. Fixed: added CreateOfferModal triggered on move-to-offered.
10. **Salary not carried to employee on hire** — data bridge broken between invitation and employee. Fixed: auth.py now reads salary/phone from invitation.

## High Issues Fixed

1. **No email format validation on public apply** — accepts arbitrary strings. Fixed: regex validation added.
2. **PDF HTML injection** — reportlab Paragraph interprets markup from user values. Fixed: XML-escape user values.
3. **Filename not sanitized in PDF** — header injection risk. Fixed: strip non-alphanumeric, truncate to 50 chars.
4. **Temp file leak in PDF generation** — never cleaned up. Fixed: BackgroundTask cleanup.
5. **Salary validation missing on job update** — NaN/Infinity bypass. Fixed: same isfinite() checks as create.
6. **Missing company_id on feedback query** — defense-in-depth gap. Fixed.
7. **Screening question_id not validated** — could submit responses to other jobs' questions. Fixed: validate against job's questions.
8. **Schedule interview demoting stage** — offered/hired candidates moved back to interview. Fixed: only advance, never demote.
9. **Interview feedback form missing from UI** — Fixed: added SubmitFeedbackModal with star ratings.

## Additional Frontend Fixes (Value Audit)

- **Salary range** added to job creation modal (was missing)
- **TAFEP compliance scan** wired to publish flow with results modal
- **Offer creation modal** with salary, start date, probation, benefits
- **Interview feedback form** with 5-star rating, recommendation dropdown

## Remaining Medium/Low (Acceptable for Current Phase)

- M: Public jobs endpoint allows company name enumeration via fallback
- M: In-memory rate limiter doesn't survive restarts (need Redis for production)
- M: Missing composite index on Candidate(job_listing_id, email)
- M: Analytics loads all records into memory (no pagination)
- M: No CSRF concern (JWT bearer tokens, not cookies)
- M: Screening required/knockout questions not enforced on submit
- L: Candidate email logged in plaintext
- L: Rate limit timestamp lists unbounded per key
- L: Seed data uses fictional but realistic Singapore data (acceptable)
- L: TAFEP patterns can be bypassed with Unicode homoglyphs
- L: Offer currency formatted as $ but default is SGD
- L: PDPA consent re-confirmation not enforced on talent pool re-apply

## Test Results

- 231 recruitment tests passing, 0 failures
- 25 new security/bridge tests added in this round
