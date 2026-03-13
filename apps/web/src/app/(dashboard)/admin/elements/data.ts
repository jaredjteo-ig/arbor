/**
 * Demo data for the admin dashboard.
 *
 * In production these would come from the /admin/* API endpoints.
 * Structured to match the API response shapes from admin.py.
 */

/* ── Types ──────────────────────────────────────────────────── */

export type UpdateStatus =
  | "draft"
  | "in_review"
  | "approved"
  | "published"
  | "rejected";

export type UpdateUrgency = "low" | "medium" | "high" | "critical";

export interface RegulatoryUpdateRow {
  id: string;
  title: string;
  source: string;
  urgency: UpdateUrgency;
  status: UpdateStatus;
  effectiveDate: string;
  description: string;
  domainsAffected: string[];
  affectedProvisionsCount: number;
}

export interface ActivityItem {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  detail: string;
}

export interface KbDomain {
  id: string;
  name: string;
  provisionCount: number;
  lastUpdated: string;
  staleness: "current" | "review-soon" | "stale";
}

export interface FeedbackItem {
  id: string;
  date: string;
  queryExcerpt: string;
  feedbackType: "thumbs_down";
  category: "inaccurate" | "incomplete" | "unclear" | "other";
  status: "pending" | "reviewed" | "resolved";
}

export interface AuditEntry {
  id: string;
  queryExcerpt: string;
  responseExcerpt: string;
  confidenceScore: number;
  provisionsCited: string[];
  riskTier: "green" | "amber" | "red";
  auditorNotes: string;
}

/* ── Demo Data ──────────────────────────────────────────────── */

export const REGULATORY_UPDATES: RegulatoryUpdateRow[] = [
  {
    id: "upd-001",
    title: "Employment Act Amendment - Key Employment Terms",
    source: "Ministry of Manpower",
    urgency: "critical",
    status: "published",
    effectiveDate: "2026-04-01",
    description:
      "Mandatory KET written terms for all employees, expanding existing requirements.",
    domainsAffected: ["Employment Act"],
    affectedProvisionsCount: 12,
  },
  {
    id: "upd-002",
    title: "CPF Contribution Rate Changes for Senior Workers",
    source: "CPF Board",
    urgency: "high",
    status: "approved",
    effectiveDate: "2027-01-01",
    description:
      "Phased increase in CPF contribution rates for workers aged 55 and above.",
    domainsAffected: ["CPF"],
    affectedProvisionsCount: 8,
  },
  {
    id: "upd-003",
    title: "Workplace Safety Penalty Framework Update",
    source: "Ministry of Manpower",
    urgency: "medium",
    status: "in_review",
    effectiveDate: "2026-07-01",
    description:
      "Revised penalty amounts and enforcement procedures for WSH violations.",
    domainsAffected: ["Workplace Safety & Health"],
    affectedProvisionsCount: 5,
  },
  {
    id: "upd-004",
    title: "Fair Employment Practice Guidelines - AI Hiring",
    source: "TAFEP",
    urgency: "medium",
    status: "draft",
    effectiveDate: "2026-10-01",
    description:
      "New guidelines on use of AI and algorithmic tools in recruitment and selection.",
    domainsAffected: ["Fair Employment"],
    affectedProvisionsCount: 3,
  },
  {
    id: "upd-005",
    title: "Foreign Worker Levy Adjustment Q3 2026",
    source: "Ministry of Manpower",
    urgency: "low",
    status: "rejected",
    effectiveDate: "2026-07-01",
    description:
      "Proposed adjustment to foreign worker levy tiers (rejected due to incomplete impact analysis).",
    domainsAffected: ["Foreign Manpower"],
    affectedProvisionsCount: 2,
  },
];

export const RECENT_ACTIVITY: ActivityItem[] = [
  {
    id: "act-1",
    timestamp: "12 Mar 2026, 14:32",
    actor: "Sarah Lim",
    action: "Published",
    detail: "Employment Act Amendment - Key Employment Terms",
  },
  {
    id: "act-2",
    timestamp: "12 Mar 2026, 11:15",
    actor: "James Tan",
    action: "Approved",
    detail: "CPF Contribution Rate Changes for Senior Workers",
  },
  {
    id: "act-3",
    timestamp: "11 Mar 2026, 16:48",
    actor: "System",
    action: "Flagged stale",
    detail: "3 PDPA provisions past review date",
  },
  {
    id: "act-4",
    timestamp: "11 Mar 2026, 09:22",
    actor: "Wei Ming",
    action: "Submitted for review",
    detail: "Workplace Safety Penalty Framework Update",
  },
  {
    id: "act-5",
    timestamp: "10 Mar 2026, 15:05",
    actor: "Sarah Lim",
    action: "Rejected",
    detail: "Foreign Worker Levy Adjustment Q3 2026",
  },
];

