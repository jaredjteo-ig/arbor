"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, CheckCircle2, Mail, Send } from "lucide-react";

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

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const form = e.currentTarget;
    const formData = new FormData(form);

    try {
      const body = new URLSearchParams();
      formData.forEach((value, key) => {
        body.append(key, value.toString());
      });

      const res = await fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      });

      if (!res.ok) throw new Error(`Submission failed (${res.status})`);
      setSubmitted(true);
      form.reset();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please email us directly.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
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
            Get in touch
          </h1>
          <p className="text-gray-600 leading-relaxed max-w-xl mx-auto">
            Tell us a bit about your team and we&apos;ll show you how Central
            can simplify HR. We typically respond within one business day.
          </p>
        </div>

        {submitted ? (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 md:p-10 text-center">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-green-50 mb-4">
              <CheckCircle2 className="w-7 h-7 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Thanks — we&apos;ve got your message.
            </h2>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              Someone from the team will be in touch shortly. In the meantime,
              feel free to head back to the homepage.
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to home
            </Link>
          </div>
        ) : (
          <form
            name="contact"
            method="POST"
            data-netlify="true"
            data-netlify-honeypot="bot-field"
            onSubmit={handleSubmit}
            className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 md:p-8 space-y-5"
          >
            {/* Hidden Netlify form-name field — required for static-export forms */}
            <input type="hidden" name="form-name" value="contact" />
            {/* Honeypot field for spam protection */}
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
                className="w-full px-4 py-2.5 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-colors text-sm resize-none"
                placeholder="Tell us about your HR needs — payroll, leave, compliance, anything."
              />
            </div>

            {error && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
              <p className="text-xs text-gray-500 leading-relaxed">
                By submitting, you agree we may reach out about your enquiry. We
                won&apos;t share your details.
              </p>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors text-sm"
              >
                {submitting ? "Sending…" : "Send message"}
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>
        )}
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
