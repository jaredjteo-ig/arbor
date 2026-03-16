"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import clsx from "clsx";
import {
  Calculator,
  Shield,
  AlertTriangle,
  FileText,
  BookOpen,
  Loader2,
  SearchX,
} from "lucide-react";
import { useFulltextSearch } from "@/hooks/api/useSearch";
import type { SearchResult } from "@/types/api";

/* ── Types ───────────────────────────────────────────────────── */

interface QuickAction {
  label: string;
  description: string;
  path: string;
  icon: typeof Calculator;
  keywords: string[];
}

export interface SearchResultsProps {
  query: string;
  onClose: () => void;
  onSelect: (path: string) => void;
}

/* ── Quick action definitions ────────────────────────────────── */

const QUICK_ACTIONS: QuickAction[] = [
  {
    label: "Calculators",
    description: "CPF, leave, salary, and more",
    path: "/calculators",
    icon: Calculator,
    keywords: [
      "cpf",
      "calculator",
      "leave",
      "salary",
      "overtime",
      "retrenchment",
      "notice",
    ],
  },
  {
    label: "Compliance",
    description: "Check regulatory compliance status",
    path: "/compliance",
    icon: Shield,
    keywords: [
      "compliance",
      "regulation",
      "tafep",
      "employment act",
      "mom",
      "statutory",
    ],
  },
  {
    label: "Emergency Protocols",
    description: "Workplace incident procedures",
    path: "/emergency",
    icon: AlertTriangle,
    keywords: ["emergency", "incident", "workplace", "safety", "accident"],
  },
  {
    label: "Documents",
    description: "Templates and generated documents",
    path: "/documents",
    icon: FileText,
    keywords: ["document", "template", "letter", "contract", "generate"],
  },
];

const MAX_PER_SECTION = 3;

/* ── Component ───────────────────────────────────────────────── */

