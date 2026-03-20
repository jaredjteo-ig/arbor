"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Check,
  X,
  Loader2,
  AlertTriangle,
  RotateCcw,
  ExternalLink,
} from "lucide-react";
import clsx from "clsx";
import type { PaceStep, ShadowResponse } from "@/services/api/shadow";

/* ── Types ────────────────────────────────────────────────── */

interface PaceCardProps {
  /** The initial preview response from /shadow/execute. */
  response: ShadowResponse;
  /** Called when the user confirms execution. */
  onConfirm: (sessionId: string) => Promise<ShadowResponse>;
  /** Called when the user cancels the session. */
  onCancel: (sessionId: string) => Promise<void>;
  /** Called when the user wants to retry after a failure. */
  onRetry?: (sessionId: string) => void;
}

type CardState =
  | "preview"
  | "cooldown"
  | "double_confirm"
  | "executing"
  | "done"
  | "failed";

/* ── Cooldown duration for dangerous actions ──────────────── */

const COOLDOWN_MS = 5_000;

/* ── Component ────────────────────────────────────────────── */

/**
 * PACE Confirmation Card (T470)
 *
 * Renders the Preview-Approve-Confirm-Exit flow inline within
 * the CommandSurface. Shows a step-by-step plan, waits for user
 * confirmation, then displays execution progress and results.
 *
 * For actions with trust_level === "always_propose", a 5-second
 * cooldown is enforced before the Proceed button becomes active.
 */
