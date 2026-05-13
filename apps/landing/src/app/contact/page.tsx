"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, Mail, Send } from "lucide-react";

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

/* Intent-aware copy. /contact?intent=demo from the hero/book-a-demo
   CTA. /contact?tier=growth from the pricing page. Both are opt-in —
   direct /contact still shows the neutral "Get in touch" variant.

   This is a client component because the landing app is statically
   exported (output: 'export') — server-side `searchParams` would
   force dynamic rendering, which Netlify static hosting doesn't
   support. `useSearchParams` reads the URL on the client at hydration. */

interface IntentCopy {
  heading: string;
  subhead: string;
  messageDefault: string;
  formIntent: string;
}

function copyForIntent(intent: string | null, tier: string | null): IntentCopy {
  if (intent === "demo") {
    return {
      heading: "Book a demo",
      subhead:
        "Tell us about your team and we’ll walk you through a real Singapore payroll cycle — CPF, IR8A, leave, and the AI advisory. Typically scheduled within one business day.",
      messageDefault:
        "We’re a Singapore-based team with about <X> employees. We’d love to see how Central handles payroll + compliance.",
      formIntent: "demo",
    };
  }
  if (tier) {
    const tierTitle =
      tier.charAt(0).toUpperCase() + tier.slice(1).toLowerCase();
    return {
      heading: `Talk to sales — ${tierTitle} plan`,
      subhead:
        "Tell us a bit about your team and we’ll prepare a quote tailored to your size and integrations.",
      messageDefault: `Interested in the ${tierTitle} plan. Our team size is approximately ___.`,
      formIntent: `pricing:${tier.toLowerCase()}`,
    };
  }
  return {
    heading: "Get in touch",
    subhead:
      "Tell us a bit about your team and we’ll show you how Central can simplify HR. We typically respond within one business day.",
    messageDefault: "",
    formIntent: "general",
  };
}

function ContactPageInner() {
  const searchParams = useSearchParams();
  const intent = searchParams.get("intent");
  const tier = searchParams.get("tier");
  const { heading, subhead, messageDefault, formIntent } = copyForIntent(
    intent,
    tier,
  );

  return (
    <div className="min-h-screen bg-gray-50">
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

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-12 md:py-16">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-50 mb-4">
            <Mail className="w-6 h-6 text-blue-600" />
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3">
            {heading}
          </h1>
          <p className="text-gray-600 leading-relaxed max-w-xl mx-auto">
            {subhead}
          </p>
        </div>

        <form
          name="contact"
          method="POST"
          action="/contact/success"
          data-netlify="true"
          data-netlify-honeypot="bot-field"
          className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 md:p-8 space-y-5"
        >
          {/* Required hidden field — tells Netlify which form this is */}
          <input type="hidden" name="form-name" value="contact" />
          {/* Captures the inbound intent (demo / pricing tier / general)
              so sales can route faster. P4-LP-1. */}
          <input type="hidden" name="intent" value={formIntent} />
          {/* Honeypot field — bots fill this in, humans never see it */}
          <p className="hidden">
            <label>
              Don&apos;t fill this out if you&apos;re human:{" "}
              <input name="bot-field" />
            </label>
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-medium text-gray-700 mb-1.5"
              >
                Your name <span className="text-red-500">*</span>
              </label>
              <input
                id="name"
                name="name"
                type="text"
                required
                autoComplete="name"
                className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-colors text-sm"
                placeholder="Jane Tan"
              />
            </div>
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700 mb-1.5"
              >
                Work email <span className="text-red-500">*</span>
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                autoComplete="email"
                className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-colors text-sm"
                placeholder="jane@company.sg"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label
                htmlFor="company"
                className="block text-sm font-medium text-gray-700 mb-1.5"
              >
                Company
              </label>
              <input
                id="company"
                name="company"
                type="text"
                autoComplete="organization"
                className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-colors text-sm"
                placeholder="Your company"
              />
            </div>
            <div>
              <label
                htmlFor="team_size"
                className="block text-sm font-medium text-gray-700 mb-1.5"
              >
                Team size
              </label>
              <select
                id="team_size"
                name="team_size"
                defaultValue=""
                className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-colors text-sm bg-white"
              >
                <option value="" disabled>
                  Select team size
                </option>
                <option value="1-10">1–10</option>
                <option value="11-50">11–50</option>
                <option value="51-200">51–200</option>
                <option value="201+">201+</option>
              </select>
            </div>
          </div>

          <div>
            <label
              htmlFor="message"
              className="block text-sm font-medium text-gray-700 mb-1.5"
            >
              What can we help with? <span className="text-red-500">*</span>
            </label>
            <textarea
              id="message"
              name="message"
              required
              rows={5}
              defaultValue={messageDefault}
              className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-colors text-sm resize-none"
              placeholder="Tell us about your HR needs — payroll, leave, compliance, anything."
            />
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
            <p className="text-xs text-gray-500 leading-relaxed">
              By submitting, you agree we may reach out about your enquiry. We
              won&apos;t share your details.
            </p>
            <button
              type="submit"
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors text-sm"
            >
              Send message
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>
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

/* Suspense boundary is required by Next.js for client components
   that call useSearchParams() under static export. The fallback
   renders the neutral copy so the page never flickers blank. */
export default function ContactPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <p className="text-sm text-gray-500">Loading…</p>
        </div>
      }
    >
      <ContactPageInner />
    </Suspense>
  );
}
