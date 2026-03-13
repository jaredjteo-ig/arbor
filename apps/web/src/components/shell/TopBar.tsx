"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import clsx from "clsx";
import { Menu, Search, Bell, User, Settings, LogOut, X } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

export interface TopBarProps {
  /** Callback to toggle the sidebar (mobile hamburger) */
  onMenuToggle: () => void;
  /** Number of unread notifications */
  notificationCount?: number;
}

export function TopBar({ onMenuToggle, notificationCount = 0 }: TopBarProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [searchExpanded, setSearchExpanded] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  /* User initial for avatar */
  const userInitial =
    user?.name?.charAt(0)?.toUpperCase() ||
    user?.email?.charAt(0)?.toUpperCase() ||
    "U";

  /* Close profile dropdown on outside click */
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        profileRef.current &&
        !profileRef.current.contains(e.target as Node)
      ) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  /* Focus search input when expanded */
  useEffect(() => {
    if (searchExpanded && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [searchExpanded]);

  return (
    <header
      className={clsx(
        "flex items-center h-[56px] px-4 shrink-0",
        "bg-[var(--color-surface-card)]",
        "border-b border-[var(--color-gray-200)]",
      )}
    >
      {/* Hamburger (mobile only) */}
      <button
        type="button"
        onClick={onMenuToggle}
        className={clsx(
          "flex items-center justify-center rounded-lg md:hidden",
          "min-h-[44px] min-w-[44px] -ml-2",
          "text-[var(--color-gray-600)] hover:text-[var(--color-gray-900)]",
          "hover:bg-[var(--color-gray-100)]",
          "transition-colors duration-200",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
        )}
        aria-label="Toggle navigation menu"
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
      </button>

      {/* Search */}
      <div className="flex-1 flex items-center ml-2 md:ml-0">
        <div
          className={clsx(
            "relative flex items-center transition-all duration-200",
            searchExpanded ? "w-full max-w-md" : "w-auto",
          )}
        >
          {!searchExpanded && (
            <button
              type="button"
              onClick={() => setSearchExpanded(true)}
              className={clsx(
                "flex items-center justify-center rounded-lg",
                "min-h-[44px] min-w-[44px]",
                "text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]",
                "hover:bg-[var(--color-gray-100)]",
                "transition-colors duration-200",
                "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
              )}
              aria-label="Open search"
            >
              <Search className="h-5 w-5" aria-hidden="true" />
            </button>
          )}

          {searchExpanded && (
            <div className="flex items-center w-full gap-2">
              <div className="relative flex-1">
                <Search
                  className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-gray-400)]"
                  aria-hidden="true"
                />
                <input
                  ref={searchInputRef}
                  type="search"
                  placeholder="Search..."
                  className={clsx(
                    "w-full rounded-lg border px-3 py-2 pl-9 text-sm",
                    "min-h-[40px]",
                    "bg-[var(--color-surface-input)]",
                    "border-[var(--color-surface-input-border)]",
                    "placeholder:text-[var(--color-gray-400)]",
                    "focus:border-[var(--color-surface-input-focus)]",
                    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
                    "transition-colors duration-200",
                  )}
                  onBlur={(e) => {
                    if (!e.currentTarget.value) {
                      setSearchExpanded(false);
                    }
                  }}
                />
              </div>
              <button
                type="button"
                onClick={() => setSearchExpanded(false)}
                className={clsx(
                  "flex items-center justify-center rounded-lg",
                  "min-h-[44px] min-w-[44px]",
                  "text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)]",
                  "hover:bg-[var(--color-gray-100)]",
                  "transition-colors duration-200",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
                )}
                aria-label="Close search"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-1">
        {/* Notifications */}
        <button
          type="button"
          onClick={() => router.push("/alerts")}
          className={clsx(
            "relative flex items-center justify-center rounded-lg",
            "min-h-[44px] min-w-[44px]",
            "text-[var(--color-gray-600)] hover:text-[var(--color-gray-900)]",
            "hover:bg-[var(--color-gray-100)]",
            "transition-colors duration-200",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
          )}
          aria-label={`Notifications${notificationCount > 0 ? ` (${notificationCount} unread)` : ""}`}
        >
          <Bell className="h-5 w-5" aria-hidden="true" />
          {notificationCount > 0 && (
            <span
              className={clsx(
                "absolute top-1.5 right-1.5 flex items-center justify-center",
                "min-w-[18px] h-[18px] px-1 rounded-full",
                "bg-[var(--color-error)] text-white text-[11px] font-semibold leading-none",
              )}
              aria-hidden="true"
            >
              {notificationCount > 99 ? "99+" : notificationCount}
            </span>
          )}
        </button>

        {/* Profile */}
        <div className="relative" ref={profileRef}>
          <button
            type="button"
            onClick={() => setProfileOpen((prev) => !prev)}
            className={clsx(
              "flex items-center justify-center rounded-lg",
              "min-h-[44px] min-w-[44px]",
              "transition-colors duration-200",
              "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
            )}
            aria-label="User menu"
            aria-expanded={profileOpen}
            aria-haspopup="true"
          >
            <div
              className={clsx(
                "flex items-center justify-center",
                "w-8 h-8 rounded-full",
                "bg-[var(--color-primary)] text-white text-sm font-semibold",
              )}
            >
              {userInitial}
            </div>
          </button>

          {/* Profile dropdown */}
          {profileOpen && (
            <div
              className={clsx(
                "absolute right-0 top-full mt-1 w-48",
                "rounded-lg border border-[var(--color-gray-200)]",
                "bg-[var(--color-surface-card)]",
                "shadow-[var(--shadow-raised)]",
                "py-1 z-50",
              )}
              role="menu"
            >
              <DropdownItem
                icon={User}
                label="Profile"
                onClick={() => {
                  setProfileOpen(false);
                  router.push("/profile");
                }}
              />
              <DropdownItem
                icon={Settings}
                label="Settings"
                onClick={() => {
                  setProfileOpen(false);
                  router.push("/settings");
                }}
              />
              <div
                className="my-1 border-t border-[var(--color-gray-200)]"
                role="separator"
              />
              <DropdownItem
                icon={LogOut}
                label="Log out"
                onClick={() => {
                  setProfileOpen(false);
                  logout();
                }}
              />
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

/* ── Dropdown menu item ────────────────────────────────────── */

interface DropdownItemProps {
  icon: typeof User;
  label: string;
  onClick: () => void;
}

function DropdownItem({ icon: Icon, label, onClick }: DropdownItemProps) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={onClick}
      className={clsx(
        "flex items-center gap-2 w-full px-3 py-2 text-sm",
        "min-h-[40px]",
        "text-[var(--color-gray-700)]",
        "hover:bg-[var(--color-gray-100)]",
        "transition-colors duration-200",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
      )}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
}
