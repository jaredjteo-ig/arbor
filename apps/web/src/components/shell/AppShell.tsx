"use client";

import { useState, useEffect, useCallback } from "react";
import clsx from "clsx";
import { NavigationSidebar } from "./NavigationSidebar";
import { TopBar } from "./TopBar";

const STORAGE_KEY = "aite-sidebar-collapsed";

export interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  /* Hydration-safe: read localStorage and set initial state after mount */
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) {
      setCollapsed(stored === "true");
    } else {
      /* Default based on viewport width */
      const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;
      setCollapsed(isTablet);
    }
    setMounted(true);
  }, []);

  /* Respond to resize: auto-collapse on tablet, expand on desktop */
  useEffect(() => {
    function handleResize() {
      const width = window.innerWidth;
      if (width < 768) {
        /* Mobile: sidebar hidden, managed by mobileOpen */
        setMobileOpen(false);
      } else if (width < 1024) {
        /* Tablet: collapse */
        setCollapsed(true);
        setMobileOpen(false);
      }
      /* Desktop (>=1024): respect user preference in localStorage */
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  /* Persist sidebar collapsed state */
  const handleToggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  /* Mobile toggle */
  const handleMobileToggle = useCallback(() => {
    setMobileOpen((prev) => !prev);
  }, []);

  /* Close mobile sidebar */
  const handleOverlayClose = useCallback(() => {
    setMobileOpen(false);
  }, []);

  /* Prevent body scroll when mobile sidebar is open */
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  /* Avoid layout flash before mount */
  if (!mounted) {
    return (
      <div className="flex h-screen bg-[var(--background)]">
        <div className="flex-1 flex flex-col">
          <div className="h-[56px] shrink-0 bg-[var(--color-surface-card)] border-b border-[var(--color-gray-200)]" />
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[var(--background)]">
      {/* Desktop / Tablet sidebar */}
      <div className="hidden md:flex shrink-0">
        <NavigationSidebar collapsed={collapsed} onToggle={handleToggle} />
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={handleOverlayClose}
          aria-hidden="true"
        />
      )}

      {/* Mobile sidebar */}
      <div
        className={clsx(
          "fixed inset-y-0 left-0 z-50 md:hidden",
          "transition-transform duration-200 ease-in-out",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <NavigationSidebar collapsed={false} onToggle={handleMobileToggle} />
      </div>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar onMenuToggle={handleMobileToggle} notificationCount={0} />

        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