export function SearchResults({
  query,
  onClose,
  onSelect,
}: SearchResultsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [kbResults, setKbResults] = useState<SearchResult[]>([]);
  const [kbLoading, setKbLoading] = useState(false);
  const [kbSearched, setKbSearched] = useState(false);

  const fulltextSearch = useFulltextSearch();

  /* ── Match quick actions by keyword ────────────────────────── */

  const lowerQuery = query.toLowerCase().trim();
  const matchedActions = QUICK_ACTIONS.filter((action) =>
    action.keywords.some(
      (kw) => lowerQuery.includes(kw) || kw.includes(lowerQuery),
    ),
  ).slice(0, MAX_PER_SECTION);

  /* ── Debounced KB search ───────────────────────────────────── */

  useEffect(() => {
    if (query.length < 2) {
      setKbResults([]);
      setKbSearched(false);
      return;
    }

    setKbLoading(true);
    const timeout = setTimeout(() => {
      fulltextSearch.mutate(
        { query, page_size: MAX_PER_SECTION },
        {
          onSuccess: (data) => {
            setKbResults(data.results.slice(0, MAX_PER_SECTION));
            setKbLoading(false);
            setKbSearched(true);
          },
          onError: () => {
            setKbResults([]);
            setKbLoading(false);
            setKbSearched(true);
          },
        },
      );
    }, 300);

    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  /* ── Build a flat list of selectable items for keyboard nav ── */

  const selectableItems = useMemo(() => {
    const items: Array<{ type: "action" | "kb"; path: string }> = [];
    for (const action of matchedActions) {
      items.push({ type: "action", path: action.path });
    }
    for (const result of kbResults) {
      items.push({
        type: "kb",
        path: `/advisory?q=${encodeURIComponent(result.title)}`,
      });
    }
    return items;
  }, [matchedActions, kbResults]);

  const totalItems = selectableItems.length;

  /* ── Keyboard navigation ───────────────────────────────────── */

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((prev) => (prev < totalItems - 1 ? prev + 1 : 0));
        return;
      }

      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((prev) => (prev > 0 ? prev - 1 : totalItems - 1));
        return;
      }

      if (e.key === "Enter" && activeIndex >= 0 && activeIndex < totalItems) {
        e.preventDefault();
        onSelect(selectableItems[activeIndex].path);
        return;
      }
    },
    [onClose, onSelect, activeIndex, totalItems, selectableItems],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  /* Reset active index when results change */
  useEffect(() => {
    setActiveIndex(-1);
  }, [query]);

  /* ── Outside click ─────────────────────────────────────────── */

  useEffect(() => {
    function handleOutsideClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [onClose]);

  /* ── Empty state ───────────────────────────────────────────── */

  const showEmpty =
    !kbLoading &&
    kbSearched &&
    kbResults.length === 0 &&
    matchedActions.length === 0;

  /* ── Render ────────────────────────────────────────────────── */

  let itemIndex = -1;

  return (
    <div
      ref={containerRef}
      className={clsx(
        "absolute left-0 right-0 top-full mt-1 z-50",
        "rounded-lg border border-[var(--color-gray-200)]",
        "bg-[var(--color-surface-card)]",
        "shadow-[var(--shadow-raised)]",
        "max-h-[400px] overflow-y-auto",
        "animate-fade-in",
      )}
      role="listbox"
      aria-label="Search results"
    >
      {/* Quick Actions */}
      {matchedActions.length > 0 && (
        <div className="p-2">
          <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-gray-400)]">
            Quick Actions
          </p>
          {matchedActions.map((action) => {
            itemIndex += 1;
            const idx = itemIndex;
            const Icon = action.icon;
            return (
              <button
                key={action.path}
                type="button"
                role="option"
                aria-selected={activeIndex === idx}
                onClick={() => onSelect(action.path)}
                onMouseEnter={() => setActiveIndex(idx)}
                className={clsx(
                  "flex items-center gap-3 w-full rounded-md px-2 py-2 text-left",
                  "min-h-[44px]",
                  "transition-colors duration-100",
                  activeIndex === idx
                    ? "bg-[var(--color-gray-100)]"
                    : "hover:bg-[var(--color-gray-50)]",
                )}
              >
                <div
                  className={clsx(
                    "flex items-center justify-center shrink-0",
                    "w-8 h-8 rounded-md",
                    "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[var(--color-gray-800)] truncate">
                    {action.label}
                  </p>
                  <p className="text-xs text-[var(--color-gray-500)] truncate">
                    {action.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* Divider between sections */}
      {matchedActions.length > 0 && (kbLoading || kbResults.length > 0) && (
        <div
          className="mx-2 border-t border-[var(--color-gray-200)]"
          role="separator"
        />
      )}

      {/* Knowledge Base Results */}
      {(kbLoading || kbResults.length > 0) && (
        <div className="p-2">
          <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-gray-400)]">
            Knowledge Base
          </p>
          {kbLoading ? (
            <div className="space-y-1">
              {Array.from({ length: 2 }).map((_, i) => (
                <SkeletonItem key={i} />
              ))}
            </div>
          ) : (
            kbResults.map((result) => {
              itemIndex += 1;
              const idx = itemIndex;
              return (
                <button
                  key={result.provision_id}
                  type="button"
                  role="option"
                  aria-selected={activeIndex === idx}
                  onClick={() =>
                    onSelect(`/advisory?q=${encodeURIComponent(result.title)}`)
                  }
                  onMouseEnter={() => setActiveIndex(idx)}
                  className={clsx(
                    "flex items-center gap-3 w-full rounded-md px-2 py-2 text-left",
                    "min-h-[44px]",
                    "transition-colors duration-100",
                    activeIndex === idx
                      ? "bg-[var(--color-gray-100)]"
                      : "hover:bg-[var(--color-gray-50)]",
                  )}
                >
                  <div
                    className={clsx(
                      "flex items-center justify-center shrink-0",
                      "w-8 h-8 rounded-md",
                      "bg-[var(--color-secondary)]/10 text-[var(--color-secondary)]",
                    )}
                  >
                    <BookOpen className="h-4 w-4" aria-hidden="true" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-[var(--color-gray-800)] truncate">
                      {result.title}
                    </p>
                    <p className="text-xs text-[var(--color-gray-500)] truncate">
                      {result.act_name} &middot; {result.domain}
                    </p>
                  </div>
                </button>
              );
            })
          )}
        </div>
      )}

      {/* Empty state */}
      {showEmpty && (
        <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
          <SearchX
            className="h-8 w-8 text-[var(--color-gray-300)] mb-2"
            aria-hidden="true"
          />
          <p className="text-sm text-[var(--color-gray-500)]">
            No results for &ldquo;{query}&rdquo;
          </p>
        </div>
      )}

      {/* Loading-only state (no quick actions matched, KB still loading) */}
      {kbLoading && matchedActions.length === 0 && (
        <div className="flex items-center justify-center py-6">
          <Loader2
            className="h-5 w-5 text-[var(--color-gray-400)] animate-spin"
            aria-hidden="true"
          />
          <span className="ml-2 text-sm text-[var(--color-gray-500)]">
            Searching...
          </span>
        </div>
      )}
    </div>
  );
}

/* ── Skeleton item for loading state ─────────────────────────── */

function SkeletonItem() {
  return (
    <div className="flex items-center gap-3 px-2 py-2 min-h-[44px]">
      <div className="w-8 h-8 rounded-md bg-[var(--color-gray-200)] animate-pulse shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3.5 w-3/4 rounded bg-[var(--color-gray-200)] animate-pulse" />
        <div className="h-3 w-1/2 rounded bg-[var(--color-gray-100)] animate-pulse" />
      </div>
    </div>
  );
}
