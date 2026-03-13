"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import clsx from "clsx";
import {
  LayoutDashboard,
  MessageSquare,
  Calculator,
  FileText,
  Shield,
  AlertTriangle,
  Users,
  BarChart3,
  Bell,
  Building2,
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface NavItem {
  labelKey: string;
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
}

const primaryNavItems: NavItem[] = [
  {
    labelKey: "nav.dashboard",
    label: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    labelKey: "nav.advisory",
    label: "Advisory",
    href: "/advisory",
    icon: MessageSquare,
  },
  {
    labelKey: "nav.calculators",
    label: "Calculators",
    href: "/calculators",
    icon: Calculator,
  },
  {
    labelKey: "nav.documents",
    label: "Documents",
    href: "/documents",
    icon: FileText,
  },
  {
    labelKey: "nav.compliance",
    label: "Compliance",
    href: "/compliance",
    icon: Shield,
  },
  {
    labelKey: "nav.emergency",
    label: "Emergency",
    href: "/emergency",
    icon: AlertTriangle,
  },
  {
    labelKey: "nav.clients",
    label: "Clients",
    href: "/clients",
    icon: Users,
  },
  {
    labelKey: "nav.analytics",
    label: "Analytics",
    href: "/analytics",
    icon: BarChart3,
  },
];

const secondaryNavItems: NavItem[] = [
  { labelKey: "nav.alerts", label: "Alerts", href: "/alerts", icon: Bell },
  {
    labelKey: "nav.profile",
    label: "Company Profile",
    href: "/profile",
    icon: Building2,
  },
  {
    labelKey: "nav.settings",
    label: "Settings",
    href: "/settings",
    icon: Settings,
  },
  { labelKey: "nav.help", label: "Help", href: "/help", icon: HelpCircle },
];

export interface NavigationSidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

function isRouteActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(href + "/");
}

export function NavigationSidebar({
  collapsed,
  onToggle,
}: NavigationSidebarProps) {
  const pathname = usePathname();

  return (
    <nav
      className={clsx(
        "flex flex-col h-full bg-[var(--color-surface-sidebar)]",
        "transition-[width] duration-200 ease-in-out",
        collapsed ? "w-[60px]" : "w-[240px]",
      )}
      aria-label="Main navigation"
    >
      {/* Logo / Brand */}
      <div
        className={clsx(
          "flex items-center h-[56px] border-b border-white/10 shrink-0",
          collapsed ? "justify-center px-2" : "px-4",
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={clsx(
              "flex items-center justify-center rounded-lg",
              "bg-white/15 text-white font-bold shrink-0",
              "w-8 h-8 text-sm",
            )}
          >
            A
          </div>
          {!collapsed && (
            <span className="text-white font-semibold text-lg truncate">
              AITE
            </span>
          )}
        </div>
      </div>

      {/* Primary nav */}
      <div className="flex-1 overflow-y-auto py-2">
        <ul className="flex flex-col gap-0.5 px-2" role="list">
          {primaryNavItems.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={isRouteActive(pathname, item.href)}
              collapsed={collapsed}
            />
          ))}
        </ul>

        {/* Divider */}
        <div className="my-3 mx-3 border-t border-white/15" role="separator" />

        {/* Secondary nav */}
        <ul className="flex flex-col gap-0.5 px-2" role="list">
          {secondaryNavItems.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={isRouteActive(pathname, item.href)}
              collapsed={collapsed}
            />
          ))}
        </ul>
      </div>

      {/* Collapse toggle */}
      <div className="shrink-0 border-t border-white/10 p-2">
        <button
          type="button"
          onClick={onToggle}
          className={clsx(
            "flex items-center justify-center w-full rounded-lg",
            "min-h-[44px] min-w-[44px]",
            "text-white/70 hover:text-white hover:bg-[var(--color-surface-sidebar-hover)]",
            "transition-colors duration-200",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white",
          )}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="h-5 w-5" aria-hidden="true" />
          ) : (
            <ChevronLeft className="h-5 w-5" aria-hidden="true" />
          )}
        </button>
      </div>
    </nav>
  );
}

/* ── NavLink item ──────────────────────────────────────────── */

interface NavLinkProps {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
}

function NavLink({ item, active, collapsed }: NavLinkProps) {
  const Icon = item.icon;

  return (
    <li>
      <Link
        href={item.href}
        title={collapsed ? item.label : undefined}
        className={clsx(
          "group relative flex items-center gap-3 rounded-lg",
          "min-h-[44px] px-3 py-2",
          "transition-colors duration-200",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white",
          active
            ? "bg-[var(--color-primary-light)] text-white"
            : "text-white/70 hover:text-white hover:bg-[var(--color-surface-sidebar-hover)]",
          collapsed && "justify-center px-0",
        )}
        aria-current={active ? "page" : undefined}
      >
        <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
        {!collapsed && (
          <span className="text-sm font-medium truncate">{item.label}</span>
        )}

        {/* Tooltip for collapsed state */}
        {collapsed && (
          <span
            className={clsx(
              "absolute left-full ml-2 px-2 py-1 rounded-md",
              "bg-[var(--color-gray-900)] text-white text-xs font-medium",
              "whitespace-nowrap opacity-0 pointer-events-none",
              "group-hover:opacity-100 group-focus-visible:opacity-100",
              "transition-opacity duration-150 z-50",
              "shadow-[var(--shadow-raised)]",
            )}
            role="tooltip"
          >
            {item.label}
          </span>
        )}
      </Link>
    </li>
  );
}
