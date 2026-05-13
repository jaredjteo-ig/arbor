"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Menu,
  X,
  ArrowRight,
  Shield,
  Sparkles,
  Calculator,
  FileText,
  BookOpen,
  Scale,
  ShieldCheck,
  Lock,
  MapPin,
  FileCheck2,
  Quote,
} from "lucide-react";
import { ManagementShowcase } from "@/components/management/ManagementShowcase";

/* ── Inline logo used in the top nav ─────────────────────── */

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

/* ── Top navigation header ───────────────────────────────── */

function LandingNav() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-4 sm:px-6 h-16">
        <Link href="/" aria-label="Central Home">
          <ArborLogo />
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          <a
            href="#features"
            className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            Features
          </a>
          <a
            href="#compliance"
            className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            Compliance
          </a>
          <a
            href="#advisory"
            className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            AI Advisory
          </a>
          <Link
            href="/pricing"
            className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
          >
            Pricing
          </Link>
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/contact"
            className="text-sm font-semibold text-gray-600 hover:text-gray-900 transition-colors"
          >
            Contact
          </Link>
          <Link
            href="/contact?intent=demo"
            className="text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 px-4 py-2.5 rounded-xl transition-colors inline-flex items-center gap-1.5"
          >
            Book a demo
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <button
          type="button"
          className="md:hidden p-2 text-gray-600 hover:text-gray-900"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
        >
          {mobileOpen ? (
            <X className="h-6 w-6" />
          ) : (
            <Menu className="h-6 w-6" />
          )}
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white px-4 py-4 space-y-3">
          <a
            href="#features"
            className="block text-sm font-medium text-gray-700 py-2"
            onClick={() => setMobileOpen(false)}
          >
            Features
          </a>
          <a
            href="#compliance"
            className="block text-sm font-medium text-gray-700 py-2"
            onClick={() => setMobileOpen(false)}
          >
            Compliance
          </a>
          <a
            href="#advisory"
            className="block text-sm font-medium text-gray-700 py-2"
            onClick={() => setMobileOpen(false)}
          >
            AI Advisory
          </a>
          <Link
            href="/pricing"
            className="block text-sm font-medium text-gray-700 py-2"
            onClick={() => setMobileOpen(false)}
          >
            Pricing
          </Link>
          <div className="pt-2 border-t border-gray-100 flex flex-col gap-2">
            <Link
              href="/contact?intent=demo"
              className="text-center text-sm font-semibold text-white bg-blue-600 px-4 py-2.5 rounded-xl"
              onClick={() => setMobileOpen(false)}
            >
              Book a demo
            </Link>
            <Link
              href="/contact"
              className="text-center text-sm font-medium text-gray-600 py-2"
              onClick={() => setMobileOpen(false)}
            >
              Contact us
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

/* ── Hero ────────────────────────────────────────────────── */
/* Above-the-fold landing. Primary CTA is Book a Demo; secondary
   is the existing /contact form. Copy emphasises Singapore HR +
   deterministic-payroll + cited-advisory — the three differentiators. */

function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-blue-50/50 via-white to-white pt-12 pb-10 md:pt-20 md:pb-16">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-semibold mb-6">
          <Sparkles className="w-3.5 h-3.5" />
          Built for Singapore SMEs
        </div>
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 leading-tight tracking-tight mb-5">
          HR, payroll & compliance —
          <br />
          <span className="bg-gradient-to-r from-blue-600 to-violet-600 bg-clip-text text-transparent">
            done the Singapore way.
          </span>
        </h1>
        <p className="max-w-2xl mx-auto text-base md:text-lg text-gray-600 leading-relaxed mb-8">
          One platform for CPF, IR8A, leave, claims, and 6-domain compliance
          checks. Deterministic payroll. AI advisory grounded in the Employment
          Act. No expensive consultants.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-3">
          <Link
            href="/contact?intent=demo"
            className="inline-flex items-center gap-2 px-7 py-3.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-all shadow-lg shadow-blue-600/20 text-base"
          >
            Book a demo
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/pricing"
            className="inline-flex items-center gap-2 px-7 py-3.5 bg-white text-gray-900 font-semibold rounded-xl border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all text-base"
          >
            See pricing
          </Link>
        </div>
        <p className="text-xs text-gray-500">
          We typically respond within one business day. No credit card needed.
        </p>
      </div>
    </section>
  );
}

