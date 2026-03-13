# T007 — DataFlow Models: Regulatory Knowledge Base

## Status: COMPLETED

## What Was Built

7 DataFlow models for the regulatory knowledge base, plus pgvector integration:

| Model             | Purpose                                        | Key Fields                                                                                   |
| ----------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Act               | Legislative acts and guideline documents       | title, short_name, authority_type, issuing_body, official_url                                |
| Domain            | HR knowledge domain hierarchy                  | name, description, parent_domain_id (self-referential)                                       |
| Provision         | Specific clauses and provisions (core KB unit) | section, formal_text, plain_summary, interpretation_notes, authority_level, superseded_by_id |
| ApplicabilityRule | Conditions for when provisions apply           | rule_type, criteria_type, criteria_value (JSON)                                              |
| CrossReference    | Relationships between provisions               | source/target provision, relationship_type                                                   |
| PracticalExample  | Worked examples with calculations              | scenario, calculation (JSON), outcome                                                        |
| RateTable         | Numerical rates (CPF, levies, thresholds)      | table_type, criteria (JSON), rate_value, effective/expiry dates                              |

## Supporting Infrastructure

- **database.py** — DataFlow instance with PostgreSQL connection, auto_migrate
- **enums.py** — AuthorityLevel, RiskTier, ApplicabilityRuleType, CrossReferenceType
- **vector_setup.py** — pgvector adapter for 1536-dim embeddings with HNSW index
- **vector_search_node.py** — Custom ProvisionSimilaritySearchNode with domain/authority filtering

## Design Decisions

- **Soft delete**: Provision and RateTable use `is_active` flag (regulatory data never truly deleted). `__dataflow__` has `soft_delete: True` config + explicit `deleted_at` field for future DataFlow support.
- **JSON fields**: `Optional[dict]` (not `Dict[str, Any]`) to avoid DataFlow isinstance checks with subscripted generics.
- **Enums as strings**: Python enums for type safety in app code, stored as TEXT in DB.
- **interpretation_notes**: Red team fix R2-COC-REC6 — stores institutional interpretation, not just raw text.
- **pgvector**: 1536-dim embeddings (OpenAI text-embedding-3-small), HNSW index, cosine distance.

## Verification

28 tests passing:

- Model registration (8), enum values (4), field validation (7)
- Database CRUD against real PostgreSQL (6) — including hierarchy, JSON, deactivation
- pgvector smoke test (3) — extension, insert, cosine similarity search

## Files

- `src/hr_advisory/models/database.py`
- `src/hr_advisory/models/enums.py`
- `src/hr_advisory/models/knowledge_base.py`
- `src/hr_advisory/models/vector_setup.py`
- `src/hr_advisory/models/vector_search_node.py`
- `src/hr_advisory/models/__init__.py` (updated)
- `tests/integration/test_knowledge_base_models.py`
