/* ── Action Registry — Intent Classification and Routing ──── */
/* T113: Classifies user commands into action types and extracts
   parameters for routing to the correct handler.                */

/* ── Types ────────────────────────────────────────────────── */

export type ActionType =
  | "navigate"
  | "calculate"
  | "advisory"
  | "compliance"
  | "document";

export interface ClassifiedIntent {
  type: ActionType;
  params: Record<string, string>;
  /** Destination path for navigate actions */
  navigateTo?: string;
  /** Specific calculator for calculate actions */
  calculator?: "cpf" | "leave" | "salary";
  /** Friendly label for the action */
  label: string;
}

/* ── Navigation patterns ─────────────────────────────────── */

const NAVIGATION_MAP: Record<string, { path: string; label: string }> = {
  dashboard: { path: "/", label: "Dashboard" },
  home: { path: "/", label: "Dashboard" },
  advisory: { path: "/advisory", label: "Advisory" },
  compliance: { path: "/compliance", label: "Compliance" },
  calculators: { path: "/calculators", label: "Calculators" },
  calculator: { path: "/calculators", label: "Calculators" },
  documents: { path: "/documents", label: "Documents" },
  templates: { path: "/documents", label: "Documents" },
  emergency: { path: "/emergency", label: "Emergency Guides" },
  analytics: { path: "/analytics", label: "Analytics" },
  settings: { path: "/settings", label: "Settings" },
  help: { path: "/help", label: "Help" },
  alerts: { path: "/alerts", label: "Alerts" },
  // Fuzzy / alternative patterns
  tadm: { path: "/emergency", label: "Emergency Guides" },
  "workplace injury": { path: "/emergency", label: "Emergency Guides" },
  "work injury": { path: "/emergency", label: "Emergency Guides" },
  "cpf calculator": { path: "/calculators", label: "CPF Calculator" },
  "leave calculator": { path: "/calculators", label: "Leave Calculator" },
  "salary calculator": { path: "/calculators", label: "Salary Calculator" },
  "deep advisory": { path: "/advisory", label: "Advisory Workspace" },
  research: { path: "/advisory", label: "Advisory Workspace" },
  // Employee-scoped routes
  "my dashboard": { path: "/my-dashboard", label: "My Dashboard" },
  "my leave": { path: "/my-leave", label: "My Leave" },
  "leave balance": { path: "/my-leave", label: "My Leave" },
  policies: { path: "/policies", label: "Company Policies" },
  "company policies": { path: "/policies", label: "Company Policies" },
  "leave policy": { path: "/policies", label: "Company Policies" },
  employees: { path: "/employees", label: "Employees" },
};

const NAVIGATION_PREFIXES = [
  "take me to",
  "go to",
  "navigate to",
  "show me",
  "show",
  "open",
  "bring up",
  "switch to",
];

/* ── Calculator patterns ─────────────────────────────────── */

const CPF_KEYWORDS = [
  "cpf",
  "central provident fund",
  "cpf contribution",
  "employer contribution",
  "employee contribution",
];

const LEAVE_KEYWORDS = [
  "leave entitlement",
  "annual leave",
  "sick leave",
  "maternity leave",
  "paternity leave",
  "leave days",
  "leave calculation",
];

const SALARY_KEYWORDS = [
  "salary breakdown",
  "net pay",
  "salary calculation",
  "take home pay",
  "net salary",
  "salary deduction",
];

const CALCULATE_PREFIXES = [
  "calculate",
  "compute",
  "what's",
  "what is",
  "how much",
  "what are",
];

/* ── Compliance patterns ─────────────────────────────────── */

const COMPLIANCE_KEYWORDS = [
  "compliance",
  "compliant",
  "compliance check",
  "compliance status",
  "am i compliant",
  "check my compliance",
  "gap analysis",
  "regulatory",
];

/* ── Document patterns ───────────────────────────────────── */

const DOCUMENT_KEYWORDS = [
  "generate",
  "create a document",
  "create document",
  "employment contract",
  "ket",
  "key employment terms",
  "letter of appointment",
  "offer letter",
  "termination letter",
  "warning letter",
  "payslip",
];

/* ── Parameter extraction ────────────────────────────────── */

function extractSalary(query: string): string | null {
  // Match patterns like "$5000", "$5,000", "5000 dollars", "salary 5000", "salary of $5000"
  const patterns = [
    /\$\s*([\d,]+(?:\.\d{2})?)/,
    /([\d,]+(?:\.\d{2})?)\s*(?:dollars?|sgd)/i,
    /salary\s+(?:of\s+)?(?:\$\s*)?([\d,]+(?:\.\d{2})?)/i,
    /(?:for|of)\s+(?:\$\s*)?([\d,]+(?:\.\d{2})?)/i,
  ];
  for (const pattern of patterns) {
    const match = query.match(pattern);
    if (match) return match[1].replace(/,/g, "");
  }
  return null;
}

