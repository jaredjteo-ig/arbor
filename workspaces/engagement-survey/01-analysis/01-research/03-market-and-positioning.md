# Singapore SME market + positioning

## The buyer's status quo

Singapore SMEs (≤200 employees) typically run engagement surveys via
one of these three:

1. **Google Forms / Microsoft Forms.** Free, no integration. HR
   exports CSV, opens in Sheets, tries to do pivot tables. ~70% of
   SMEs we've seen.
2. **Engagement-only SaaS.** Lattice, CultureAmp, Officevibe, 15Five.
   $5–$15 per employee per month. Integration with HRIS is a paid
   add-on or non-existent. ~20%.
3. **Annual GPTW Trust Index.** Outsourced to GPTW, single annual
   data point, no operational signal in between. ~10% (and these
   often run #1 in parallel for pulse).

**Pain points.**

- **Disconnection from HRIS.** Survey results don't link to the
  employee record, the appraisal, the exit interview. HR keeps three
  spreadsheets and ties them by name.
- **Aggregation toil.** "What does HR do with the data?" — usually
  pivot tables in Sheets, then a slide deck. Manual every cycle.
- **Survey fatigue.** Quarterly long-form surveys → low response
  rates. Pulse alternative isn't on the radar for most SMEs.
- **Anonymity tension.** With 7 employees in Engineering and 1
  female engineer, "anonymous by department" is not anonymous.
  Existing tools don't surface this risk.

## Where the platform wins

We are NOT competing with Lattice on depth. We win on three vectors:

### 1. Native lifecycle integration

Engagement is one stage of a lifecycle the platform already covers
end-to-end. We can show:

- Engagement pulse score declining → appraisal score also declining
  → predicted retention risk → exit interview cited the same theme.

This is the demo's value flow. Lattice can't do this — they have
engagement, no appraisal/leave/payroll/exit. CultureAmp has a thin
HRIS sync; not native.

### 2. Compliance-aware copy

Every survey can include a one-line PDPA notice ("Anonymous responses
are not linked to your employee record. We aggregate by department of
≥5 to prevent re-identification.") The platform already maintains
PDPA-aware patterns (P33 anonymity collapse, P34 no-PII derived
views) — engagement reuses them.

### 3. Singapore-shaped templates

The library ships with a "Singapore SME quarterly pulse" template
that asks specifically Singapore-relevant questions:

- "How fairly are flexible-work arrangements applied across the
  team?" (FWA mandate context)
- "Do you feel comfortable raising fair-employment concerns?" (TAFEP)
- "How clear is your manager about CPF / payroll deductions?"

That's defensibly different from US-shaped Lattice / 15Five content.

## Value propositions

1. **The only HR platform that connects engagement to retention,
   appraisal, and exit data in one click.** Buyers see the gap-to-exit
   timeline natively; they don't get this from any standalone survey
   tool.
2. **Singapore-shaped templates ready out of the box.** Q12-style,
   Trust-Index-pillars, Pulse, plus a "Singapore SME quarterly" with
   PDPA / FWA / TAFEP / CPF context.
3. **Pulse cadence with no extra cost.** Schedule once, runs forever;
   no per-survey fee, no separate tool.

## Unique selling points (USPs — be critical)

A USP is a thing the buyer can ONLY get from us. Be honest about which
of the above are USPs vs. table stakes.

- **TABLE STAKES (everyone has these):** Q12 paraphrase, Trust Index
  pillars, Likert/free-text questions, response collection.
- **DIFFERENTIATED (some competitors, not all):** anonymity
  with re-identification protection, cohort targeting,
  scheduled pulse cadence, in-app + tokenised email delivery.
- **TRUE USP (only us):** the lifecycle cross-reference.
  Engagement-pulse-score → exit-interview-theme correlation, displayed
  natively without HR doing manual joins. **This is the only thing in
  the value-proposition list a Lattice buyer cannot get from Lattice.**

The demo MUST showcase the USP, not the table stakes. Don't lead
with "we have Q12 paraphrase" — lead with "show me the engagement
trend of the 3 people who resigned last quarter, side by side with
their exit-interview themes."

## Pricing implications (out of scope, noted)

- Engagement-only SaaS: $5–15 per employee per month.
- We're already in the customer's pocket via the HRIS subscription;
  this is bundled-included. Differentiates further on TCO.
- Trust Index certification path: HR can export Trust-Index data in
  the GPTW-required format → upgrade hook to a paid certification
  add-on. (v2.)

## AAA framework alignment

| Lever    | What we automate / augment / amplify                     |
| -------- | -------------------------------------------------------- |
| Automate | Pulse-survey scheduling, theme tagging, cohort fan-out   |
| Augment  | Theme correlation across exit / appraisal / engagement   |
| Amplify  | A non-HR-specialist manager runs a Gallup-quality survey |

## Network behaviours (platform model)

| Behaviour       | What ships in v1                                            |
| --------------- | ----------------------------------------------------------- |
| Accessibility   | 3-7 questions, mobile-friendly, 90s pulse                   |
| Engagement      | Trend chart per question; HR sees % response live           |
| Personalization | Cohort filters; per-employee landing card                   |
| Connection      | Reward stage tile + activity-feed entries; cross-stage v2   |
| Collaboration   | Manager-level views (team aggregate, ≥5 employee threshold) |

## 80 / 15 / 5 product focus

- **80% agnostic.** Survey templates, response capture, theme tally,
  cohort targeting, schedule. Usable for any HR product anywhere.
- **15% configurable self-service.** Question library, cohort
  definition spec, cadence config, anonymity threshold.
- **5% Singapore-customisation.** PDPA copy, FWA/TAFEP/CPF question
  prompts, Trust-Index export format.

## Risks to flag for the plan

1. **Gallup IP.** Use a paraphrase + visible attribution; don't ship
   verbatim Q12.
2. **Small-cohort de-anonymization.** Enforce a minimum cohort size
   (e.g. ≥5) for any aggregated view. P33/P34 patterns are
   directly applicable.
3. **Survey fatigue.** Default cadence of monthly pulse is right;
   shipping a daily-pulse default would tank response rates and the
   demo would look thin within a month.
4. **LLM cost on theme analysis.** P13 budget cap applies. v1 uses
   deterministic keyword sweep; v2 LLM is gated by per-tenant cost
   guard.
5. **Manager dashboard scope creep.** "Manager views team aggregate"
   is a real feature with anonymity rules. v1 ships HR-only; v2
   adds manager view.