/* ── Trust Strip ─────────────────────────────────────────── */
/* Five trust signals. Every claim must be true today — no
   unaudited certifications. Mirrors the in-product PDPA +
   'no AI in payroll math' + cited-advisory taglines. */

function TrustStrip() {
  const signals = [
    {
      icon: Lock,
      title: "PDPA-compliant",
      body: "PII encrypted at rest. Accessed only for HR and payroll purposes.",
    },
    {
      icon: MapPin,
      title: "Singapore-hosted",
      body: "Data centre in Singapore. No data leaves the region.",
    },
    {
      icon: FileCheck2,
      title: "Statutory files",
      body: "CPF e-Submit, Bank GIRO, IR8A and IR21 generated to Board formats.",
    },
    {
      icon: Calculator,
      title: "No AI in payroll math",
      body: "Deterministic calculations. AI only for advisory + compliance Q&A.",
    },
    {
      icon: Quote,
      title: "Cited advisory",
      body: "Every answer cites the underlying EA, CPF, EFMA or IRAS provision.",
    },
  ];

  return (
    <section className="py-12 bg-white border-y border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 md:gap-4">
          {signals.map(({ icon: Icon, title, body }) => (
            <div key={title} className="flex flex-col items-start gap-2 px-2">
              <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                <Icon className="w-4 h-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{title}</p>
                <p className="text-xs text-gray-500 leading-relaxed mt-0.5">
                  {body}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── Compliance preview section ──────────────────────────── */

const SAMPLE_DOMAINS = [
  { name: "Employment Act", covered: true },
  { name: "Central Provident Fund (CPF)", covered: true },
  { name: "Foreign Manpower (EFMA)", covered: false },
  { name: "Workplace Safety & Health (WSH)", covered: false },
  { name: "Tax / IRAS", covered: true },
  { name: "TAFEP Guidelines", covered: true },
];

function ComplianceSection() {
  return (
    <section id="compliance" className="py-16 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-red-50 text-red-700 rounded-full text-sm font-medium mb-4">
              <Shield className="w-4 h-4" />
              6-Domain Compliance
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
              Stay Ahead of Singapore Regulations
            </h2>
            <p className="text-gray-600 leading-relaxed mb-6">
              Automated compliance health checks across Employment Act, CPF,
              EFMA, WSH, TAFEP, and Tax/IRAS. Get risk-tiered findings with
              remediation guidance before gaps become fines.
            </p>
            <Link
              href="/contact"
              className="inline-flex items-center gap-2 text-blue-600 font-semibold hover:text-blue-700 transition-colors"
            >
              Talk to us about a compliance check
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
            <div className="flex items-center gap-2 mb-5">
              <ShieldCheck className="h-5 w-5 text-blue-600" />
              <span className="text-sm font-semibold text-gray-900">
                Compliance at a Glance
              </span>
              <span className="text-[10px] font-medium uppercase tracking-wider text-gray-500 bg-gray-100 rounded-full px-2 py-0.5">
                Example
              </span>
            </div>
            <div className="space-y-3">
              {SAMPLE_DOMAINS.map((domain) => (
                <div
                  key={domain.name}
                  className="flex items-center justify-between py-2 border-b border-gray-50 last:border-b-0"
                >
                  <span className="text-sm text-gray-700">{domain.name}</span>
                  <span
                    className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${
                      domain.covered
                        ? "bg-green-50 text-green-700"
                        : "bg-amber-50 text-amber-700"
                    }`}
                  >
                    {domain.covered ? "Covered" : "Needs Review"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ── AI Advisory preview section ─────────────────────────── */

function AdvisorySection() {
  return (
    <section id="advisory" className="py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 order-2 lg:order-1">
            <div className="flex items-center gap-2 mb-5">
              <Sparkles className="h-5 w-5 text-blue-600" />
              <span className="text-sm font-semibold text-gray-900">
                AI-Powered Advisory
              </span>
              <span className="text-[10px] font-medium uppercase tracking-wider text-gray-500 bg-gray-100 rounded-full px-2 py-0.5">
                Example
              </span>
            </div>

            <div className="rounded-lg bg-gray-50 p-4 mb-4">
              <p className="text-xs font-medium text-gray-500 mb-1">Question</p>
              <p className="text-sm text-gray-800">
                What are the notice period requirements for employees under the
                Employment Act?
              </p>
            </div>

            <div className="rounded-lg border border-gray-200 p-4">
              <p className="text-xs font-medium text-gray-500 mb-1">Answer</p>
              <p className="text-sm text-gray-700 leading-relaxed">
                Under Part II of the Employment Act, notice periods depend on
                the length of service. For employees with less than 26 weeks,
                the notice period is 1 day...
              </p>
              <div className="flex flex-wrap gap-1.5 mt-3">
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-700 bg-blue-50 rounded-full px-2.5 py-0.5">
                  <BookOpen className="h-3 w-3" />
                  EA Part II
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-700 bg-blue-50 rounded-full px-2.5 py-0.5">
                  <Scale className="h-3 w-3" />
                  Section 10
                </span>
              </div>
            </div>
          </div>

          <div className="order-1 lg:order-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm font-medium mb-4">
              <Sparkles className="w-4 h-4" />
              AI Compliance Advisor
            </div>
            <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
              Answers Grounded in Singapore Employment Law
            </h2>
            <p className="text-gray-600 leading-relaxed mb-6">
              Ask any HR question and get instant answers with source citations
              from the Employment Act, CPF Act, EFMA, WSH Act, TAFEP guidelines,
              and IRAS regulations. No more Googling, no more guessing.
            </p>
            <div className="space-y-3">
              {[
                {
                  icon: Calculator,
                  text: "Deterministic CPF & payroll calculations",
                },
                {
                  icon: FileText,
                  text: "Source-cited answers from 6 regulatory domains",
                },
                {
                  icon: Shield,
                  text: "Compliance gap detection with remediation steps",
                },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.text} className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                      <Icon className="w-4 h-4 text-blue-600" />
                    </div>
                    <span className="text-sm text-gray-700">{item.text}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ── Bottom CTA ──────────────────────────────────────────── */

function BottomCta() {
  return (
    <section className="py-16 bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-700 text-white">
      <div className="max-w-3xl mx-auto text-center px-4 sm:px-6">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">
          Ready to simplify your HR?
        </h2>
        <p className="text-lg text-white/80 mb-8 max-w-xl mx-auto">
          See Central running on a real Singapore payroll cycle in a 30-minute
          call. We&apos;ll show CPF, IR8A, leave, and the AI advisory in your
          own browser.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/contact?intent=demo"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-blue-700 font-semibold rounded-xl hover:bg-white/90 transition-all shadow-lg"
          >
            Book a demo
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/pricing"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/15 transition-all"
          >
            See pricing
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ── Footer ──────────────────────────────────────────────── */

function LandingFooter() {
  return (
    <footer className="bg-gray-900 text-gray-400 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center rounded-lg bg-white/10 text-white font-bold w-8 h-8 text-xs tracking-tight">
              HR
            </div>
            <span className="text-white font-semibold">Central</span>
            <span className="text-sm text-gray-500 ml-2">
              HR Advisory Platform
            </span>
          </div>
          <p className="text-sm text-gray-500">
            Covering Employment Act, CPF, EFMA, WSH, TAFEP, and Tax/IRAS
            regulations
          </p>
        </div>
      </div>
    </footer>
  );
}

/* ── Page Component ──────────────────────────────────────── */

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <LandingNav />

      <Hero />
      <TrustStrip />

      <main id="features" className="py-8 px-4 sm:px-6">
        <ManagementShowcase />
      </main>

      <ComplianceSection />
      <AdvisorySection />
      <BottomCta />
      <LandingFooter />
    </div>
  );
}
