"use client";

import { useState } from "react";
import Link from "next/link";
import {
  HelpCircle,
  ChevronDown,
  ChevronUp,
  BookOpen,
  ArrowRight,
  MessageSquare,
  Shield,
  Calculator,
  FileText,
  AlertTriangle,
  Bell,
  Users,
  Search,
  AlertCircle,
} from "lucide-react";
import { AppCard, AppButton } from "@/components/design-system";
import { useHelpArticles, useGettingStarted } from "@/hooks/api/useHelp";
import type { HelpArticle, GettingStartedStep } from "@/types/api";

/* ── Category icon mapping ──────────────────────────────────── */

const CATEGORY_ICONS: Record<string, typeof HelpCircle> = {
  Advisory: MessageSquare,
  Calculators: Calculator,
  Compliance: Shield,
  Documents: FileText,
  Alerts: Bell,
  Emergency: AlertTriangle,
  "Getting Started": BookOpen,
  "Account & Security": Users,
};

/* ── Loading skeleton ────────────────────────────────────────── */

function HelpSkeleton() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-7 w-7 rounded bg-[var(--color-gray-200)] animate-pulse" />
        <div className="space-y-2">
          <div className="h-6 w-24 rounded bg-[var(--color-gray-200)] animate-pulse" />
          <div className="h-4 w-64 rounded bg-[var(--color-gray-200)] animate-pulse" />
        </div>
      </div>
      <div className="h-48 rounded-xl bg-[var(--color-gray-200)] animate-pulse" />
      {[1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className="h-16 rounded-xl bg-[var(--color-gray-200)] animate-pulse"
        />
      ))}
    </div>
  );
}

/* ── FAQ Accordion Item ──────────────────────────────────────── */

function FaqItem({ article }: { article: HelpArticle }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <AppCard variant="standard" className="transition-shadow">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] rounded-lg"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              {article.title}
            </h3>
          </div>
          <div className="shrink-0">
            {isOpen ? (
              <ChevronUp className="h-4 w-4 text-[var(--color-gray-400)]" />
            ) : (
              <ChevronDown className="h-4 w-4 text-[var(--color-gray-400)]" />
            )}
          </div>
        </div>
      </button>
      {isOpen && (
        <div className="mt-3 pt-3 border-t border-[var(--color-gray-200)]">
          <p className="text-sm text-[var(--color-gray-700)] leading-relaxed whitespace-pre-line">
            {article.content}
          </p>
        </div>
      )}
    </AppCard>
  );
}

/* ── Getting Started Card ────────────────────────────────────── */

