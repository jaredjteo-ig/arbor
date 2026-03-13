import type { ReactNode } from "react";

/**
 * Auth layout — standalone fullscreen pages without the AppShell sidebar/topbar.
 * Centers a card on a subtle gradient background.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[var(--color-gray-50)] via-white to-[var(--color-gray-100)] px-4 py-8">
      <div className="w-full max-w-[440px]">{children}</div>
    </div>
  );
}
