"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import {
  FileText,
  Grid3X3,
  List,
  Search,
  FileSignature,
  BookOpen,
  Mail,
  ClipboardList,
  Shield,
  ChevronRight,
} from "lucide-react";
import {
  AppCard,
  AppButton,
  LoadingState,
  ErrorState,
} from "@/components/design-system";
import { documentsApi } from "@/services/api/documents";
import type { DocumentTemplate } from "@/types/api";

/* ── Constants ───────────────────────────────────────────── */

const CATEGORIES = [
  "All",
  "Contracts",
  "Policies",
  "Letters",
  "Forms",
] as const;

const categoryIcon: Record<string, typeof FileText> = {
  Contracts: FileSignature,
  Policies: BookOpen,
  Letters: Mail,
  Forms: ClipboardList,
};

/* ── Page ────────────────────────────────────────────────── */

export default function DocumentsPage() {
  const [view, setView] = useState<"grid" | "list">("grid");
  const [activeCategory, setActiveCategory] = useState("All");
  const [search, setSearch] = useState("");
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTemplates = () => {
    setLoading(true);
    setError(null);
    documentsApi
      .listTemplates()
      .then((data) => {
        setTemplates(data.templates);
      })
      .catch((err) => {
        setError(
          err instanceof Error ? err.message : "Failed to load templates",
        );
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const filtered = useMemo(() => {
    let results = templates;
    if (activeCategory !== "All") {
      results = results.filter((t) => t.category === activeCategory);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      results = results.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q),
      );
    }
    return results;
  }, [templates, activeCategory, search]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText
            className="h-7 w-7 text-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              Document Templates
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
              EA-compliant templates for employment contracts, policies,
              letters, and forms.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 bg-[var(--color-gray-100)] rounded-lg p-1">
          <button
            onClick={() => setView("grid")}
            className={`p-2 rounded-md transition-colors ${
              view === "grid"
                ? "bg-white text-[var(--color-gray-900)] shadow-sm"
                : "text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"
            }`}
            aria-label="Grid view"
          >
            <Grid3X3 className="h-4 w-4" />
          </button>
          <button
            onClick={() => setView("list")}
            className={`p-2 rounded-md transition-colors ${
              view === "list"
                ? "bg-white text-[var(--color-gray-900)] shadow-sm"
                : "text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]"
            }`}
            aria-label="List view"
          >
            <List className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex gap-2 overflow-x-auto pb-1">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                activeCategory === cat
                  ? "bg-[var(--color-primary)] text-white"
                  : "bg-[var(--color-gray-100)] text-[var(--color-gray-600)] hover:bg-[var(--color-gray-200)]"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
        <div className="flex-1 min-w-0 sm:max-w-xs">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-gray-400)]" />
            <input
              type="text"
              placeholder="Search templates..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-[var(--color-gray-200)] bg-white text-[var(--color-gray-900)] placeholder:text-[var(--color-gray-400)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {/* Loading state */}
      {loading && <LoadingState variant="card" count={6} />}

      {/* Error state */}
      {!loading && error && (
        <ErrorState
          variant="server"
          title="Failed to load templates"
          description={error}
          onRetry={fetchTemplates}
        />
      )}

      {/* Content */}
      {!loading && !error && (
        <>
          {/* Results count */}
          <p className="text-sm text-[var(--color-gray-500)]">
            {filtered.length} template{filtered.length !== 1 ? "s" : ""}
            {activeCategory !== "All" && ` in ${activeCategory}`}
          </p>

          {/* Template grid or list */}
          {filtered.length === 0 ? (
            <AppCard variant="standard">
              <div className="text-center py-8">
                <FileText className="h-10 w-10 text-[var(--color-gray-300)] mx-auto mb-3" />
                <p className="text-[var(--color-gray-500)]">
                  No templates found. Try adjusting your filters.
                </p>
              </div>
            </AppCard>
          ) : view === "grid" ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((t) => (
                <TemplateCard key={t.id} template={t} />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((t) => (
                <TemplateListItem key={t.id} template={t} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ── Grid card ───────────────────────────────────────────── */

function TemplateCard({ template }: { template: DocumentTemplate }) {
  const Icon = categoryIcon[template.category] ?? FileText;

  return (
    <AppCard variant="standard">
      <div className="flex flex-col h-full">
        <div className="flex items-start gap-3 mb-3">
          <div className="p-2 rounded-lg bg-[var(--color-primary-bg)] shrink-0">
            <Icon className="h-5 w-5 text-[var(--color-primary)]" />
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-sm text-[var(--color-gray-900)] line-clamp-2">
              {template.name}
            </h3>
            <span className="text-xs text-[var(--color-gray-500)]">
              {template.category}
            </span>
          </div>
        </div>

        <p className="text-xs text-[var(--color-gray-600)] line-clamp-2 mb-3 flex-1">
          {template.description}
        </p>

        {template.compliance_notes.length > 0 && (
          <div className="flex items-start gap-1.5 mb-3 p-2 rounded-md bg-[var(--color-gray-50)]">
            <Shield className="h-3.5 w-3.5 text-[var(--color-primary)] mt-0.5 shrink-0" />
            <p className="text-xs text-[var(--color-gray-600)] line-clamp-2">
              {template.compliance_notes[0]}
            </p>
          </div>
        )}

        <div className="flex items-center justify-between pt-2 border-t border-[var(--color-gray-100)]">
          <span className="text-xs text-[var(--color-gray-400)]">
            {template.provisions_count} provision
            {template.provisions_count !== 1 ? "s" : ""} linked
          </span>
          <div className="flex gap-2">
            <Link href={`/documents/${template.id}/preview`}>
              <AppButton variant="text" size="sm">
                Preview
              </AppButton>
            </Link>
            <Link href={`/documents/${template.id}/generate`}>
              <AppButton size="sm">Generate</AppButton>
            </Link>
          </div>
        </div>
      </div>
    </AppCard>
  );
}

/* ── List item ───────────────────────────────────────────── */

function TemplateListItem({ template }: { template: DocumentTemplate }) {
  const Icon = categoryIcon[template.category] ?? FileText;

  return (
    <Link href={`/documents/${template.id}/preview`}>
      <AppCard variant="standard">
        <div className="flex items-center gap-4">
          <div className="p-2 rounded-lg bg-[var(--color-primary-bg)] shrink-0">
            <Icon className="h-5 w-5 text-[var(--color-primary)]" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-sm text-[var(--color-gray-900)] truncate">
                {template.name}
              </h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-gray-100)] text-[var(--color-gray-500)] shrink-0">
                {template.category}
              </span>
            </div>
            <p className="text-xs text-[var(--color-gray-500)] truncate mt-0.5">
              {template.description}
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-xs text-[var(--color-gray-400)]">
              {template.provisions_count} provisions
            </span>
            <ChevronRight className="h-4 w-4 text-[var(--color-gray-400)]" />
          </div>
        </div>
      </AppCard>
    </Link>
  );
}
