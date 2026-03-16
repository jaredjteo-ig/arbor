import type { ReactNode } from "react";
import { ValuePropositionPanel } from "./elements/ValuePropositionPanel";

/**
 * Auth layout — split-screen on desktop, full-width form on mobile.
 *
 * Left panel (md+): Value proposition content on dark navy background.
 * Right panel:      The login/signup form card, centered vertically.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      {/* Left: value proposition (hidden on mobile) */}
      <ValuePropositionPanel />

      {/* Right: auth form card */}
      <div className="flex flex-1 items-center justify-center bg-gradient-to-br from-[var(--color-gray-50)] via-white to-[var(--color-gray-100)] px-4 py-8">
        <div className="w-full max-w-[440px]">{children}</div>
      </div>
    </div>
  );
}