function extractAge(query: string): string | null {
  const patterns = [
    /age\s+(\d{1,3})/i,
    /(\d{1,3})\s*(?:years?\s+old|yo|y\/o)/i,
    /aged?\s+(\d{1,3})/i,
  ];
  for (const pattern of patterns) {
    const match = query.match(pattern);
    if (match) {
      const age = parseInt(match[1], 10);
      if (age >= 15 && age <= 100) return match[1];
    }
  }
  return null;
}

function extractCitizenship(query: string): string | null {
  const lower = query.toLowerCase();
  if (
    lower.includes("singaporean") ||
    lower.includes("citizen") ||
    /\bsc\b/.test(lower)
  ) {
    return "sc";
  }
  if (lower.includes("permanent resident") || /\bpr\b/.test(lower)) {
    return "pr";
  }
  if (
    lower.includes("foreigner") ||
    lower.includes("foreign") ||
    /\bep\b/.test(lower)
  ) {
    return "foreigner";
  }
  return null;
}

function extractYearsOfService(query: string): string | null {
  const patterns = [
    /(\d+)\s*(?:years?\s+of\s+service)/i,
    /served?\s+(\d+)\s*years?/i,
    /(\d+)\s*years?\s+(?:with|at|in)/i,
  ];
  for (const pattern of patterns) {
    const match = query.match(pattern);
    if (match) return match[1];
  }
  return null;
}

/* ── Core classifier ─────────────────────────────────────── */

/**
 * Classify a user query into an action type with extracted parameters.
 * Priority order: navigate > calculate > compliance > document > advisory (fallback).
 */
export function classifyIntent(query: string): ClassifiedIntent {
  const lower = query.toLowerCase().trim();

  // 1. Navigation — check for explicit navigation commands
  for (const prefix of NAVIGATION_PREFIXES) {
    if (lower.startsWith(prefix)) {
      const target = lower.slice(prefix.length).trim();
      // Try exact key match first
      for (const [keyword, { path, label }] of Object.entries(NAVIGATION_MAP)) {
        if (target === keyword || target.includes(keyword)) {
          return {
            type: "navigate",
            params: { target: keyword },
            navigateTo: path,
            label: `Navigate to ${label}`,
          };
        }
      }
      // Fuzzy match: check if any keyword is a substring of the target
      for (const [keyword, { path, label }] of Object.entries(NAVIGATION_MAP)) {
        if (keyword.includes(target) || target.includes(keyword)) {
          return {
            type: "navigate",
            params: { target: keyword },
            navigateTo: path,
            label: `Navigate to ${label}`,
          };
        }
      }
    }
  }

  // 2. Calculator — check for calculation keywords
  const hasCalculatePrefix = CALCULATE_PREFIXES.some((p) =>
    lower.startsWith(p),
  );
  const hasCpf = CPF_KEYWORDS.some((k) => lower.includes(k));
  const hasLeave = LEAVE_KEYWORDS.some((k) => lower.includes(k));
  const hasSalary = SALARY_KEYWORDS.some((k) => lower.includes(k));

  if (hasCalculatePrefix || hasCpf || hasLeave || hasSalary) {
    const params: Record<string, string> = {};

    if (hasCpf) {
      const salary = extractSalary(query);
      const age = extractAge(query);
      const citizenship = extractCitizenship(query);
      if (salary) params.salary = salary;
      if (age) params.age = age;
      if (citizenship) params.citizenship = citizenship;

      return {
        type: "calculate",
        params,
        calculator: "cpf",
        label: "CPF Contribution Calculator",
      };
    }

    if (hasLeave) {
      const yos = extractYearsOfService(query);
      if (yos) params.years_of_service = yos;

      return {
        type: "calculate",
        params,
        calculator: "leave",
        label: "Leave Entitlement Calculator",
      };
    }

    if (hasSalary) {
      const salary = extractSalary(query);
      if (salary) params.salary = salary;

      return {
        type: "calculate",
        params,
        calculator: "salary",
        label: "Salary Breakdown Calculator",
      };
    }

    // Generic calculate with CPF as default
    const salary = extractSalary(query);
    const age = extractAge(query);
    const citizenship = extractCitizenship(query);
    if (salary) params.salary = salary;
    if (age) params.age = age;
    if (citizenship) params.citizenship = citizenship;

    return {
      type: "calculate",
      params,
      calculator: "cpf",
      label: "CPF Contribution Calculator",
    };
  }

  // 3. Compliance — check for compliance keywords
  if (COMPLIANCE_KEYWORDS.some((k) => lower.includes(k))) {
    return {
      type: "compliance",
      params: {},
      label: "Compliance Check",
    };
  }

  // 4. Document — check for document generation keywords
  if (DOCUMENT_KEYWORDS.some((k) => lower.includes(k))) {
    return {
      type: "document",
      params: {},
      navigateTo: "/documents",
      label: "Document Generation",
    };
  }

  // 5. Advisory — fallback for any HR question
  return {
    type: "advisory",
    params: {},
    label: "HR Advisory",
  };
}
