"use client";

import { useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import Link from "next/link";
import clsx from "clsx";
import { useTranslation } from "react-i18next";
import {
  LayoutDashboard,
  MessageSquare,
  Calculator,
  FileText,
  Shield,
  AlertTriangle,
  Users,
  BarChart3,
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  CalendarDays,
  Wallet,
  Receipt,
  Clock,
  CalendarClock,
  ListChecks,
  FileBarChart,
  UserPlus,
  Building2,
  Plug,
  GraduationCap,
  Award,
  FolderKanban,
  Package,
  Timer,
  ClipboardCheck,
  Briefcase,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

interface NavItem {
  labelKey: string;
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  iconClassName?: string;
  children?: NavItem[];
}

/* ── Admin nav groups ─────────────────────────────────────── */

const adminCoreNavItems: NavItem[] = [
  {
    labelKey: "nav.dashboard",
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    labelKey: "nav.advisory",
    label: "Advisory",
    href: "/advisory",
    icon: MessageSquare,
  },
  {
    labelKey: "nav.compliance",
    label: "Compliance",
    href: "/compliance",
    icon: Shield,
  },
];

const adminToolsNavItems: NavItem[] = [
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
];

/* Group 3: Management — expandable sub-categories */
const adminManagementNavItems: NavItem[] = [
  {
    labelKey: "nav.payroll",
    label: "Payroll",
    href: "/payroll",
    icon: Wallet,
    children: [
      {
        labelKey: "nav.payroll.runs",
        label: "Payroll Runs",
        href: "/payroll",
        icon: ListChecks,
      },
      {
        labelKey: "nav.payroll.reports",
        label: "Reports",
        href: "/payroll/accounting-sync",
        icon: FileBarChart,
      },
      {
        labelKey: "nav.payroll.filings",
        label: "Gov Filings",
        href: "/payroll/filings",
        icon: Building2,
      },
    ],
  },
  {
    labelKey: "nav.leave",
    label: "Leave",
    href: "/leave",
    icon: CalendarDays,
    children: [
      {
        labelKey: "nav.leave.applications",
        label: "Applications",
        href: "/leave",
        icon: CalendarDays,
      },
    ],
  },
  {
    labelKey: "nav.policies",
    label: "Policies",
    href: "/policies",
    icon: FileText,
  },
  {
    labelKey: "nav.claims",
    label: "Claims",
    href: "/claims",
    icon: Receipt,
  },
  {
    labelKey: "nav.attendance",
    label: "Attendance",
    href: "/attendance",
    icon: Clock,
  },
  {
    labelKey: "nav.shifts",
    label: "Shifts",
    href: "/shifts",
    icon: CalendarClock,
  },
  {
    labelKey: "nav.employees",
    label: "Employees",
    href: "/employees",
    icon: Users,
  },
  {
    labelKey: "nav.onboarding",
    label: "Onboarding",
    href: "/employees?tab=onboarding",
    icon: ClipboardCheck,
  },
  {
    labelKey: "nav.appraisals",
    label: "Appraisals",
    href: "/appraisals",
    icon: Award,
  },
  {
    labelKey: "nav.projects",
    label: "Projects",
    href: "/projects",
    icon: FolderKanban,
  },
  {
    labelKey: "nav.inventory",
    label: "Inventory",
    href: "/inventory",
    icon: Package,
  },
  {
    labelKey: "nav.recruitment",
    label: "Recruitment",
    href: "/recruitment",
    icon: UserPlus,
    children: [
      {
        labelKey: "nav.recruitment.dashboard",
        label: "Dashboard",
        href: "/recruitment",
        icon: BarChart3,
      },
      {
        labelKey: "nav.recruitment.jobs",
        label: "Jobs",
        href: "/recruitment?tab=jobs",
        icon: Briefcase,
      },
      {
        labelKey: "nav.recruitment.candidates",
        label: "Candidates",
        href: "/recruitment?tab=candidates",
        icon: Users,
      },
      {
        labelKey: "nav.recruitment.interviews",
        label: "Interviews",
        href: "/recruitment?tab=interviews",
        icon: CalendarDays,
      },
      {
        labelKey: "nav.recruitment.settings",
        label: "Settings",
        href: "/recruitment/settings",
        icon: Settings,
      },
    ],
  },
  {
    labelKey: "nav.approvals",
    label: "Approvals",
    href: "/approvals",
    icon: ClipboardCheck,
  },
  {
    labelKey: "nav.reports",
    label: "Reports",
    href: "/reports",
    icon: BarChart3,
  },
  {
    labelKey: "nav.analytics",
    label: "Analytics",
    href: "/analytics",
    icon: BarChart3,
  },
];

const adminBottomNavItems: NavItem[] = [
  {
    labelKey: "nav.emergency",
    label: "Emergency",
    href: "/emergency",
    icon: AlertTriangle,
    iconClassName: "text-[var(--color-risk-amber)]",
  },
  {
    labelKey: "nav.training",
    label: "Training",
    href: "/training/skillsfuture",
    icon: GraduationCap,
  },
  {
    labelKey: "nav.admin",
    label: "Admin",
    href: "/admin",
    icon: Shield,
  },
  {
    labelKey: "nav.integrations",
    label: "Integrations",
    href: "/settings/integrations",
    icon: Plug,
  },
  {
    labelKey: "nav.settings",
    label: "Settings",
    href: "/settings",
    icon: Settings,
  },
  { labelKey: "nav.help", label: "Help", href: "/help", icon: HelpCircle },
];

/* ── Employee nav groups ──────────────────────────────────── */

const employeeCoreNavItems: NavItem[] = [
  {
    labelKey: "nav.my-dashboard",
    label: "My Dashboard",
    href: "/my-dashboard",
    icon: LayoutDashboard,
  },
  {
    labelKey: "nav.my-onboarding",
    label: "My Onboarding",
    href: "/my-onboarding",
    icon: ClipboardCheck,
  },
  {
    labelKey: "nav.my-profile",
    label: "My Profile",
    href: "/my-profile",
    icon: Users,
  },
  {
    labelKey: "nav.my-leave",
    label: "My Leave",
    href: "/my-leave",
    icon: CalendarDays,
  },
  {
    labelKey: "nav.my-claims",
    label: "My Claims",
    href: "/my-claims",
    icon: Receipt,
  },
  {
    labelKey: "nav.my-payslips",
    label: "My Payslips",
    href: "/my-payslips",
    icon: Wallet,
  },
  {
    labelKey: "nav.my-attendance",
    label: "My Attendance",
    href: "/my-attendance",
    icon: Clock,
  },
  {
    labelKey: "nav.my-timesheets",
    label: "My Timesheets",
    href: "/my-timesheets",
    icon: Timer,
  },
  {
    labelKey: "nav.my-inventory",
    label: "My Inventory",
    href: "/my-inventory",
    icon: Package,
  },
  {
    labelKey: "nav.advisory",
    label: "Advisory",
    href: "/advisory",
    icon: MessageSquare,
  },
];

const employeeBottomNavItems: NavItem[] = [
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

function isRouteActive(
  pathname: string,
  href: string,
  searchParams?: URLSearchParams | null,
  exactOnly?: boolean,
): boolean {
  if (href === "/") return pathname === "/";

  // Parse href to separate path from query params
  const [hrefPath, hrefQuery] = href.split("?");

  if (hrefQuery) {
    // For hrefs with query params (e.g. "/employees?tab=onboarding"),
    // match both pathname AND the query param
    if (pathname !== hrefPath) return false;
    if (!searchParams) return false;
    const expectedParams = new URLSearchParams(hrefQuery);
    for (const [key, value] of expectedParams.entries()) {
      if (searchParams.get(key) !== value) return false;
    }
    return true;
  }

  // Exact match mode — used for employee nav items that share routes with
  // admin items (e.g. /claims, /leave, /attendance) to prevent collisions.
  if (exactOnly) {
    return pathname === hrefPath;
  }

  // For plain hrefs, match pathname but NOT if a "tab" query param is set
  // (meaning a sibling nav item specifically targets this path + tab combo)
  const pathMatch =
    pathname === hrefPath || pathname.startsWith(hrefPath + "/");
  if (!pathMatch) return false;

  // If the current URL has a "tab" query param and this href is an exact path
  // match (not a prefix), defer to the tab-specific nav item
  if (searchParams?.has("tab") && pathname === hrefPath) return false;

  return true;
}

function isGroupActive(
  pathname: string,
  item: NavItem,
  searchParams?: URLSearchParams | null,
): boolean {
  if (isRouteActive(pathname, item.href, searchParams)) return true;
  return (
    item.children?.some((c) => isRouteActive(pathname, c.href, searchParams)) ??
    false
  );
}

export function NavigationSidebar({
  collapsed,
  onToggle,
}: NavigationSidebarProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { t } = useTranslation();

  const isEmployee = user?.role === "employee";

  const coreNavItems = isEmployee ? employeeCoreNavItems : adminCoreNavItems;
  const bottomNavItems = isEmployee
    ? employeeBottomNavItems
    : adminBottomNavItems;

  return (
    <nav
      className={clsx(
        "flex flex-col h-full bg-[var(--color-surface-sidebar)]",
        "transition-[width] duration-200 ease-in-out",
        collapsed ? "w-[60px]" : "w-[240px]",
      )}
      aria-label="Main navigation"
    >
      {/* Logo */}
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
            C
          </div>
          {!collapsed && (
            <span className="text-white font-semibold text-lg truncate">
              Central
            </span>
          )}
        </div>
      </div>

      {/* Nav */}
      <div className="flex-1 overflow-y-auto py-2">
        {/* Core */}
        <ul className="flex flex-col gap-0.5 px-2" role="list">
          {coreNavItems.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={isRouteActive(
                pathname,
                item.href,
                searchParams,
                isEmployee,
              )}
              collapsed={collapsed}
            />
          ))}
        </ul>

        {/* Admin groups */}
        {!isEmployee && (
          <>
            {/* Tools */}
            <NavGroupLabel label={t("nav.group_tools")} collapsed={collapsed} />
            <ul className="flex flex-col gap-0.5 px-2" role="list">
              {adminToolsNavItems.map((item) => (
                <NavLink
                  key={item.href}
                  item={item}
                  active={isRouteActive(pathname, item.href, searchParams)}
                  collapsed={collapsed}
                />
              ))}
            </ul>

            {/* Management — expandable */}
            <NavGroupLabel
              label={t("nav.group_management")}
              collapsed={collapsed}
            />
            <ul className="flex flex-col gap-0.5 px-2" role="list">
              {adminManagementNavItems.map((item) =>
                item.children && !collapsed ? (
                  <ExpandableNavLink
                    key={item.href}
                    item={item}
                    pathname={pathname}
                    collapsed={collapsed}
                    searchParams={searchParams}
                  />
                ) : (
                  <NavLink
                    key={item.href}
                    item={item}
                    active={isGroupActive(pathname, item, searchParams)}
                    collapsed={collapsed}
                  />
                ),
              )}
            </ul>
          </>
        )}

        {/* Separator */}
        <div className="my-3 mx-3 border-t border-white/15" role="separator" />

        {/* Bottom */}
        <ul className="flex flex-col gap-0.5 px-2" role="list">
          {bottomNavItems.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={isRouteActive(pathname, item.href, searchParams)}
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

/* ── NavGroupLabel ─────────────────────────────────────────── */

function NavGroupLabel({
  label,
  collapsed,
}: {
  label: string;
  collapsed: boolean;
}) {
  if (collapsed) return null;
  return (
    <p className="px-4 pt-4 pb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-gray-400)]">
      {label}
    </p>
  );
}

/* ── Expandable NavLink (with children) ────────────────────── */

function ExpandableNavLink({
  item,
  pathname,
  collapsed,
  searchParams,
}: {
  item: NavItem;
  pathname: string;
  collapsed: boolean;
  searchParams?: URLSearchParams | null;
}) {
  const { t } = useTranslation();
  const active = isGroupActive(pathname, item, searchParams);
  const [expanded, setExpanded] = useState(active);
  const Icon = item.icon;
  const translated = t(item.labelKey, { defaultValue: item.label });

  return (
    <li>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={clsx(
          "group relative flex items-center gap-3 rounded-lg w-full text-left",
          "min-h-[44px] px-3 py-2",
          "transition-colors duration-200",
          active
            ? "bg-[var(--color-primary-light)] text-white"
            : "text-white/70 hover:text-white hover:bg-[var(--color-surface-sidebar-hover)]",
        )}
      >
        <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium truncate flex-1">
          {translated}
        </span>
        <ChevronDown
          className={clsx(
            "h-4 w-4 shrink-0 transition-transform duration-200",
            expanded && "rotate-180",
          )}
        />
      </button>

      {expanded && item.children && (
        <ul className="ml-4 mt-0.5 space-y-0.5 border-l border-white/10 pl-2">
          {item.children.map((child) => (
            <li key={child.labelKey}>
              <Link
                href={child.href}
                className={clsx(
                  "flex items-center gap-2 px-2 py-1.5 rounded-md text-xs",
                  "transition-colors duration-200",
                  isRouteActive(pathname, child.href, searchParams)
                    ? "text-white bg-white/10"
                    : "text-white/60 hover:text-white hover:bg-white/5",
                )}
              >
                <child.icon className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">
                  {t(child.labelKey, { defaultValue: child.label })}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

/* ── Simple NavLink ────────────────────────────────────────── */

function NavLink({
  item,
  active,
  collapsed,
}: {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
}) {
  const { t } = useTranslation();
  const Icon = item.icon;
  const translated = t(item.labelKey, { defaultValue: item.label });

  return (
    <li>
      <Link
        href={item.href}
        title={collapsed ? translated : undefined}
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
        <Icon
          className={clsx("h-5 w-5 shrink-0", item.iconClassName)}
          aria-hidden="true"
        />
        {!collapsed && (
          <span className="text-sm font-medium truncate">{translated}</span>
        )}

        {/* Tooltip for collapsed */}
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
            {translated}
          </span>
        )}
      </Link>
    </li>
  );
}
