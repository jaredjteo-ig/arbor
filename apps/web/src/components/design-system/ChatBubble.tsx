"use client";

import type { ReactNode } from "react";
import clsx from "clsx";

export type RiskTier = "green" | "amber" | "red";

interface ChatBubbleBaseProps {
  children: ReactNode;
  className?: string;
}

interface UserBubbleProps extends ChatBubbleBaseProps {
  role: "user";
  riskTier?: never;
  sources?: never;
}

interface SystemBubbleProps extends ChatBubbleBaseProps {
  role: "system";
  /** Optional risk-tier left border colour */
  riskTier?: RiskTier;
  /** Optional source citations rendered below the content */
  sources?: ReactNode;
}

export type ChatBubbleProps = UserBubbleProps | SystemBubbleProps;

const riskBorderStyles: Record<RiskTier, string> = {
  green: "border-l-4 border-l-[var(--color-risk-green)]",
  amber: "border-l-4 border-l-[var(--color-risk-amber)]",
  red: "border-l-4 border-l-[var(--color-risk-red)]",
};

export function ChatBubble(props: ChatBubbleProps) {
  const { role, children, className } = props;

  if (role === "user") {
    return (
      <div className={clsx("flex justify-end", className)}>
        <div
          className={clsx(
            "max-w-[85%] rounded-[12px] px-4 py-3",
            "bg-[var(--color-primary-light)] text-white",
            "text-base leading-relaxed",
          )}
        >
          {children}
        </div>
      </div>
    );
  }

  /* System bubble */
  const { riskTier, sources } = props;

  return (
    <div className={clsx("flex justify-start", className)}>
      <div
        className={clsx(
          "w-full rounded-[12px] px-4 py-3",
          "bg-[var(--color-surface-card)] text-[var(--foreground)]",
          "shadow-[var(--shadow-card)]",
          "text-base leading-relaxed",
          /* markdown-like prose spacing */
          "[&_p]:mb-2 [&_ul]:mb-2 [&_ol]:mb-2 [&_li]:ml-4 [&_li]:list-disc",
          "[&_h3]:font-semibold [&_h3]:text-lg [&_h3]:mb-1",
          "[&_h4]:font-semibold [&_h4]:mb-1",
          "[&_strong]:font-semibold",
          riskTier && riskBorderStyles[riskTier],
        )}
      >
        {children}

        {sources && (
          <div className="mt-3 pt-3 border-t border-[var(--color-gray-200)] flex flex-wrap gap-2">
            {sources}
          </div>
        )}
      </div>
    </div>
  );
}
