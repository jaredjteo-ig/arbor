# Privacy Policy + ToS Deltas — Xero Integration

What needs to land in Arbor's public-facing privacy policy and
terms of service before the Xero partner-program review is
submitted (M4-T04). Drafted in plain language so legal can adapt
without engineering re-explanation.

Cross-reference: `02-data-retention.md` for the source-of-truth on
what we keep and for how long.

---

## Privacy policy — additions / edits

Add a new section, "Third-party integrations" (or extend an
existing one), with a sub-section per integration. Xero text:

### Xero Accounting

When you connect Arbor to Xero, the following data flows between
the two systems:

**What Arbor reads from Xero**

- Your Xero organisation's name, type, and ID (so we know which
  org to post journals to and can show it in our settings).
- Your Xero chart of accounts (so we can map payroll buckets to
  the correct expense and liability accounts).

We do **not** read invoices, bills, contacts, banking data,
payments, or any customer/supplier records.

**What Arbor writes to Xero**

- ManualJournal entries representing approved payroll runs.
  Each journal is balanced, marked as BAS Excluded for GST, and
  dated to the payroll run's pay date.

We do **not** create, modify, or delete accounts, contacts,
invoices, or any other Xero record on your behalf.

**OAuth credentials**
Connecting Xero issues an OAuth 2.0 access and refresh token.

- Stored: Arbor's primary database, encrypted at rest using a
  Fernet key (`INTEGRATION_ENCRYPTION_KEY`).
- Retention while connected: indefinite, refreshed automatically
  to avoid Xero's 60-day idle expiry.
- Retention after disconnect: tokens are **hard-deleted** when
  you disconnect via Arbor's UI. Tokens auto-disconnected by
  Xero (you revoked from inside Xero, or the refresh window
  expired) are kept for 90 days for dispute resolution then
  redacted; the metadata row is kept for 7 years for audit per
  IRAS Income Tax Act requirements.
- Sharing: not shared with any third party.

**Data residency**
OAuth tokens and audit logs sit in the same Postgres instance as
the rest of your Arbor company data. Region: <fill in based on
deployment — Singapore for the GCP Asia-Southeast1 deployment>.

**Your rights**

- You can disconnect Xero at any time from Settings → Integrations.
- Disconnecting revokes Arbor's authorisation at Xero (your "Connected
  apps" list will no longer show Arbor) and hard-deletes the local
  token row. You can reconnect at any time.
- You can request a copy of all Xero-related audit log rows
  (`xero_export_logs`) Arbor holds for your company by emailing
  support.

---

## Terms of service — additions / edits

Add a "Third-party integrations" section.

### Accuracy and responsibility

Arbor's accounting integrations (currently Xero, with QuickBooks
and Zoho on the roadmap) post **payroll journal data you have
already approved** to your accounting platform. By approving a
payroll run and clicking Export, you confirm that:

1. The figures in the run are correct to the best of your
   knowledge.
2. The account mapping you've configured in Arbor reflects how
   your accountant wants payroll journals categorised.
3. Arbor is not your accounting system of record — your Xero (or
   equivalent) data is the authoritative source.

If a journal posts to the wrong account because of a mapping error
on your side, the correction is your responsibility. Arbor
provides a Void function to neutralise any incorrectly-posted
journal cleanly.

### What Arbor doesn't guarantee

- We don't retry failed Xero posts automatically. If Xero is
  unreachable, the export fails with a clear error and you can
  retry. We don't queue exports during a Xero outage and
  silently flush them later.
- We don't auto-create Xero accounts. Your chart of accounts must
  already contain the codes you're mapping to.
- We don't reconcile Xero data back to Arbor. The journal is a
  one-way push.

### Suspension

We reserve the right to disable a customer's Xero integration if
Xero notifies us of abusive usage (rate-limit violations, malformed
journals, etc.) or if your Arbor account is suspended for separate
reasons.

---

## Where these go

- Public privacy policy: e.g. `apps/landing/src/app/privacy/page.tsx`
  or wherever the marketing site hosts it. The text above goes
  into a new "Third-party integrations" section.
- Public terms of service: same surface, "Third-party integrations"
  section.
- The Xero app's listing privacy/ToS URLs (set in
  developer.xero.com → Configuration) must point to whichever
  pages contain the text above.

---

## Approval gate

Before submitting the partner-program application:

- [ ] Privacy policy updated and live.
- [ ] Terms of service updated and live.
- [ ] URLs in Xero app config point to the updated pages.
- [ ] Sanity-check that data-residency claim matches actual
      deployment region.

When the QuickBooks or Zoho hardening lands (M3-T07 cross-ref),
add equivalent sections under the same "Third-party integrations"
header — the Xero copy is the template.
