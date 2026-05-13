# P4-LP — Landing page & procurement surface

**Source audit:** `04-validate/07-buyer-audit-2026-05-08.md` P1 + P3.

**Problem.** Live landing page has only a "Login" CTA. Signup is
invitation-only. As a true new customer (Obayashi's HR procurement),
you cannot self-onboard, and there's nothing on the page to
unblock a procurement conversation:

- No "Book a demo" / "Request access" path
- No trust signals (PDPA / SG-hosted / audited)
- No pricing or "Contact for pricing" tiers
- No customer logos / testimonial strip (later, not now)

These don't block a paid pilot once procurement says yes, but they
prevent the buyer from getting to the "I want to talk to you" stage
without an outbound conversation.

**Estimate:** 1 day total (FE only — copy + form + page).

**Bundling:** single commit "P4-LP marketing surface". No
dependency on P4-QW or P4-MG.

---

## P4-LP-1 — Book-a-demo CTA + form

- **What:** primary CTA on the landing page next to (or instead of)
  "Login" → "Book a demo".
- **Where:**
  - FE: `apps/landing/src/...` (the Netlify-hosted landing app, not
    the dashboard app).
  - Form already exists with Netlify form attribute from the earlier
    contact-form work — reuse it. Or wire to a Resend/Postmark
    transactional email.
- **Form fields:**
  - Company name (required)
  - Number of employees (required, dropdown bands: 1-50 / 51-200 /
    201-500 / 500+)
  - Contact name (required)
  - Email (required)
  - Phone (optional, +65 default)
  - "What's prompting you to look now?" (optional textarea)
- **Submit:** drops a record into the existing Netlify form intake
  OR posts to a `/api/contact-demo` endpoint that mails the team.
- **Acceptance:**
  - Landing page shows two CTAs above the fold: "Book a demo"
    (primary) and "Login" (secondary).
  - Form submission yields an immediate "Thanks — we'll be in
    touch within 1 working day" confirmation.
  - Submission shows up in the configured channel (Netlify dashboard
    or transactional email inbox).
- **Regression test:** Playwright on the landing app — fill form,
  submit, assert confirmation.

---

## P4-LP-2 — Trust strip

- **What:** a single horizontal strip above the fold (or just
  below) with 4-6 trust signals.
- **Items to include:**
  - **PDPA-compliant** — "PII encrypted at rest, all data accessed
    only for HR/payroll purposes." (Mirror the copy from My
    Profile.)
  - **Singapore-hosted** — "Data centre in Singapore (or AP-SE1).
    No data leaves the region." (Verify before claiming.)
  - **Statutory file generation** — "CPF e-Submit + Bank GIRO + IR8A
    files generated to Singapore CPF Board / IRAS formats."
  - **No AI in payroll math** — "Deterministic calculations,
    auditable. AI only for advisory + compliance Q&A." (Mirror the
    calculator page tagline.)
  - **Cited employment-law advisory** — "Every advisory answer
    cites the underlying Employment Act / CPF / EFMA provision."
- **Constraint:** every claim must be true today. Don't add ISO
  27001 or SOC 2 if not yet audited.
- **Where:** new section component on the landing app.
- **Acceptance:** strip renders above the fold on desktop; stacks
  cleanly on mobile (<640px).
- **Regression test:** Playwright responsive screenshot at 1280px
  and 375px viewports.

---

## P4-LP-3 — Pricing transparency

- **What:** dedicated `/pricing` page on the landing app with named
  tiers (or, at minimum, "Contact for pricing" with a tier matrix).
- **Approach:**
  - **Path A (recommended for now):** "Contact for pricing" page
    with named tiers showing only what's included, no $ figures:
    - **Starter** — up to 50 employees, core HR + payroll + advisory
    - **Growth** — 51-200 employees, + integrations + analytics
    - **Enterprise** — 201+ employees, + dedicated success
      manager + custom SLA
  - **Path B (later):** publish band pricing once 3+ paying customers
    are stable and the cost model is calibrated.
- **Where:** new page on the landing app, link in the top nav.
- **Acceptance:**
  - `/pricing` accessible from the landing nav.
  - Each tier has a clear "Talk to sales" CTA that opens the
    book-a-demo form pre-filled with the tier.
- **Regression test:** Playwright — visit each tier link, fill the
  pre-filled form, submit.

---

## Cross-cutting for P4-LP bundle

- **Copy review:** before shipping, have a human read all marketing
  copy for tone alignment (`rules/communication.md` — plain language,
  outcomes-first).
- **Independence rule:** all copy must respect `rules/independence.md`
  — no "open-source version of X", no commercial-product references.
  Describe Arbor on its own terms.
- **Don't pre-build:** customer logo wall, video testimonials, case
  studies — defer until 3+ named customers consent.
