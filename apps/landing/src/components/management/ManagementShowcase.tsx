"use client";

import Link from "next/link";
import {
  Wallet,
  CalendarDays,
  Receipt,
  Clock,
  CalendarClock,
  Users,
  FileText,
  Shield,
  Building2,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  Globe,
  Zap,
  Lock,
} from "lucide-react";

interface FeatureModule {
  id: string;
  title: string;
  description: string;
  icon: typeof Wallet;
  color: string;
  bgColor: string;
  capabilities: string[];
}

const FEATURE_MODULES: FeatureModule[] = [
  {
    id: "payroll",
    title: "Payroll",
    description:
      "Complete payroll processing with CPF, SDL, FWL, and SHG calculations. Generate payslips, bank files, and statutory filings.",
    icon: Wallet,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50",
    capabilities: [
      "Gross-to-net calculation",
      "CPF for all age bands & PR years",
      "SDL, FWL, SHG auto-calculated",
      "Payslip generation (EA s88A)",
      "CPF e-Submit file",
      "IR8A/IR21 tax filings",
      "Bank GIRO/FAST files",
      "YTD tracking & reports",
    ],
  },
  {
    id: "leave",
    title: "Leave Management",
    description:
      "Full leave lifecycle from application to approval. Supports all Singapore statutory leave types with pro-ration.",
    icon: CalendarDays,
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    capabilities: [
      "16+ leave types (EA compliant)",
      "Application & approval workflow",
      "Balance auto-calculation",
      "Public holiday integration",
      "Carry-forward rules",
      "Leave calendar view",
      "Policy by employee group",
      "Pro-ration for mid-year joiners",
    ],
  },
  {
    id: "claims",
    title: "Claims & Expenses",
    description:
      "Digital expense claims with receipt uploads, category tracking, approval workflows, and payroll integration.",
    icon: Receipt,
    color: "text-orange-600",
    bgColor: "bg-orange-50",
    capabilities: [
      "Digital claim submission",
      "Receipt photo upload",
      "Custom categories & limits",
      "Approval workflow",
      "Audit trail",
      "Claims-to-payroll integration",
      "Monthly reports",
      "Accounting sync",
    ],
  },
  {
    id: "attendance",
    title: "Attendance & Time",
    description:
      "Clock in/out with GPS verification, overtime tracking, and timesheet approval linked to payroll.",
    icon: Clock,
    color: "text-violet-600",
    bgColor: "bg-violet-50",
    capabilities: [
      "Mobile clock in/out",
      "GPS location tracking",
      "Photo proof of attendance",
      "Lateness detection",
      "Overtime auto-calculation",
      "Timesheet approval",
      "Real-time payroll sync",
      "Multi-location support",
    ],
  },
  {
    id: "shifts",
    title: "Shift Scheduling",
    description:
      "Visual shift allocation with availability checking, leave integration, and labour law compliance.",
    icon: CalendarClock,
    color: "text-pink-600",
    bgColor: "bg-pink-50",
    capabilities: [
      "Weekly shift grid",
      "Availability-based scheduling",
      "Leave-integrated availability",
      "Schedule publishing",
      "Hours per staff tracking",
      "Auto-payroll calculation",
      "Mobile schedule access",
      "44-hour weekly limit check",
    ],
  },
  {
    id: "employees",
    title: "Employee Management",
    description:
      "Complete employee lifecycle from onboarding to offboarding. NRIC/bank encryption, org chart, and document storage.",
    icon: Users,
    color: "text-teal-600",
    bgColor: "bg-teal-50",
    capabilities: [
      "Employee profiles (30+ fields)",
      "PII encryption (PDPA)",
      "Onboarding workflow",
      "Probation tracking",
      "Org chart",
      "Document storage",
      "Bulk CSV import",
      "Employment history",
    ],
  },
  {
    id: "documents",
    title: "Documents",
    description:
      "Generate employment contracts, KET documents, and HR templates customised to your company.",
    icon: FileText,
    color: "text-amber-600",
    bgColor: "bg-amber-50",
    capabilities: [
      "Employment contracts",
      "Key Employment Terms (KET)",
      "HR policy templates",
      "Letter generation",
      "Custom templates",
      "PDF export",
    ],
  },
  {
    id: "compliance",
    title: "Compliance",
    description:
      "Automated compliance health checks across 6 regulatory domains. Stay ahead of gaps before they become fines.",
    icon: Shield,
    color: "text-red-600",
    bgColor: "bg-red-50",
    capabilities: [
      "6-domain health check",
      "Risk-tiered findings",
      "Regulatory alerts",
      "Fine amount warnings",
      "Remediation guidance",
      "Shadow agent annotations",
    ],
  },
];