export const KB_DOMAINS: KbDomain[] = [
  {
    id: "kb-ea",
    name: "Employment Act",
    provisionCount: 234,
    lastUpdated: "12 Mar 2026",
    staleness: "current",
  },
  {
    id: "kb-cpf",
    name: "CPF",
    provisionCount: 189,
    lastUpdated: "8 Mar 2026",
    staleness: "current",
  },
  {
    id: "kb-wsh",
    name: "Workplace Safety & Health",
    provisionCount: 142,
    lastUpdated: "25 Feb 2026",
    staleness: "review-soon",
  },
  {
    id: "kb-fe",
    name: "Fair Employment",
    provisionCount: 97,
    lastUpdated: "2 Mar 2026",
    staleness: "current",
  },
  {
    id: "kb-fm",
    name: "Foreign Manpower",
    provisionCount: 118,
    lastUpdated: "10 Jan 2026",
    staleness: "stale",
  },
  {
    id: "kb-pdpa",
    name: "PDPA",
    provisionCount: 67,
    lastUpdated: "5 Dec 2025",
    staleness: "stale",
  },
];

export const FEEDBACK_ITEMS: FeedbackItem[] = [
  {
    id: "fb-1",
    date: "12 Mar 2026",
    queryExcerpt: "Can I deduct salary for late coming?",
    feedbackType: "thumbs_down",
    category: "inaccurate",
    status: "pending",
  },
  {
    id: "fb-2",
    date: "12 Mar 2026",
    queryExcerpt: "Maternity leave eligibility for contract workers",
    feedbackType: "thumbs_down",
    category: "incomplete",
    status: "pending",
  },
  {
    id: "fb-3",
    date: "11 Mar 2026",
    queryExcerpt: "How to calculate retrenchment benefit?",
    feedbackType: "thumbs_down",
    category: "unclear",
    status: "reviewed",
  },
  {
    id: "fb-4",
    date: "11 Mar 2026",
    queryExcerpt: "S Pass quota for manufacturing sector",
    feedbackType: "thumbs_down",
    category: "inaccurate",
    status: "pending",
  },
  {
    id: "fb-5",
    date: "10 Mar 2026",
    queryExcerpt: "Overtime rates for shift workers on public holidays",
    feedbackType: "thumbs_down",
    category: "incomplete",
    status: "resolved",
  },
  {
    id: "fb-6",
    date: "9 Mar 2026",
    queryExcerpt: "PDPA obligations for employee medical records",
    feedbackType: "thumbs_down",
    category: "other",
    status: "pending",
  },
  {
    id: "fb-7",
    date: "8 Mar 2026",
    queryExcerpt: "Notice period for probationary employees",
    feedbackType: "thumbs_down",
    category: "unclear",
    status: "reviewed",
  },
  {
    id: "fb-8",
    date: "7 Mar 2026",
    queryExcerpt: "CPF contribution cap for bonuses",
    feedbackType: "thumbs_down",
    category: "inaccurate",
    status: "resolved",
  },
];

export const AUDIT_ENTRIES: AuditEntry[] = [
  {
    id: "aud-1",
    queryExcerpt:
      "Employee refusing to work overtime despite contractual obligation",
    responseExcerpt:
      "Under EA s38, an employee may refuse overtime that exceeds 72 hours/month. The employer must check whether the monthly cap has been reached before...",
    confidenceScore: 0.92,
    provisionsCited: ["EA s38", "EA s40(1)", "EA Part IV"],
    riskTier: "amber",
    auditorNotes: "",
  },
  {
    id: "aud-2",
    queryExcerpt: "CPF contribution for employee turning 55 mid-month",
    responseExcerpt:
      "CPF contributions change from the month following the employee's 55th birthday. For the month in which the employee turns 55, the existing rates apply...",
    confidenceScore: 0.95,
    provisionsCited: ["CPF Act s7(1)", "CPF Regs Sch1"],
    riskTier: "green",
    auditorNotes: "",
  },
  {
    id: "aud-3",
    queryExcerpt: "Can employer monitor employee personal devices under PDPA?",
    responseExcerpt:
      "PDPA requires consent for collection of personal data. Monitoring personal devices without explicit consent would likely breach the Consent Obligation...",
    confidenceScore: 0.78,
    provisionsCited: ["PDPA s13", "PDPA s14", "PDPC Advisory Guidelines"],
    riskTier: "red",
    auditorNotes: "",
  },
  {
    id: "aud-4",
    queryExcerpt: "Retrenchment benefits for employee with 8 years of service",
    responseExcerpt:
      "While not legally mandatory, the prevailing norm for retrenchment benefits is 2 weeks to 1 month salary per year of service. For 8 years, this typically...",
    confidenceScore: 0.88,
    provisionsCited: ["EA s45B", "MOM Advisory", "Tripartite Guidelines"],
    riskTier: "green",
    auditorNotes: "",
  },
  {
    id: "aud-5",
    queryExcerpt:
      "Foreign worker dormitory standards after COVID-19 regulations",
    responseExcerpt:
      "Post-COVID regulations under FEDA require minimum 4.5 sqm per resident, improved ventilation standards, and quarterly health inspections...",
    confidenceScore: 0.84,
    provisionsCited: ["FEDA s2", "FEDA Regs 2021", "MOM Circular 2024/03"],
    riskTier: "amber",
    auditorNotes: "",
  },
];
