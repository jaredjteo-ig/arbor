"use client";

import { useEffect } from "react";
import clsx from "clsx";

interface ShadowWidgetProps {
  /** Whether the command surface is currently open */
  isCommandOpen: boolean;
  /** Whether the shadow agent has something to surface (attention state) */
  hasAttention?: boolean;
  /** Whether the advisory deep workspace page is active */
  isAdvisoryPage?: boolean;
  /** Number of unseen nudges to display as a badge */
  nudgeCount?: number;
  /** Callback to toggle the command surface */
  onToggle: () => void;
  /** Callback when the widget is clicked (marks nudges as seen) */
  onNudgesSeen?: () => void;
}

/**
 * The Shadow Widget — persistent entry point for the AI command surface.
 *
 * Replaces the old AdvisoryFAB. A subtle 36px circle with a breathing
 * animation that communicates "alive" without being distracting.
 *
 * Four visual states:
 * - Resting: semi-transparent with slow breathing pulse
 * - Hover: solidifies, slight scale, shows tooltip
 * - Attention: periodic ripple when the agent has something to surface
 * - Hidden: when command surface is open or on advisory page
 */
export function ShadowWidget({
  isCommandOpen,
  hasAttention = false,
  isAdvisoryPage = false,
  nudgeCount = 0,
  onToggle,
  onNudgesSeen,
}: ShadowWidgetProps) {
  const showNudgeBadge = nudgeCount > 0;
  const showAttention = hasAttention || showNudgeBadge;

  const handleClick = () => {
    // Mark nudges as seen when user interacts with the widget
    if (showNudgeBadge && onNudgesSeen) {
      onNudgesSeen();
    }
    onToggle();
  };

  // Global keyboard shortcut: Ctrl+Shift+A
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === "A") {
        e.preventDefault();
        // Mark nudges as seen on keyboard shortcut too
        if (nudgeCount > 0 && onNudgesSeen) {
          onNudgesSeen();
        }
        onToggle();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onToggle, onNudgesSeen, nudgeCount]);

  // Hide when command surface is open or on advisory deep workspace
  if (isCommandOpen || isAdvisoryPage) return null;

  return (
    <div
      className="fixed bottom-6 right-6 lg:right-[calc(var(--shadow-margin-current,var(--shadow-margin-collapsed))+1.5rem)] transition-[right] duration-[var(--shadow-transition-normal)] ease-out"
      style={{ zIndex: "var(--z-shadow-widget)" }}
    >
      {/* Attention ripple ring — when agent has something to surface or nudges exist */}
      {showAttention && (
        <span
          className={clsx(
            "absolute inset-0 rounded-full",
            "bg-[var(--shadow-accent)]",
            showNudgeBadge
              ? "animate-shadow-nudge-pulse"
              : "animate-shadow-ripple",
          )}
          style={{
            width: "var(--shadow-widget-size)",
            height: "var(--shadow-widget-size)",
          }}
          aria-hidden="true"
        />
      )}

      {/* Main widget button */}
      <button
        type="button"
        onClick={handleClick}
        aria-label={`Ask Central (Ctrl+Shift+A)${showNudgeBadge ? ` — ${nudgeCount} new notification${nudgeCount !== 1 ? "s" : ""}` : ""}`}
        title="Ask Central (Ctrl+Shift+A)"
        className={clsx(
          "relative flex items-center justify-center",
          "rounded-full cursor-pointer",
          "bg-[var(--color-primary)]",
          "text-white",
          showNudgeBadge ? "opacity-100" : "animate-shadow-breathe",
          "hover:opacity-100 hover:scale-110",
          "active:scale-95",
          "transition-transform duration-[var(--shadow-transition-fast)] ease-out",
          "motion-reduce:hover:scale-100",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
        )}
        style={{
          width: "var(--shadow-widget-size)",
          height: "var(--shadow-widget-size)",
        }}
      >
        {/* Shadow mark icon — abstract circle with trailing gradient */}
        <svg
          width="18"
          height="18"
          viewBox="0 0 18 18"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="7" cy="9" r="5" fill="white" opacity="0.9" />
          <ellipse cx="12" cy="9" rx="4" ry="3.5" fill="white" opacity="0.3" />
        </svg>
      </button>

      {/* Nudge count badge — shown when there are unseen nudges */}
      {showNudgeBadge && (
        <span
          className={clsx(
            "absolute -top-1 -right-1 flex items-center justify-center",
            "min-w-[18px] h-[18px] px-1 rounded-full",
            "bg-[var(--color-error)] text-white text-[11px] font-semibold leading-none",
            "pointer-events-none",
            "animate-shadow-badge-in",
          )}
          aria-hidden="true"
        >
          {nudgeCount > 9 ? "9+" : nudgeCount}
        </span>
      )}
    </div>
  );
}
