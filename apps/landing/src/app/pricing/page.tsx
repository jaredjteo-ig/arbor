import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Sparkles,
  Users,
  Building2,
} from "lucide-react";

/* ── Logo (shared with the landing nav) ──────────────────── */

function ArborLogo() {
  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center justify-center rounded-lg bg-blue-600 text-white font-bold w-9 h-9 text-sm tracking-tight">
        HR
      </div>
      <span className="text-xl font-bold text-gray-900">Central</span>
    </div>
  );
}

/* ── Tier matrix ─────────────────────────────────────────── */
/* No $ figures published. Each tier links to /contact?tier=X
   which renders a sales-routing variant of the contact form
   (P4-LP-3). Path A from the brief — Path B (published bands)
   ships only after 3+ paying customers stabilise the cost model. */

interface Tier {
  id: "starter" | "growth" | "enterprise";
  icon: typeof Sparkles;
  name: string;
  band: string;
  pitch: string;
  features: string[];
  ctaLabel: string;
  featured?: boolean;
}

const TIERS: Tier[] = [
  {
    id: "starter",
    icon: Sparkles,
    name: "Starter",
    band: "Up to 50 employees",
    pitch:
      "Everything a Singapore SME needs to run payroll, leave and compliance — without consultants.",
    features: [
      "Deterministic CPF, SDL, FWL & SHG payroll",
      "CPF e-Submit + Bank GIRO file generation",
      "Leave & claims with manager approval",
      "AI advisory grounded in the Employment Act",
      "6-domain compliance health check",
      "PDPA-compliant data handling",
    ],
    ctaLabel: "Talk to sales",
  },
  {
    id: "growth",
    icon: Users,
    name: "Growth",
    band: "51 – 200 employees",
    pitch:
      "Everything in Starter, plus accounting + workforce analytics for the team beyond their first 50.",
    features: [
      "Everything in Starter",
      "Xero ManualJournal export (QBO + Zoho on request)",
      "Workforce analytics & lifecycle dashboard",
      "Bulk payroll & multi-period exports",
      "Mapping health monitoring",
      "Priority email support",
    ],
    ctaLabel: "Talk to sales",
    featured: true,
  },
  {
    id: "enterprise",
    icon: Building2,
    name: "Enterprise",
    band: "201+ employees",
    pitch:
      "Built for groups, multi-entity orgs, and HR teams that need an SLA — not a Slack message.",
    features: [
      "Everything in Growth",
      "Dedicated customer success manager",
      "Custom SLA & uptime commitments",
      "Multi-entity / multi-currency support (roadmap)",
      "Custom integrations & SSO",
      "Quarterly compliance reviews",
    ],
    ctaLabel: "Talk to sales",
  },
];

/* ── FAQ ────────────────────────────────────────────────── */

const FAQ = [
  {
    q: "Why don’t you publish prices?",
    a: "Singapore SMEs vary widely on integrations, headcount mix (foreign workers, multi-entity, contractors) and required SLAs. We want to quote what you actually need rather than a list price that double-counts. Most decisions take one 30-minute call.",
  },
  {
    q: "Is there a free trial?",
    a: "Yes — every plan includes a 14-day trial. No credit card. We seed a test company with a SG-shaped employee mix so you can run a payroll cycle, generate CPF + IR8A files, and ask the advisory anything before signing.",
  },
  {
    q: "Where is my data hosted?",
    a: "Singapore (AP-Southeast-1). PII is encrypted at rest using Fernet keys you control. No data leaves the region. The advisory model itself runs on AWS Bedrock in-region — no cross-border calls.",
  },
  {
    q: "How does payroll math get audited?",
    a: "Every calculation is deterministic — no AI in the math path. Each payroll run produces an audit trail (calculation inputs, statutory rates applied, output payslips) that a human can re-verify line-by-line.",
  },
];

/* ── Page ───────────────────────────────────────────────── */

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-4 sm:px-6 h-16">
          <Link href="/" aria-label="Central Home">
            <ArborLogo />
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-12 md:py-16">
        {/* Heading */}
        <div className="text-center mb-12 md:mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-semibold mb-5">
            Pricing
          </div>
          <h1 className="text-3xl md:text-5xl font-bold text-gray-900 mb-4 tracking-tight">
            Priced to your team, not a list.
          </h1>
          <p className="text-base md:text-lg text-gray-600 max-w-2xl mx-auto leading-relaxed">
            Three plans built for Singapore SMEs. Tell us your team size and
            integration mix — we’ll quote what you actually need.
          </p>
        </div>

        {/* Tier cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          {TIERS.map((tier) => {
            const Icon = tier.icon;
            return (
              <div
                key={tier.id}
                className={
                  tier.featured
                    ? "relative rounded-2xl border-2 border-blue-600 bg-white shadow-xl p-6 md:p-7 flex flex-col"
                    : "relative rounded-2xl border border-gray-200 bg-white shadow-sm p-6 md:p-7 flex flex-col"
                }
              >
                {tier.featured && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-blue-600 text-white text-xs font-semibold rounded-full">
                    Most common
                  </span>
                )}
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-lg font-bold text-gray-900">
                      {tier.name}
                    </p>
                    <p className="text-xs text-gray-500">{tier.band}</p>
                  </div>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed mb-5">
                  {tier.pitch}
                </p>
                <ul className="space-y-2.5 mb-6 flex-1">
                  {tier.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-sm text-gray-700"
                    >
                      <Check className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
                <Link
                  href={`/contact?tier=${tier.id}`}
                  className={
                    tier.featured
                      ? "inline-flex items-center justify-center gap-2 px-5 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors text-sm"
                      : "inline-flex items-center justify-center gap-2 px-5 py-3 bg-gray-900 text-white font-semibold rounded-xl hover:bg-gray-800 transition-colors text-sm"
                  }
                >
                  {tier.ctaLabel}
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            );
          })}
        </div>

        {/* FAQ */}
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-8 text-center">
            Common questions
          </h2>
          <dl className="space-y-6">
            {FAQ.map(({ q, a }) => (
              <div
                key={q}
                className="rounded-xl border border-gray-200 bg-white p-5"
              >
                <dt className="text-base font-semibold text-gray-900 mb-2">
                  {q}
                </dt>
                <dd className="text-sm text-gray-600 leading-relaxed">{a}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Bottom CTA */}
        <div className="mt-16 text-center bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-700 rounded-2xl p-8 md:p-10 text-white">
          <h2 className="text-2xl md:text-3xl font-bold mb-3">
            Still deciding?
          </h2>
          <p className="text-white/85 max-w-xl mx-auto mb-6 leading-relaxed">
            Book a 30-minute walkthrough. We’ll show Central running on a real
            Singapore payroll cycle — and recommend the plan that fits.
          </p>
          <Link
            href="/contact?intent=demo"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-blue-700 font-semibold rounded-xl hover:bg-white/90 transition-colors text-sm shadow-lg"
          >
            Book a demo
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </main>

      <footer className="bg-gray-900 text-gray-400 py-10 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center rounded-lg bg-white/10 text-white font-bold w-8 h-8 text-xs tracking-tight">
              HR
            </div>
            <span className="text-white font-semibold">Central</span>
          </div>
          <p className="text-sm text-gray-500">
            HR Advisory Platform · Singapore
          </p>
        </div>
      </footer>
    </div>
  );
}
