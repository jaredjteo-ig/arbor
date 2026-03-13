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

## Key Files

- `src/hr_advisory/kb/` — Content and pipeline
- `src/hr_advisory/kb/embeddings.py` — Embedding pipeline
- `src/hr_advisory/models/` — DataFlow models
- `src/hr_advisory/api/routers/kb.py` — KB endpoints
- `src/hr_advisory/api/routers/search.py` — Search endpoints
- `src/hr_advisory/api/routers/admin.py` — Update lifecycle
- `docs/01-architecture.md` — Architecture docs

## Consult Agent

For KB work: `kb-pipeline-specialist`