const VALUE_PROPS = [
  {
    icon: Zap,
    title: "Quick Setup",
    description:
      "Get started in under a minute. No complex configuration required.",
  },
  {
    icon: Sparkles,
    title: "AI-Powered",
    description:
      "Shadow agent answers HR questions, surfaces compliance gaps, and guides you.",
  },
  {
    icon: Lock,
    title: "Singapore Compliant",
    description:
      "Employment Act, CPF, IRAS, MOM — built for Singapore from the ground up.",
  },
  {
    icon: Globe,
    title: "All-in-One",
    description:
      "Payroll, leave, claims, attendance, shifts, compliance — one platform.",
  },
];

export function ManagementShowcase() {
  return (
    <div className="max-w-7xl mx-auto">
      {/* Hero Section */}
      <div className="relative mb-10 rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-700 p-8 md:p-12 text-white overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full -translate-y-1/2 translate-x-1/3" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-white rounded-full translate-y-1/2 -translate-x-1/3" />
        </div>

        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/20 backdrop-blur-sm rounded-full text-sm font-medium mb-4">
            <Sparkles className="w-4 h-4" />
            HR Management for Singapore SMEs
          </div>
          <h1 className="text-3xl md:text-4xl font-bold mb-4">
            Your Complete HR Management Suite
          </h1>
          <p className="text-lg text-white/80 mb-8 leading-relaxed">
            Payroll, leave, claims, attendance, shifts, employee management,
            compliance — everything you need to run HR. Plus an AI assistant
            that knows Singapore employment law.
          </p>
          <Link
            href="/contact"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-blue-700 font-semibold rounded-xl hover:bg-white/90 transition-all shadow-lg"
          >
            <Building2 className="w-5 h-5" />
            Contact Us
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Value Props Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        {VALUE_PROPS.map((prop) => {
          const Icon = prop.icon;
          return (
            <div
              key={prop.title}
              className="flex flex-col items-center text-center p-4 rounded-xl bg-white border border-gray-100 shadow-sm"
            >
              <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center mb-3">
                <Icon className="w-5 h-5 text-blue-600" />
              </div>
              <h3 className="font-semibold text-gray-900 text-sm mb-1">
                {prop.title}
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                {prop.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* Section Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">What You Get</h2>
          <p className="text-sm text-gray-500 mt-1">
            All these features unlock when you set up your company
          </p>
        </div>
      </div>

      {/* Feature Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
        {FEATURE_MODULES.map((module) => {
          const Icon = module.icon;
          return (
            <Link
              key={module.id}
              href="/contact"
              className="group relative rounded-xl border border-gray-100 bg-white hover:border-blue-300 hover:shadow-md transition-all duration-200"
            >
              <div className="p-5">
                <div className="flex items-start gap-3 mb-3">
                  <div
                    className={`w-10 h-10 rounded-lg ${module.bgColor} flex items-center justify-center shrink-0`}
                  >
                    <Icon className={`w-5 h-5 ${module.color}`} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-gray-900 text-sm leading-tight">
                      {module.title}
                    </h3>
                  </div>
                </div>

                <p className="text-xs text-gray-500 leading-relaxed mb-3">
                  {module.description}
                </p>

                <div className="space-y-1">
                  {module.capabilities.slice(0, 4).map((cap) => (
                    <div key={cap} className="flex items-center gap-1.5">
                      <CheckCircle2 className="w-3 h-3 text-green-500 shrink-0" />
                      <span className="text-xs text-gray-600 truncate">
                        {cap}
                      </span>
                    </div>
                  ))}
                  {module.capabilities.length > 4 && (
                    <p className="text-xs text-gray-400 pl-[18px]">
                      +{module.capabilities.length - 4} more features
                    </p>
                  )}
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Bottom CTA */}
      <div className="text-center py-8 px-4 rounded-xl bg-gray-50 border border-gray-200">
        <Building2 className="w-8 h-8 text-gray-400 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Ready to get started?
        </h3>
        <p className="text-sm text-gray-500 mb-4 max-w-md mx-auto">
          Get in touch and we&apos;ll show you how Central can simplify HR for
          your team.
        </p>
        <Link
          href="/contact"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors"
        >
          <Building2 className="w-4 h-4" />
          Contact Us
        </Link>
      </div>
    </div>
  );
}
