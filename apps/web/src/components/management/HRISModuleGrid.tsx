"use client";

import { useRouter } from "next/navigation";
import {
  Wallet,
  CalendarDays,
  Receipt,
  Clock,
  CalendarClock,
  Users,
  FileText,
  Shield,
  ArrowRight,
  Plug,
  GraduationCap,
  BarChart3,
} from "lucide-react";

interface Module {
  title: string;
  description: string;
  icon: typeof Wallet;
  href: string;
  color: string;
  bgColor: string;
  stats?: string;
}

const MODULES: Module[] = [
  {
    title: "Payroll",
    description: "CPF, SDL, FWL, payslips, bank files, IR8A",
    icon: Wallet,
    href: "/payroll",
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
  },
  {
    title: "Leave",
    description: "16+ leave types, approvals, calendar, policies",
    icon: CalendarDays,
    href: "/leave",
    color: "text-blue-600",
    bgColor: "bg-blue-50",
  },
  {
    title: "Claims",
    description: "Expense claims, receipt upload, approval, payroll sync",
    icon: Receipt,
    href: "/claims",
    color: "text-orange-600",
    bgColor: "bg-orange-50",
  },
  {
    title: "Attendance",
    description: "Clock in/out, GPS, overtime, timesheet approval",
    icon: Clock,
    href: "/attendance",
    color: "text-violet-600",
    bgColor: "bg-violet-50",
  },
  {
    title: "Shifts",
    description: "Shift scheduling, availability, publishing",
    icon: CalendarClock,
    href: "/shifts",
    color: "text-pink-600",
    bgColor: "bg-pink-50",
  },
  {
    title: "Employees",
    description: "Profiles, onboarding, documents, org chart",
    icon: Users,
    href: "/employees",
    color: "text-teal-600",
    bgColor: "bg-teal-50",
  },
  {
    title: "Documents",
    description: "Contracts, KETs, HR templates, PDF generation",
    icon: FileText,
    href: "/documents",
    color: "text-amber-600",
    bgColor: "bg-amber-50",
  },
  {
    title: "Compliance",
    description: "6-domain health check, risk alerts, regulations",
    icon: Shield,
    href: "/compliance",
    color: "text-red-600",
    bgColor: "bg-red-50",
  },
  {
    title: "Training",
    description: "SkillsFuture courses, grants, SFC credits",
    icon: GraduationCap,
    href: "/training/skillsfuture",
    color: "text-indigo-600",
    bgColor: "bg-indigo-50",
  },
  {
    title: "Analytics",
    description: "Workforce data, payroll summaries, reports",
    icon: BarChart3,
    href: "/analytics",
    color: "text-cyan-600",
    bgColor: "bg-cyan-50",
  },
  {
    title: "Integrations",
    description: "Xero, banks, WhatsApp, Telegram, SkillsFuture",
    icon: Plug,
    href: "/settings/integrations",
    color: "text-gray-600",
    bgColor: "bg-gray-50",
  },
];

interface HRISModuleGridProps {
  hasCompany: boolean;
  compact?: boolean;
}

/**
 * Rich module navigation grid for the dashboard.
 * Shows all HRIS modules as clickable cards with descriptions.
 */
export function HRISModuleGrid({
  hasCompany,
  compact = false,
}: HRISModuleGridProps) {
  const router = useRouter();

  return (
    <div
      className={`grid gap-3 ${compact ? "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4" : "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4"}`}
    >
      {MODULES.map((mod) => {
        const Icon = mod.icon;
        return (
          <button
            key={mod.title}
            type="button"
            onClick={() => router.push(mod.href)}
            className="group text-left p-4 rounded-xl border border-gray-200 bg-white hover:border-blue-300 hover:shadow-md transition-all duration-200"
          >
            <div className="flex items-start gap-3">
              <div
                className={`w-9 h-9 rounded-lg ${mod.bgColor} flex items-center justify-center shrink-0`}
              >
                <Icon className={`w-4.5 h-4.5 ${mod.color}`} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900 text-sm">
                    {mod.title}
                  </h3>
                  <ArrowRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-blue-500 transition-colors shrink-0" />
                </div>
                <p className="text-xs text-gray-500 mt-0.5 leading-relaxed line-clamp-2">
                  {mod.description}
                </p>
                {mod.stats && hasCompany && (
                  <p className="text-xs text-blue-600 font-medium mt-1">
                    {mod.stats}
                  </p>
                )}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
