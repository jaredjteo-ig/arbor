"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Check,
  ExternalLink,
  RotateCcw,
  User,
  Calendar,
  DollarSign,
  Clock,
} from "lucide-react";
import clsx from "clsx";
import type { ShadowResponse } from "@/services/api/shadow";
import { shadowApi } from "@/services/api/shadow";

/* ── Constants ────────────────────────────────────────────── */

const UNDO_WINDOW_MS = 8_000;

/* ── Types ────────────────────────────────────────────────── */

interface ArborResultProps {
  /** The execution result from /shadow/confirm. */
  response: ShadowResponse;
  /** Whether to show the undo toast. */
  showUndo?: boolean;
}

/* ── Module icon mapping ─────────────────────────────────── */

const MODULE_ICONS: Record<string, React.FC<{ className?: string }>> = {
  employees: User,
  leave: Calendar,
  payroll: DollarSign,
  attendance: Clock,
};

/* ── Component ────────────────────────────────────────────── */

/**
 * ArborResult (T472)
 *
 * Displays execution results with Arbor identity styling,
 * navigation links, data cards, and an 8-second undo toast.
 */
export function ArborResult({ response, showUndo = true }: ArborResultProps) {
  const router = useRouter();
  const module = response.intent?.module ?? "";
  const action = response.intent?.action ?? "";
  const sessionId = response.session_id;
  const isUndoable = response.session?.is_undoable ?? false;
  const success = response.success !== false;

  const [undoRemaining, setUndoRemaining] = useState(
    showUndo && isUndoable ? UNDO_WINDOW_MS / 1000 : 0,
  );
  const [undoActive, setUndoActive] = useState(showUndo && isUndoable);
  const [undoMessage, setUndoMessage] = useState("");

  // ── Undo countdown (8 seconds) ─────────────────────────
  useEffect(() => {
    if (!undoActive) return;

    const interval = setInterval(() => {
      setUndoRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setUndoActive(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [undoActive]);

  const handleUndo = useCallback(async () => {
    if (!sessionId) return;
    try {
      const result = await shadowApi.undo(sessionId);
      setUndoActive(false);
      setUndoMessage(result.message);
    } catch {
      setUndoMessage("Central: Could not undo this action.");
    }
  }, [sessionId]);

  // Extract navigation link from response data
  const navigationRoute = response.data?.navigation as string | undefined;
  const ModuleIcon = MODULE_ICONS[module] ?? Check;

  // Clean message by removing "Arbor: " prefix for display
  const displayMessage = (response.message ?? "").replace(/^Arbor:\s*/i, "");

  return (
    <div className="space-y-3">
      {/* ── Result card ──────────────────────────────────── */}
      <div
        className={clsx(
          "rounded-xl border px-4 py-3 space-y-2",
          success
            ? "border-[var(--color-primary)]/20 bg-[var(--color-primary)]/5"
            : "border-[var(--color-risk-red)]/20 bg-red-50",
        )}
      >
        {/* Header with module icon */}
        <div className="flex items-center gap-2">
          <div
            className={clsx(
              "flex h-6 w-6 items-center justify-center rounded-full",
              success
                ? "bg-[var(--color-primary)]"
                : "bg-[var(--color-risk-red)]",
            )}
          >
            <ModuleIcon className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-sm font-semibold text-[var(--foreground)]">
            {success ? "Done" : "Failed"} — {module}.{action}
          </span>
        </div>

        {/* Message */}
        <p className="text-sm text-[var(--foreground)] leading-relaxed pl-8">
          {displayMessage}
        </p>

        {/* Data card (if structured data is present) */}
        {success && response.data && typeof response.data === "object" && (
          <div className="ml-8 rounded-lg bg-[var(--background)] border border-[var(--color-gray-200)] px-3 py-2">
            {Object.entries(response.data)
              .filter(([k]) => !["navigation", "raw", "result"].includes(k))
              .slice(0, 5)
              .map(([key, value]) => (
                <div key={key} className="flex justify-between text-xs py-0.5">
                  <span className="text-[var(--color-gray-500)] capitalize">
                    {key.replace(/_/g, " ")}
                  </span>
                  <span className="text-[var(--foreground)] font-medium">
                    {String(value)}
                  </span>
                </div>
              ))}
          </div>
        )}

        {/* Navigation link */}
        {navigationRoute && (
          <button
            type="button"
            onClick={() => router.push(navigationRoute)}
            className="ml-8 inline-flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline"
          >
            <ExternalLink className="h-3 w-3" />
            View details
          </button>
        )}
      </div>

      {/* ── Undo toast ─────────────────────────────────────── */}
      {undoActive && (
        <div className="flex items-center justify-between rounded-lg bg-[var(--color-gray-100)] px-3 py-2 animate-in slide-in-from-bottom-2 duration-200">
          <span className="text-xs text-[var(--color-gray-600)]">
            Undo available ({undoRemaining}s)
          </span>
          <button
            type="button"
            onClick={handleUndo}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium text-[var(--color-primary)] bg-white border border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)] transition-colors"
          >
            <RotateCcw className="h-3 w-3" />
            Undo
          </button>
        </div>
      )}

      {/* ── Undo result message ─────────────────────────── */}
      {undoMessage && (
        <p className="text-xs text-[var(--color-gray-600)] italic">
          {undoMessage.replace(/^Arbor:\s*/i, "")}
        </p>
      )}
    </div>
  );
}
