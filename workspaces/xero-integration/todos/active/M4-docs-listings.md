# M4 — Documentation + Marketplace Listings

Customer-facing documentation, internal runbooks, and the Xero App
Marketplace listing prep. None of these are code blockers but all
are sales/support multipliers.

---

## M4-T01 — Customer-facing user guide

**Tasks:**

1. New page at `apps/web/src/app/(dashboard)/help/xero-integration/page.tsx`
   (or in the docs site if one exists).
2. Cover:
   - "How to connect Xero" — screenshots of the Settings flow.
   - "Account mapping explained" — what each of the six buckets
     does, with example chart-of-accounts entries.
   - "Why my export failed" — common errors (account archived,
     scope changed, mapping wrong) with one-click remediation.
   - "What does void do?" — accountant-friendly explanation.
   - "Idempotency and retry safety" — for technical buyers.
   - "Rate limits and large companies" — when to stage exports.
   - FAQs.
3. Link from the export modal: "Need help? See the Xero guide."
4. Cross-link from the mapping page.

**Acceptance:** A new customer can self-serve OAuth → first export
without filing a support ticket.

**Files:** `apps/web/src/app/(dashboard)/help/xero-integration/page.tsx`,
embedded in the app.

---

## M4-T02 — Internal support runbook

**Tasks:**

1. New file `deploy/runbooks/xero-support.md`:
   - "Customer says their export failed" — diagnostic SQL queries,
     log grep snippets, common root causes.
   - "Customer says they're not connected" — token state checks.
   - "Customer says journal posted twice" — XeroExportLog query to
     verify, void-procedure walkthrough.
   - "How to manually reset a customer's Xero connection."
2. Cross-reference with the deployment runbook (M1-T08).
3. Walk a teammate through one full simulated incident before
   considering the runbook done.

**Acceptance:** Tier-1 support can resolve common Xero issues
without escalating to engineering.

**Files:** `deploy/runbooks/xero-support.md` (new).

---

## M4-T03 — Xero App Marketplace listing prep

**Problem:** Xero has an App Marketplace
(https://apps.xero.com). Listed apps get organic traffic from
Xero customers searching for HRIS integrations. The listing is
gated on the partner-program app being approved (M1-T01).

**Tasks (separate workstream — block on M2 ship):**

1. Create new workspace `workspaces/xero-marketplace-listing/`.
2. Assets needed:
   - 256×256 PNG logo (Xero spec).
   - 4 × screenshots of the integration in action (1280×720).
   - Demo video (60-90s).
   - App description (long + short form).
   - Support URL, privacy policy URL, terms URL.
   - Pricing model (likely "free for current Arbor customers").
3. Submit listing via developer.xero.com → Marketplace.
4. Monitor listing engagement metrics.

**Acceptance:** Listing live in the Xero App Marketplace and
discoverable.

**Files:** `workspaces/xero-marketplace-listing/` (new).

---

## M4-T04 — Privacy policy + ToS updates

**Tasks:**

1. Update Arbor's privacy policy to disclose Xero data flow:
   - What Xero data we read (chart of accounts, organisation name).
   - What Xero data we write (manual journals).
   - How long OAuth tokens are retained (cross-ref M1-T10).
   - Data residency (where Arbor stores the encrypted tokens).
2. Update terms of service to clarify accounting-data accuracy
   responsibility (we post; customer verifies).
3. Make sure the Xero app's listed privacy policy URL points to a
   page that covers this.

**Acceptance:** Legal/compliance reviewable; matches what's
disclosed in Xero's app review.

**Files:** Public-facing privacy/ToS pages.
