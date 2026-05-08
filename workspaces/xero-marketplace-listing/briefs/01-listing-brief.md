# Xero App Marketplace — Listing Brief

Submission to https://apps.xero.com requires assets and copy
prepared in advance. This brief is the source of truth for
everything we'll need; build the actual listing once 3+ paying
customers have connected and Arbor's app has been certified through
the partner program.

Cross-reference: `workspaces/xero-integration/todos/active/M4-docs-listings.md`
(M4-T03), and `deploy/xero-deployment-runbook.md` for the deployment
that backs the listing.

---

## App identity

- **Name on listing**: Arbor — Singapore HR & Payroll
- **Tagline (max 80 chars)**: AI-powered HRIS for Singapore SMEs.
  Payroll, leave, compliance.
- **Category**: Payroll & HR (Xero's standard category)
- **Geography**: Singapore primary; AU/NZ/UK secondary

## Logo

Required: 256×256 PNG, transparent background, full bleed acceptable.

- File: `apps/web/public/xero-marketplace-logo.png` (to be produced)
- Source: Arbor's existing `HR` monogram on blue 600 — high contrast
  works on Xero's white listing background.

## Screenshots (4 required, 1280×720 PNG)

Plan to capture from a populated demo company on the live deployment:

1. **Settings → Integrations** with Xero connected, showing the
   "Connected to <org>" status badge. Communicates one-click setup.
2. **Payroll run detail page** with the Export to Xero button visible
   and the green "Exported · journal X" badge from a prior run.
   Communicates: this is a real workflow, not a screenshot of an
   empty state.
3. **Export modal mid-flow**: account mapping section with
   auto-matched suggestions visible, BASEXCLUDED GST badge in the
   footer, debit/credit preview table on the right. Communicates
   correctness signals an accountant looks for.
4. **Mapping settings page**: typeahead open, account search filtered,
   mapping-health banner visible (with one stale code highlighted).
   Communicates: we handle the day-2 problems.

## Demo video (optional but high-conversion)

60–90 seconds, no voiceover required (silent + captions performs
well for this audience). Shot list:

1. Settings → Integrations → Connect Xero → consent screen → return
   (10s).
2. Payroll run detail → Export to Xero → modal opens → mapping
   pre-filled → Post to Xero → success preview (40s).
3. Switch to Xero browser tab → Reports → Journal Report → new
   ManualJournal visible with correct narration and BASEXCLUDED
   tax type (15s).
4. End card with "Try Arbor for Singapore SMEs" + URL (10s).

## Long-form description (~600 words)

Working draft (to be edited before submission):

> Arbor is the modern HRIS Singapore SMEs use to run payroll, manage
> leave, and stay compliant with the Employment Act, CPF, IRAS, and
> MOM. The Xero integration posts every approved payroll run to your
> Xero books as a balanced ManualJournal — no spreadsheets, no
> double entry.
>
> **What it does**
>
> - Posts payroll journals to Xero with one click.
> - Auto-matches your Xero chart of accounts to the six payroll
>   buckets (salary, bonus, employer CPF, SDL/FWL, statutory
>   payable, net pay payable).
> - Marks every line as BAS Excluded so your GST F5 return stays
>   accurate.
> - Voids and re-posts cleanly when you need to correct a run —
>   no duplicates in your books.
> - Bulk-exports historical runs for mid-year onboarding.
>
> **What makes it safe**
>
> - Posts only to manual journals — never invoices, contacts, or
>   banking.
> - Idempotency keys prevent duplicate posts on retry.
> - Mapping health checks flag archived or renamed accounts before
>   your next export.
> - Full audit trail in Arbor: who exported what, when, with the
>   exact journal hash.
> - PDPA-compliant: tokens encrypted at rest, hard-deleted on
>   disconnect, revoked at Xero's side.
>
> **Pricing**
>
> Included free with any Arbor subscription. No per-export fees, no
> per-employee surcharge.
>
> **Singapore SME first**
>
> Built for SG payroll: CPF age bands, SHG funds, SDL, FWL, statutory
> file generation. The Xero integration mirrors how SG accountants
> structure payroll journals — out of the box.

## Short-form description (~140 chars)

> Post Singapore payroll to Xero as balanced ManualJournals.
> Auto-mapped, GST-correct (BAS Excluded), with one-click void
> &amp; bulk export.

## Support URL

Production help page: https://central.kailash.ai/help/xero-integration
(or the deployed equivalent at the time of submission).

## Privacy policy URL

Must explicitly cover Xero data flow:

- What we read: chart of accounts only, plus org name/type for
  display.
- What we write: ManualJournals on the user's behalf.
- Where tokens are stored: Fernet-encrypted in Arbor's primary
  Postgres in the user's data residency region.
- Retention: tokens hard-deleted on disconnect; metadata kept for
  90 days then redacted; audit log kept 7 years (IRAS).
- Third parties: none — we never share Xero data with anyone.

Update Arbor's privacy policy to match before submission.

## Terms of service URL

Must clarify:

- Customer is responsible for verifying journal accuracy before
  Arbor posts.
- Xero is the system of record for accounting; if Xero rejects a
  posting, Arbor surfaces the error but does not retry blindly.
- Voids and corrections are the customer's responsibility once a
  journal is posted.

## Pre-submission checklist

- [ ] 3+ paying customers actively using the integration (Xero's
      partner-program gate).
- [ ] M0+M1+M2 + critical M3 items (T01 logging, T02 alerting,
      T05 test connection) shipped.
- [ ] Production deploy has been stable for ≥ 30 days.
- [ ] Privacy policy and ToS updated to mention Xero.
- [ ] Customer references prepared (3 willing to be quoted).
- [ ] Logo + 4 screenshots + demo video produced.
- [ ] Long-form description finalised (this doc).

## Pricing for the listing

Free as part of Arbor subscription. Match Xero's expected pricing
copy: "Free with Arbor — ask Arbor for pricing".

## Contact

For Xero's review team: standard Arbor support email (TBD).

## Out of scope

- Two-way sync (we don't read invoices, bills, etc.).
- Foreign-currency journals (deferred — see M2-T12).
- Auto-creation of accounts in Xero (we use the customer's existing
  chart only).