export function PaceCard({
  response,
  onConfirm,
  onCancel,
  onRetry,
}: PaceCardProps) {
  const sessionId = response.session_id ?? "";
  const session = response.session;
  const trustLevel = response.intent?.trust_level ?? "propose";
  const isDangerous = trustLevel === "always_propose";
  const isDoubleConfirm = trustLevel === "double_confirm";

  const [state, setState] = useState<CardState>("preview");
  const [steps, setSteps] = useState<PaceStep[]>(session?.steps ?? []);
  const [resultMessage, setResultMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [cooldownRemaining, setCooldownRemaining] = useState(
    isDangerous ? COOLDOWN_MS / 1000 : 0,
  );

  // ── Cooldown timer for dangerous actions ────────────────
  useEffect(() => {
    if (!isDangerous || state !== "preview") return;

    setState("cooldown");
    setCooldownRemaining(COOLDOWN_MS / 1000);

    const interval = setInterval(() => {
      setCooldownRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setState("preview");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isDangerous]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Confirm handler ─────────────────────────────────────
  const handleConfirm = useCallback(async () => {
    if (!sessionId) return;

    setState("executing");

    // Mark all steps as executing sequentially (visual feedback)
    setSteps((prev) =>
      prev.map((s, i) => (i === 0 ? { ...s, status: "executing" } : s)),
    );

    try {
      const result = await onConfirm(sessionId);

      // Handle double_confirm_required — need second confirmation
      if (result.type === "double_confirm_required") {
        setState("double_confirm");
        setResultMessage(result.message ?? "Please confirm again.");
        return;
      }

      // Update steps from result
      if (result.session?.steps) {
        setSteps(result.session.steps);
      } else {
        // Mark all as done
        setSteps((prev) => prev.map((s) => ({ ...s, status: "done" })));
      }

      if (result.success === false) {
        setState("failed");
        setErrorMessage(result.error ?? result.message ?? "Action failed.");
      } else {
        setState("done");
        setResultMessage(result.message ?? "Action completed.");
      }
    } catch {
      setState("failed");
      setErrorMessage("Something went wrong. Please try again.");
      setSteps((prev) => prev.map((s) => ({ ...s, status: "failed" })));
    }
  }, [sessionId, onConfirm]);

  // ── Cancel handler ──────────────────────────────────────
  const handleCancel = useCallback(async () => {
    if (!sessionId) return;
    try {
      await onCancel(sessionId);
    } catch {
      // Cancel is best-effort
    }
  }, [sessionId, onCancel]);

  // ── Step icon ────────────────────────────────────────────
  const StepIcon = ({ status }: { status: PaceStep["status"] }) => {
    switch (status) {
      case "done":
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-primary)]">
            <Check className="h-3 w-3 text-white" />
          </div>
        );
      case "executing":
        return (
          <div className="flex h-5 w-5 items-center justify-center">
            <Loader2 className="h-4 w-4 text-[var(--color-primary)] animate-spin" />
          </div>
        );
      case "failed":
        return (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-risk-red)]">
            <X className="h-3 w-3 text-white" />
          </div>
        );
      default:
        return (
          <div className="h-5 w-5 rounded-full border-2 border-[var(--color-gray-300)]" />
        );
    }
  };

  return (
    <div className="space-y-3">
      {/* ── Header ──────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <svg
          width="16"
          height="16"
          viewBox="0 0 18 18"
          fill="none"
          aria-hidden="true"
        >
          <circle
            cx="7"
            cy="9"
            r="5"
            fill="var(--color-primary)"
            opacity="0.6"
          />
          <ellipse
            cx="12"
            cy="9"
            rx="4"
            ry="3.5"
            fill="var(--color-primary)"
            opacity="0.2"
          />
        </svg>
        <span className="text-sm font-semibold text-[var(--foreground)]">
          {state === "done"
            ? "Action completed"
            : state === "failed"
              ? "Action failed"
              : state === "executing"
                ? "Executing..."
                : "Confirm action"}
        </span>
      </div>

      {/* ── Confirmation message ────────────────────────── */}
      {session?.confirmation_message &&
        state !== "done" &&
        state !== "failed" && (
          <p className="text-sm text-[var(--color-gray-600)] leading-relaxed">
            {session.confirmation_message}
          </p>
        )}

      {/* ── Steps list ──────────────────────────────────── */}
      <div className="space-y-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-start gap-2.5">
            <StepIcon status={step.status} />
            <span
              className={clsx(
                "text-sm leading-snug pt-0.5",
                step.status === "done"
                  ? "text-[var(--foreground)]"
                  : step.status === "failed"
                    ? "text-[var(--color-risk-red)]"
                    : step.status === "executing"
                      ? "text-[var(--foreground)]"
                      : "text-[var(--color-gray-500)]",
              )}
            >
              {step.description}
            </span>
          </div>
        ))}
      </div>

      {/* ── Result message (done state) ─────────────────── */}
      {state === "done" && resultMessage && (
        <div className="rounded-lg bg-[var(--color-gray-50)] px-3 py-2.5">
          <p className="text-sm text-[var(--foreground)] leading-relaxed">
            {resultMessage.replace(/^Arbor:\s*/i, "")}
          </p>
        </div>
      )}

      {/* ── Error message (failed state) ────────────────── */}
      {state === "failed" && errorMessage && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2.5">
          <AlertTriangle className="h-4 w-4 text-[var(--color-risk-red)] mt-0.5 shrink-0" />
          <p className="text-sm text-[var(--color-risk-red)] leading-relaxed">
            {errorMessage.replace(/^Arbor:\s*/i, "")}
          </p>
        </div>
      )}

      {/* ── Action buttons ──────────────────────────────── */}
      <div className="flex items-center gap-2 pt-1">
        {(state === "preview" || state === "cooldown") && (
          <>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={state === "cooldown"}
              className={clsx(
                "inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors",
                state === "cooldown"
                  ? "bg-[var(--color-gray-200)] text-[var(--color-gray-400)] cursor-not-allowed"
                  : "bg-[var(--color-primary)] text-white hover:opacity-90",
              )}
            >
              {state === "cooldown" ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Proceed ({cooldownRemaining}s)
                </>
              ) : (
                "Proceed"
              )}
            </button>
            <button
              type="button"
              onClick={handleCancel}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium text-[var(--color-gray-600)] bg-[var(--color-gray-100)] hover:bg-[var(--color-gray-200)] transition-colors"
            >
              Cancel
            </button>
          </>
        )}

        {state === "executing" && (
          <div className="flex items-center gap-2 text-sm text-[var(--color-gray-500)]">
            <Loader2 className="h-4 w-4 animate-spin text-[var(--color-primary)]" />
            Working on it...
          </div>
        )}

        {state === "done" && response.intent && (
          <a
            href={response.route || `/${response.intent.module}`}
            className="inline-flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline"
          >
            View details
            <ExternalLink className="h-3 w-3" />
          </a>
        )}

        {state === "failed" && onRetry && (
          <button
            type="button"
            onClick={() => onRetry(sessionId)}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium text-[var(--color-gray-600)] bg-[var(--color-gray-100)] hover:bg-[var(--color-gray-200)] transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Retry
          </button>
        )}
      </div>

      {/* ── Double confirm state ────────────────────────── */}
      {state === "double_confirm" && (
        <div className="space-y-2">
          <div className="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2.5 border border-amber-200">
            <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-800">
                Second confirmation required
              </p>
              <p className="text-xs text-amber-700 mt-0.5">
                This is a government or financial action. Please confirm again
                to proceed.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleConfirm}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium bg-amber-600 text-white hover:bg-amber-700 transition-colors"
            >
              Confirm Again
            </button>
            <button
              type="button"
              onClick={handleCancel}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium text-[var(--color-gray-600)] bg-[var(--color-gray-100)] hover:bg-[var(--color-gray-200)] transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* ── Danger warning for always_propose actions ──── */}
      {(isDangerous || isDoubleConfirm) &&
        (state === "preview" || state === "cooldown") && (
          <p className="text-[10px] text-[var(--color-risk-amber)] mt-1">
            {isDoubleConfirm
              ? "This is a government/financial action requiring double confirmation."
              : "This action modifies data and cannot be easily undone."}
          </p>
        )}
    </div>
  );
}
