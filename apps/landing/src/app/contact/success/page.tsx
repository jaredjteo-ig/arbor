import Link from "next/link";
import type { Metadata } from "next";
import { ArrowLeft, CheckCircle2 } from "lucide-react";

export const metadata: Metadata = {
  title: "Thanks — Central",
  description: "We've received your message and will be in touch shortly.",
};

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

export default function ContactSuccessPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
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

      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12">
        <div className="max-w-md w-full bg-white rounded-2xl border border-gray-200 shadow-sm p-8 md:p-10 text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-green-50 mb-4">
            <CheckCircle2 className="w-7 h-7 text-green-600" />
          </div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
            Thanks — we&apos;ve got your message.
          </h1>
          <p className="text-gray-600 mb-6">
            Someone from the team will be in touch within one business day.
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>
        </div>
      </main>

      <footer className="bg-gray-900 text-gray-400 py-10">
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
