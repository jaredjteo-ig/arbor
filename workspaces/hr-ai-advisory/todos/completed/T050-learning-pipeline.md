# T050 — Platform Learning Pipeline (COC Layer 5)

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Feedback Taxonomy**:

- `FeedbackCategory` enum (WRONG_ANSWER, OUTDATED_INFO, UNCLEAR_EXPLANATION, MISSING_TOPIC, IRRELEVANT_RESPONSE, TOO_GENERIC)
- `RecommendationType` enum (KB_EXPANSION, KB_CORRECTION, PROMPT_REFINEMENT, ROUTING_CHANGE, NEW_SCENARIO)
- `RecommendationStatus` enum (PROPOSED, UNDER_REVIEW, APPROVED, REJECTED, IMPLEMENTED)

**Data Models**:

- `QueryPattern` dataclass tracking detected patterns in user queries — domains, frequency, avg confidence/satisfaction, example queries
- `KbGap` dataclass for detected knowledge base gaps — evidence query count, avg confidence when hit, negative feedback count, suggested provisions, auto-assigned priority
- `RoutingInsight` dataclass for agent routing pattern insights — domain pair co-occurrence, resolution confidence, suggested action
- `ResolutionPattern` dataclass for successful cross-domain resolution patterns — agent sequence, key provisions, success count
- `FeedbackRecord` dataclass for processed feedback with categorisation and session linkage
- `ImprovementRecommendation` dataclass with full review lifecycle — proposal, human review, approval/rejection
- `MonthlyReport` dataclass summarising all pipeline outputs for human review

**Feedback and Pattern Tracking**:

- `record_feedback()` — ingests user feedback (positive/negative with category) into the learning pipeline
- `record_query_pattern()` — records or updates query pattern observations with running average confidence/satisfaction

**KB Gap Detection**:

- `detect_kb_gap()` — registers a detected KB gap with auto-assigned priority based on evidence strength (negative feedback count and avg confidence thresholds)
- `get_kb_gaps()` — retrieves gaps with optional priority filter, sorted by negative feedback count

**Routing and Resolution**:

- `record_routing_insight()` — captures domain co-occurrence patterns for routing optimisation
- `capture_resolution_pattern()` — records successful cross-domain resolution patterns with rolling success count and confidence

**Recommendation Engine**:

- `propose_recommendation()` — creates a platform improvement recommendation with type, priority, and evidence count
- `review_recommendation()` — records human expert review decision (approve/reject) with notes
- `get_recommendations()` — retrieves recommendations with optional status filter

**Monthly Reporting**:

- `generate_monthly_report()` — aggregates feedback records, KB gaps, routing insights, and open recommendations into a monthly summary
- `get_monthly_reports()` — returns all reports, most recent first

**Governance**: All evolved changes go through human review (CARE Human-on-the-Loop).

**Addresses**: R2-GAP4

## Files

- `src/hr_advisory/trust/learning_pipeline.py` — platform learning pipeline module
