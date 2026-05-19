import Link from "next/link";
import {
  ArrowLeft,
  Building2,
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  Shield,
  TriangleAlert,
} from "lucide-react";
import { AppCard } from "@/components/design-system";

/**
 * Customer-facing Xero integration guide.
 *
 * In-app at /help/xero-integration. Reachable from the export modal
 * footer ("Need help?") and the mapping page footer ("Xero
 * integration help"). Plain language; no engineering jargon.
 */
export default function XeroIntegrationHelpPage() {
  return (
    <div className="max-w-3xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      <Link
        href="/payroll"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-gray-600)] hover:text-[var(--color-gray-900)]"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to payroll
      </Link>

      <div>
        <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
          Xero integration — help guide
        </h1>
        <p className="text-sm text-[var(--color-gray-500)] mt-1">
          Connect your Xero organisation to Central and post payroll journals
          straight to your books. Works with any Xero plan.
        </p>
      </div>

      <Section
        icon={<Building2 className="w-5 h-5 text-blue-600" />}
        title="How to connect Xero"
      >
        <ol className="list-decimal list-inside space-y-2 text-sm text-[var(--color-gray-700)]">
          <li>
            Go to{" "}
            <Link
              href="/settings/integrations"
              className="text-blue-600 hover:underline"
            >
              Settings → Integrations
            </Link>
            .
          </li>
          <li>
            Click <strong>Connect</strong> on the Xero card.
          </li>
          <li>
            You&apos;ll be redirected to Xero to confirm. Click{" "}
            <strong>Allow access</strong>.
          </li>
          <li>
            If your login has access to multiple Xero organisations (common for
            bookkeepers), you&apos;ll see a picker — choose the one Central
            should post journals to.
          </li>
          <li>
            You&apos;ll land back at Settings with a green &ldquo;Xero
            connected&rdquo; banner. That&apos;s it.
          </li>
        </ol>
        <p className="text-xs text-[var(--color-gray-500)] mt-3">
          Note: while Central is in early access, Xero shows an
          &ldquo;unverified app&rdquo; warning during connection — that will go
          away once we&apos;re certified through Xero&apos;s partner program.
          You can safely click through it.
        </p>
      </Section>

      <Section
        icon={<CheckCircle2 className="w-5 h-5 text-emerald-600" />}
        title="Account mapping explained"
      >
        <p className="text-sm text-[var(--color-gray-700)]">
          Before your first export, Central needs to know which Xero accounts to
          post to. There are <strong>six buckets</strong>:
        </p>
        <ul className="text-sm text-[var(--color-gray-700)] list-disc list-inside space-y-1.5 mt-3">
          <li>
            <strong>Salary Expense</strong> (debit) — basic wages.
          </li>
          <li>
            <strong>Bonus Expense</strong> (debit) — any bonus paid in the
            period.
          </li>
          <li>
            <strong>Employer CPF Expense</strong> (debit) — your share of CPF.
          </li>
          <li>
            <strong>SDL + FWL Expense</strong> (debit) — Skills Development Levy
            and Foreign Worker Levy if applicable.
          </li>
          <li>
            <strong>CPF &amp; Statutory Payable</strong> (credit, a liability
            account) — what you owe to CPF Board, MOM, IRAS.
          </li>
          <li>
            <strong>Net Pay Payable</strong> (credit, a liability) — what you
            owe employees.
          </li>
        </ul>
        <p className="text-sm text-[var(--color-gray-700)] mt-3">
          Central auto-suggests a mapping the first time by reading your Xero
          chart of accounts. You confirm or edit, and the mapping is saved
          across exports. You can revisit it any time at{" "}
          <Link
            href="/settings/integrations/xero"
            className="text-blue-600 hover:underline"
          >
            Settings → Integrations → Xero
          </Link>
          .
        </p>
      </Section>

      <Section
        icon={<TriangleAlert className="w-5 h-5 text-amber-600" />}
        title="Why my export failed"
      >
        <dl className="text-sm text-[var(--color-gray-700)] space-y-3">
          <div>
            <dt className="font-semibold">
              &ldquo;Xero rejected one or more account codes&rdquo;
            </dt>
            <dd className="text-[var(--color-gray-600)] mt-0.5">
              An account in your mapping was archived or renamed in Xero. Open
              the mapping page, click <strong>Refresh accounts</strong>, fix any
              flagged mappings, then retry.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">
              &ldquo;Your Xero connection expired or was revoked&rdquo;
            </dt>
            <dd className="text-[var(--color-gray-600)] mt-0.5">
              Xero invalidates tokens after 60 days of disuse. Click{" "}
              <strong>Reconnect Xero</strong> and pick the same organisation.
              Your mapping is preserved.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">
              &ldquo;Pay date is required&rdquo;
            </dt>
            <dd className="text-[var(--color-gray-600)] mt-0.5">
              Set the pay date on the payroll run before exporting. Xero posts
              the journal to that date in your organisation&apos;s timezone —
              getting it right matters for period accuracy.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">
              &ldquo;Another export in progress&rdquo; (409)
            </dt>
            <dd className="text-[var(--color-gray-600)] mt-0.5">
              Two clicks landed within the same second — Central blocks the
              second one to prevent posting twice. Wait three seconds and retry.
            </dd>
          </div>
        </dl>
      </Section>

      <Section
        icon={<RefreshCw className="w-5 h-5 text-[var(--color-gray-600)]" />}
        title="What does Void do?"
      >
        <p className="text-sm text-[var(--color-gray-700)]">
          If you exported a run by mistake (wrong period, wrong mapping, wrong
          amounts), click <strong>Void Xero export</strong> on the run detail
          page.
        </p>
        <ul className="list-disc list-inside text-sm text-[var(--color-gray-700)] space-y-1.5 mt-3">
          <li>
            The journal stays in your Xero with status <strong>VOIDED</strong>{" "}
            on the original date — your accountant can still see it for the
            audit trail.
          </li>
          <li>
            The run reverts to &ldquo;not exported&rdquo; in Central so you can
            re-export with corrected data.
          </li>
          <li>
            Voids appear in your Xero Journal Report and can be drilled into to
            see when the void happened.
          </li>
        </ul>
      </Section>

      <Section
        icon={<Shield className="w-5 h-5 text-[var(--color-gray-600)]" />}
        title="Idempotency &amp; retry safety"
      >
        <p className="text-sm text-[var(--color-gray-700)]">
          Every export carries a unique idempotency key Xero uses to dedupe. If
          the network drops mid-request and your client retries, Xero returns
          the original journal — never two.
        </p>
        <p className="text-sm text-[var(--color-gray-700)] mt-2">
          On Central&apos;s side, a database lock per payroll run prevents two
          browser tabs from racing. The combination means you can double-click
          without consequence.
        </p>
      </Section>

      <Section
        icon={<ExternalLink className="w-5 h-5 text-[var(--color-gray-600)]" />}
        title="Rate limits and large companies"
      >
        <p className="text-sm text-[var(--color-gray-700)]">
          Xero allows 60 calls per minute and 5,000 per day per organisation.
          Each Central export is one call. If you have multiple Central
          companies posting to one Xero organisation, they share the same daily
          quota.
        </p>
        <p className="text-sm text-[var(--color-gray-700)] mt-2">
          Bulk-exporting 24 historical runs at once stays well within the
          per-minute cap. Bigger backfills should be split across days.
        </p>
      </Section>

      <Section title="FAQs">
        <dl className="text-sm text-[var(--color-gray-700)] space-y-3">
          <div>
            <dt className="font-semibold">Does Central pull data from Xero?</dt>
            <dd className="text-[var(--color-gray-600)] mt-0.5">
              Only the chart of accounts (so we know what to map to). We
              don&apos;t read invoices, contacts, or banking. We only post
              payroll journals.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">
              What if I have multi-currency in Xero?
            </dt>
            <dd className="text-[var(--color-gray-600)] mt-0.5">
              Today, journals post in your Xero org&apos;s base currency.
              Multi-currency support is on the roadmap — talk to us if it&apos;s
              blocking.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">Is GST handled correctly?</dt>
            <dd className="text-[var(--color-gray-600)] mt-0.5">
              Yes. All payroll lines post as <strong>BAS Excluded</strong>
              (out-of-scope for GST), so your IRAS GST F5 return isn&apos;t
              affected by Central&apos;s journals.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">How do I disconnect?</dt>
            <dd className="text-[var(--color-gray-600)] mt-0.5">
              Settings → Integrations → Xero → Disconnect. Your access token is
              hard-deleted from Central and revoked at Xero&apos;s side. You can
              reconnect at any time.
            </dd>
          </div>
        </dl>
      </Section>
    </div>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon?: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <AppCard className="p-6 space-y-3">
      <div className="flex items-center gap-2.5">
        {icon}
        <h2 className="text-base font-bold text-[var(--color-gray-900)]">
          {title}
        </h2>
      </div>
      <div>{children}</div>
    </AppCard>
  );
}
