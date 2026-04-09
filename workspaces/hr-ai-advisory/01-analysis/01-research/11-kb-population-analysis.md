# KB Population Analysis

## Current State

The Knowledge Base is **empty** on the live site — 0 provisions, 0 domains, 0 acts. This is why the advisory AI returns "low confidence, escalate to specialist" for every question.

## Good News: Content Already Exists

The content bundles are **pre-written** at `src/hr_advisory/kb/content/`:

| Module                    | Act                 | Provisions   | Coverage                                                |
| ------------------------- | ------------------- | ------------ | ------------------------------------------------------- |
| `employment_act.py`       | Employment Act 1968 | 17           | KET, payslips, leave, OT, termination, salary, Part IV  |
| `cpf.py`                  | CPF Act             | 8            | Contribution rates, age bands, PR gradation, OW ceiling |
| `foreign_manpower.py`     | EFMA                | 8            | Quotas, levies, work passes, DRC                        |
| `tafep.py`                | TGFEP Guidelines    | 9            | Fair employment, FWA, grievance, discrimination         |
| `remaining_domains.py`    | WSH + Tax + others  | 16           | Safety, IRAS, SDL, SHG                                  |
| `industrial_relations.py` | IRA                 | 9            | Unions, disputes, TADM                                  |
| `adversarial_gaps.py`     | Multiple            | Gap-specific | Edge cases for testing                                  |

**Total: ~70 provisions ready to load.**

## Loading Approach

The KB has a `KBContentPipeline` with `bulk_load(bundle)` that:

1. Creates the Act record (idempotent — checks by short_name)
2. Creates Domain records (hierarchical)
3. Creates Provision records with formal_text, plain_summary, interpretation_notes
4. Creates ApplicabilityRule records (headcount thresholds, sector filters)
5. Creates CrossReference records between provisions
6. Creates PracticalExample records with worked calculations

## What Needs to Happen

1. **Create a seed script** that calls `pipeline.bulk_load()` for each content module
2. **Run it against the live database** via SSH into the backend container
3. **Verify** the compliance dashboard shows domains covered
4. **Test** the advisory AI answers with citations

## Impact

Once loaded:

- Compliance dashboard: 0/5 → 5/5 domains covered
- Advisory AI: answers with cited provisions instead of "low confidence"
- Provision tags: clickable → advisory gives grounded answers
- Compliance checklist: backend check returns real findings with provision IDs