function GettingStartedCard({ step }: { step: GettingStartedStep }) {
  return (
    <div className="flex items-start gap-4">
      <div
        className="flex items-center justify-center w-8 h-8 rounded-full shrink-0 text-sm font-bold text-white"
        style={{ backgroundColor: "var(--color-primary)" }}
      >
        {step.step_number}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
          {step.title}
        </h3>
        <p className="text-sm text-[var(--color-gray-600)] mt-1 leading-relaxed">
          {step.description}
        </p>
        <Link
          href={step.action_path}
          className="inline-flex items-center gap-1 mt-2 text-xs font-semibold text-[var(--color-primary)] hover:underline"
        >
          {step.action_label}
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────── */

export default function HelpPage() {
  const {
    data: articlesData,
    isPending: articlesLoading,
    error: articlesError,
  } = useHelpArticles();
  const {
    data: gettingStartedData,
    isPending: gsLoading,
    error: gsError,
  } = useGettingStarted();

  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const isPending = articlesLoading || gsLoading;
  const error = articlesError || gsError;

  if (isPending) return <HelpSkeleton />;

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <AppCard variant="standard">
          <div className="text-center py-8">
            <AlertCircle className="h-10 w-10 text-red-400 mx-auto mb-3" />
            <p className="text-[var(--color-gray-700)] font-medium">
              Unable to load help content
            </p>
            <p className="text-sm text-[var(--color-gray-500)] mt-1">
              {error.message}
            </p>
          </div>
        </AppCard>
      </div>
    );
  }

  const articles = articlesData?.articles ?? [];
  const categories = articlesData?.categories ?? [];
  const gettingStarted = gettingStartedData;

  // Filter articles by category and search
  let filteredArticles = articles;
  if (activeCategory) {
    filteredArticles = filteredArticles.filter(
      (a) => a.category === activeCategory,
    );
  }
  if (searchQuery.trim()) {
    const query = searchQuery.toLowerCase();
    filteredArticles = filteredArticles.filter(
      (a) =>
        a.title.toLowerCase().includes(query) ||
        a.content.toLowerCase().includes(query),
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <HelpCircle
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Help Centre
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Learn how to use Central effectively for your HR compliance needs.
          </p>
        </div>
      </div>

      {/* Getting Started section */}
      {gettingStarted && (
        <AppCard variant="elevated">
          <div className="flex items-center gap-2 mb-2">
            <BookOpen
              className="h-5 w-5 text-[var(--color-primary)]"
              aria-hidden="true"
            />
            <h2 className="text-lg font-bold text-[var(--color-gray-900)]">
              {gettingStarted.title}
            </h2>
          </div>
          <p className="text-sm text-[var(--color-gray-600)] mb-6 leading-relaxed">
            {gettingStarted.introduction}
          </p>
          <div className="space-y-6">
            {gettingStarted.steps.map((step) => (
              <GettingStartedCard key={step.step_number} step={step} />
            ))}
          </div>
        </AppCard>
      )}

      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-gray-400)]" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search help articles..."
          className="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-[var(--color-gray-200)] bg-white text-[var(--color-gray-700)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent"
        />
      </div>

      {/* Category filter pills */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setActiveCategory(null)}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            activeCategory === null
              ? "bg-[var(--color-primary)] text-white"
              : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:bg-[var(--color-gray-200)]"
          }`}
        >
          All Topics
        </button>
        {categories.map((cat) => {
          const CatIcon = CATEGORY_ICONS[cat] ?? HelpCircle;
          return (
            <button
              key={cat}
              onClick={() =>
                setActiveCategory(activeCategory === cat ? null : cat)
              }
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                activeCategory === cat
                  ? "bg-[var(--color-primary)] text-white"
                  : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:bg-[var(--color-gray-200)]"
              }`}
            >
              <CatIcon className="h-3.5 w-3.5" />
              {cat}
            </button>
          );
        })}
      </div>

      {/* FAQ Articles */}
      {filteredArticles.length === 0 ? (
        <AppCard variant="standard">
          <div className="text-center py-8">
            <Search className="h-10 w-10 text-[var(--color-gray-300)] mx-auto mb-3" />
            <p className="text-[var(--color-gray-500)]">
              No articles match your search. Try different keywords or clear
              your filters.
            </p>
          </div>
        </AppCard>
      ) : (
        <div className="space-y-3">
          {/* Group by category if no specific category selected */}
          {activeCategory === null && !searchQuery.trim()
            ? categories.map((cat) => {
                const catArticles = filteredArticles.filter(
                  (a) => a.category === cat,
                );
                if (catArticles.length === 0) return null;
                const CatIcon = CATEGORY_ICONS[cat] ?? HelpCircle;
                return (
                  <div key={cat} className="space-y-2">
                    <div className="flex items-center gap-2 pt-2">
                      <CatIcon className="h-4 w-4 text-[var(--color-primary)]" />
                      <h3 className="text-sm font-semibold text-[var(--color-gray-700)] uppercase tracking-wider">
                        {cat}
                      </h3>
                    </div>
                    {catArticles.map((article) => (
                      <FaqItem key={article.id} article={article} />
                    ))}
                  </div>
                );
              })
            : filteredArticles.map((article) => (
                <FaqItem key={article.id} article={article} />
              ))}
        </div>
      )}

      {/* Contact section */}
      <AppCard variant="standard">
        <div className="text-center py-4">
          <h3 className="text-base font-bold text-[var(--color-gray-900)] mb-2">
            Still need help?
          </h3>
          <p className="text-sm text-[var(--color-gray-600)] mb-4">
            If you cannot find what you are looking for, ask Central directly in
            the Advisory chat or contact our support team.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/advisory">
              <AppButton variant="primary" size="md">
                <MessageSquare className="h-4 w-4" />
                Ask Central
              </AppButton>
            </Link>
            <a href="mailto:support@arbor.terrene.dev">
              <AppButton variant="outlined" size="md">
                Contact Support
              </AppButton>
            </a>
          </div>
        </div>
      </AppCard>

      <p className="text-xs text-[var(--color-gray-400)] text-center pb-4">
        {articles.length} help articles available
      </p>
    </div>
  );
}
