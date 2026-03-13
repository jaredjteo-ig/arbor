# T047 — Error Correction

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Error Discovery and Classification**:

- `ErrorSource` enum (USER_REPORT, EXPERT_AUDIT, REGULATORY_CHANGE_LAG, AUTOMATED_DETECTION, INTERNAL_REVIEW)
- `CorrectionStatus` enum (IDENTIFIED, INVESTIGATING, CORRECTED, VERIFIED, NOTIFIED) for full lifecycle tracking

**Data Models**:

- `ErrorRecord` dataclass with full error metadata: severity, affected provisions and domains, discovery info, correction details, verification details, notification timestamp, affected session IDs, and KB update lag days
- `CorrectionNotification` dataclass for affected user notifications (email, in-app, or both)
- `TransparentCorrectionEntry` dataclass for the public correction log with what-was-wrong, what-was-corrected, and KB lag disclosure

**Full Correction Lifecycle**:

- `report_error()` — creates a new error record in IDENTIFIED status
- `start_investigation()` — moves error to INVESTIGATING status
- `apply_correction()` — records the correction description and corrector, moves to CORRECTED status
- `verify_correction()` — marks as VERIFIED, records verifier, and automatically adds a `TransparentCorrectionEntry` to the public correction log with KB lag disclosure

**Affected Session Identification**:

- `identify_affected_sessions()` — identifies sessions that received advice based on incorrect provisions (in production, queries the trust store via DataFlow by provision IDs)

**Transparency**:

- `get_correction_log()` — returns public correction log, most recent first
- `get_error_records()` — returns error records with optional status filter, sorted by discovery date

## Files

- `src/hr_advisory/trust/error_correction.py` — error correction and transparency module
