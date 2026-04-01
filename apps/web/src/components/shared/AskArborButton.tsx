"use client";

/* ── AskArborButton ─────────────────────────────────────── */
/* Contextual entry point that navigates to the advisory     */
/* chat with a pre-filled question. Two visual variants:     */
/*   "default" — compact button with sparkle icon            */
/*   "subtle"  — inline text link style                      */

import { useRouter } from "next/navigation";
import clsx from "clsx";
import { Sparkles } from "lucide-react";

export interface AskArborButtonProps {
  question: string;
  variant?: "default" | "subtle";
  className?: string;
}

export function AskArborButton({
  question,
  variant = "default",
  className,
}: AskArborButtonProps) {
  const router = useRouter();

  const handleClick = () => {
    router.push(`/advisory?q=${encodeURIComponent(question)}`);
  };

  if (variant === "subtle") {
    return (
      <button
        type="button"
        onClick={handleClick}
        className={clsx(
          "inline-flex items-center gap-1.5 text-sm",
          "text-[var(--color-primary)] hover:underline",
          "transition-colors",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
          className,
        )}
      >
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        Ask Central about this
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={clsx(
        "inline-flex items-center gap-2 rounded-[8px]",
        "px-3 py-1.5 text-sm font-medium",
        "bg-[var(--color-primary)] text-white",
        "hover:bg-[var(--color-primary-light)]",
        "active:bg-[var(--color-primary-dark)]",
        "transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
        className,
      )}
    >
      <Sparkles className="h-4 w-4" aria-hidden="true" />
      Ask Central about this
    </button>
  );
}
