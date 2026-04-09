---
name: kb-management
description: "Knowledge base pipeline and content management. Use when loading provisions, managing search, handling regulatory updates, or working with embeddings."
---

# Knowledge Base Management

## Content Pipeline

```
Legislative Source → KB Loader → DataFlow Nodes → PostgreSQL → Embeddings → pgvector
```

## DataFlow Models

| Model          | Purpose                  | Key Fields                                                            |
| -------------- | ------------------------ | --------------------------------------------------------------------- |
| Act            | Legislative acts         | name, short_name, jurisdiction                                        |
| Domain         | HR domains               | name, slug, description                                               |
| Provision      | Legal provisions         | title, formal_text, plain_summary, section_reference, authority_level |
| CrossReference | Links between provisions | source_provision_id, target_provision_id, relationship_type           |

## Content Structure

Each provision includes:

- **formal_text** — Exact legal text
- **plain_summary** — SME-friendly explanation
- **section_reference** — e.g., "Part IV, Section 38"
- **authority_level** — statutory/subsidiary/tripartite/administrative/best_practice
- **practical_examples** — JSON array of real-world scenarios
- **applicability_rules** — JSON defining who this applies to
- **effective_date** / **review_date** — Currency tracking

## Search

### Semantic (pgvector)

```python
# POST /search/semantic
{"query": "annual leave", "top_k": 10, "domain_id": null, "threshold": 0.7}
```

Ranking: title match (highest) > summary > formal text

### Full-text

```python
# POST /search/fulltext
{"query": "notice period", "domain_id": null, "act_id": null, "page": 1}
```

Filters: domain, act, authority level, effective date range

### Fallback

Keyword-density scoring when pgvector unavailable.

## Embedding Pipeline

File: `src/hr_advisory/kb/embeddings.py`

Model: `EMBEDDING_MODEL` env var (default: `text-embedding-3-small`)

NEVER hardcode the model name.

## Regulatory Update Lifecycle

```
draft → in_review → approved → published (or rejected)
```

Endpoints in `src/hr_advisory/api/routers/admin.py`:

- `POST /admin/updates` — Create draft
- `POST /admin/updates/{id}/submit` — Submit for review
- `POST /admin/updates/{id}/approve` — Human gate (CARE)
- `POST /admin/updates/{id}/publish` — Update KB

## Staleness Tracking

- `GET /admin/staleness/summary` — Status counts
- `GET /admin/staleness/stale` — Past review date
- `POST /admin/staleness/review` — Record review

## Content Bundles (Pre-Written)

7 content modules at `src/hr_advisory/kb/content/`:

| Module                    | Act Short Name | Provisions | Status    |
| ------------------------- | -------------- | ---------- | --------- |
| `employment_act.py`       | EA             | 17         | Loaded    |
| `cpf.py`                  | CPFA           | 8          | Loaded    |
| `foreign_manpower.py`     | EFMA           | 8          | Loaded    |
| `tafep.py`                | TGFEP          | 9          | Loaded    |
| `remaining_domains.py`    | CDCSA          | 16         | Loaded    |
| `industrial_relations.py` | IRA            | 9          | Loaded    |
| `adversarial_gaps.py`     | Multiple       | ~32        | Test data |

**Total loaded: 67 provisions, 6 acts, 29 domains, 62 applicability rules, 56 examples, 27 cross-references, 28 rate tables.**

## Seed Script

`scripts/seed_kb.py` — loads all content bundles via `KBContentPipeline.bulk_load()`.

**Idempotent**: `load_provision` checks `_find_provision_by_section` before creating. Safe to re-run. Child records (rules, examples) only created for newly-created provisions (`_newly_created` flag).

**To run on live server** (must stop backend first to free Postgres connections):

```bash
docker compose stop backend
docker start arbor-backend && sleep 10
docker exec -w /app arbor-backend python seed_kb.py
docker compose start backend
```

## Compliance Domain Mapping

The compliance router maps domain keys to KB Act short_names:

| Compliance Key   | Act Short Name | Sub-filter                          |
| ---------------- | -------------- | ----------------------------------- |
| employment_act   | EA             | —                                   |
| cpf              | CPFA           | —                                   |
| foreign_manpower | EFMA           | —                                   |
| tax              | CDCSA          | domain: "Tax Obligations"           |
| wsh              | CDCSA          | domain: "Workplace Safety & Health" |
| fair_employment  | TGFEP          | —                                   |

File: `src/hr_advisory/api/routers/compliance.py` — `_DOMAIN_TO_ACT_SHORT_NAMES` and `_DOMAIN_TO_KB_DOMAIN_NAMES`

## Advisory KB Retrieval

`src/hr_advisory/agents/orchestration/kb_retriever.py` maps specialist domain keys to KB domain names. Search is keyword-based (word overlap scoring across title, section, formal_text, plain_summary). No embeddings/vectors currently used.

## Key Files

- `src/hr_advisory/kb/` — Content and pipeline
- `src/hr_advisory/kb/content/` — 7 content bundle modules
- `src/hr_advisory/kb/pipeline.py` — KBContentPipeline (bulk_load, load_provision, idempotent)
- `src/hr_advisory/kb/admin.py` — search_provisions, get_kb_stats
- `src/hr_advisory/kb/embeddings.py` — Embedding pipeline (not yet populated)
- `src/hr_advisory/models/knowledge_base.py` — DataFlow models (Act, Domain, Provision, etc.)
- `src/hr_advisory/api/routers/kb.py` — KB query endpoints
- `src/hr_advisory/api/routers/compliance.py` — Compliance status (domain→act mapping)
- `src/hr_advisory/api/routers/admin.py` — Update lifecycle + alert email on publish
- `scripts/seed_kb.py` — Bulk loader script

## Consult Agent

For KB work: `kb-pipeline-specialist`
