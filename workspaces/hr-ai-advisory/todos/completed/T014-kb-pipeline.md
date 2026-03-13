# T014 — Knowledge Base Content Pipeline and Tooling

## Status: COMPLETED

## What Was Built

### Pipeline (`src/hr_advisory/kb/pipeline.py`)

- `KBContentPipeline` — bulk loading of regulatory content via DataFlow nodes
- `load_act/domain/provision/applicability_rule/cross_reference/practical_example/rate_table`
- `bulk_load` — accepts structured bundle dict (act + domains + provisions + rules + examples + cross-refs + rate tables)
- Idempotent on act short_name and domain name
- Resolves act_short_name → source_act_id and domain_name → domain_id automatically

### Validator (`src/hr_advisory/kb/validator.py`)

- Required/recommended field validation for provisions
- Bundle validation (all provisions in a bundle)
- DB integrity checks: orphan rules, missing cross-ref targets, provisions without domains, rate tables without source_url
- Quality report: provision counts per domain, provisions with/without examples

### Embedding Pipeline (`src/hr_advisory/kb/embeddings.py`)

- OpenAI text-embedding-3-small integration
- Batch embedding with graceful API key absence handling
- Generates combined text (section + title + summary + formal_text) for optimal embeddings

### Admin Functions (`src/hr_advisory/kb/admin.py`)

- `add_provision` — add single provision by act short_name
- `update_provision` — version management (new record, old marked superseded)
- `get_kb_stats` — counts of all entity types
- `search_provisions` — keyword search with optional domain filter

## Key Learning

- DataFlow ListNode caching requires `enable_cache: False` for fresh reads after raw SQL cleanup
- DataFlow ListNode returns `{"records": [...]}` dict, not a plain list — must use `_extract_records()` helper

## Verification

37 tests passed (0 failures, 0 skips)

## Files

- `src/hr_advisory/kb/pipeline.py`
- `src/hr_advisory/kb/validator.py`
- `src/hr_advisory/kb/embeddings.py`
- `src/hr_advisory/kb/admin.py`
- `src/hr_advisory/kb/__init__.py`
- `tests/integration/test_kb_pipeline.py`
