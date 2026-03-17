"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { classifyIntent, type ClassifiedIntent } from "./action-registry";
import { calculatorsApi } from "@/services/api/calculators";
import { complianceApi } from "@/services/api/compliance";

/* ── Types ────────────────────────────────────────────────── */

interface CommandResult {
  type: "text" | "navigation" | "calculation" | "error";
  content: string;
  citations?: Array<{ label: string; authority: string }>;
  riskTier?: string;
  navigateTo?: string;
  /** Structured calculator result */
  calculatorResult?: CalculatorDisplayResult;
}

export interface CalculatorDisplayResult {
  calculatorName: string;
  inputs: Array<{ label: string; value: string }>;
  results: Array<{ label: string; value: string; highlight?: boolean }>;
  source: string;
  linkTo: string;
}

interface ShadowAgentState {
  /** Whether the command surface overlay is open */
  isCommandOpen: boolean;
  /** Whether the shadow agent has something to surface (attention state) */
  hasAttention: boolean;
  /** Whether a command is currently being processed */
  isProcessing: boolean;
  /** Whether the current page is the advisory deep workspace */
  isAdvisoryPage: boolean;
  /** Recent commands for suggestion list */
  recentCommands: string[];
}

interface ShadowAgentActions {
  /** Open the command surface */
  openCommand: () => void;
  /** Close the command surface */
  closeCommand: () => void;
  /** Toggle the command surface */
  toggleCommand: () => void;
  /** Submit a command and get a result */
  submitCommand: (query: string) => Promise<CommandResult | null>;
  /** Set attention state (agent has something to surface) */
  setAttention: (value: boolean) => void;
}

type ShadowAgentContextValue = ShadowAgentState & ShadowAgentActions;

/* ── Context ──────────────────────────────────────────────── */

const ShadowAgentCtx = createContext<ShadowAgentContextValue | null>(null);

/* ── Action Handlers ─────────────────────────────────────── */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

/** Handle calculator dispatch (T115) */
async function handleCalculate(
  intent: ClassifiedIntent,
): Promise<CommandResult> {
  const { calculator, params } = intent;

  try {
    if (calculator === "cpf") {
      const salary = params.salary ? parseFloat(params.salary) : 5000;
      const age = params.age ? parseInt(params.age, 10) : 30;
      const citizenship = params.citizenship || "sc";

      const result = await calculatorsApi.cpf({
        gross_salary: salary,
        employee_age: age,
        citizenship_status: citizenship,
      });

      return {
        type: "calculation",
        content: `CPF contributions calculated for $${salary.toLocaleString()} salary.`,
        calculatorResult: {
          calculatorName: "CPF Contribution Calculator",
          inputs: [
            { label: "Gross Salary", value: `$${salary.toLocaleString()}` },
            { label: "Age", value: String(age) },
            {
              label: "Citizenship",
              value:
                citizenship === "sc"
                  ? "Singaporean"
                  : citizenship === "pr"
                    ? "Permanent Resident"
                    : "Foreigner",
            },
          ],
          results: [
            {
              label: "Employer Contribution",
              value: `$${result.employer_contribution.toFixed(2)}`,
            },
            {
              label: "Employee Contribution",
              value: `$${result.employee_contribution.toFixed(2)}`,
            },
            {
              label: "Total Contribution",
              value: `$${result.total_contribution.toFixed(2)}`,
              highlight: true,
            },
            {
              label: "Employer Rate",
              value: `${(result.employer_rate * 100).toFixed(1)}%`,
            },
            {
              label: "Employee Rate",
              value: `${(result.employee_rate * 100).toFixed(1)}%`,
            },
            { label: "Age Band", value: result.age_band },
          ],
          source: "Central Provident Fund Act",
          linkTo: "/calculators",
        },
      };
    }

    if (calculator === "leave") {
      const yos = params.years_of_service
        ? parseInt(params.years_of_service, 10)
        : 1;

      const result = await calculatorsApi.leave({
        years_of_service: yos,
        employment_type: "full-time",
      });

      return {
        type: "calculation",
        content: `Leave entitlements for ${yos} year(s) of service.`,
        calculatorResult: {
          calculatorName: "Leave Entitlement Calculator",
          inputs: [
            { label: "Years of Service", value: String(yos) },
            { label: "Employment Type", value: "Full-time" },
          ],
          results: [
            {
              label: "Annual Leave",
              value: `${result.annual_leave_days} days`,
              highlight: true,
            },
            {
              label: "Sick Leave",
              value: `${result.sick_leave_days} days`,
            },
            {
              label: "Hospitalisation Leave",
              value: `${result.hospitalisation_leave_days} days`,
            },
          ],
          source: "Employment Act",
          linkTo: "/calculators",
        },
      };
    }

    if (calculator === "salary") {
      const salary = params.salary ? parseFloat(params.salary) : 5000;

      const result = await calculatorsApi.salary({
        gross_salary: salary,
      });

      return {
        type: "calculation",
        content: `Salary breakdown for $${salary.toLocaleString()}.`,
        calculatorResult: {
          calculatorName: "Salary Breakdown Calculator",
          inputs: [
            {
              label: "Gross Salary",
              value: `$${salary.toLocaleString()}`,
            },
          ],
          results: [
            {
              label: "Net Pay (Est.)",
              value: `$${result.estimated_net_pay.toFixed(2)}`,
              highlight: true,
            },
            {
              label: "CPF Employee",
              value: `$${result.cpf_employee_deduction.toFixed(2)}`,
            },
            {
              label: "CPF Employer",
              value: `$${result.cpf_employer_contribution.toFixed(2)}`,
            },
            {
              label: "Total Cost to Employer",
              value: `$${result.total_cost_to_employer.toFixed(2)}`,
            },
          ],
          source: "CPF Act & Employment Act",
          linkTo: "/calculators",
        },
      };
    }

    return {
      type: "error",
      content: "Calculator type not recognized.",
    };
  } catch {
    return {
      type: "error",
      content:
        "Unable to run the calculation. Please try using the full calculator page.",
    };
  }
}

/** Handle compliance check */
async function handleCompliance(): Promise<CommandResult> {
  try {
    const result = await complianceApi.status(1);

    const statusLabel =
      result.overall_status === "compliant"
        ? "Your organization is currently compliant."
        : result.overall_status === "partial"
          ? "Your organization has some compliance gaps."
          : "Your organization needs attention on compliance.";

    return {
      type: "text",
      content: statusLabel,
      riskTier:
        result.overall_status === "compliant"
          ? "green"
          : result.overall_status === "partial"
            ? "amber"
            : "red",
      navigateTo: "/compliance",
    };
  } catch {
    // If the API fails, navigate to compliance page instead
    return {
      type: "navigation",
      content: "Opening compliance dashboard...",
      navigateTo: "/compliance",
    };
  }
}

/** Handle advisory query (T114: command mode) */
async function handleAdvisory(query: string): Promise<CommandResult> {
  const token = getToken();

  if (!token) {
    return {
      type: "error",
      content: "Please sign in to use the AI assistant.",
    };
  }

  try {
    const response = await fetch(`${API_BASE}/advisory/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        query,
        response_format: "command",
      }),
    });

    if (!response.ok) {
      return {
        type: "error",
        content: "Unable to process your request right now. Please try again.",
      };
    }

    const data = await response.json();

    // Handle Nexus envelope unwrapping
    let result = data;
    if (data?.data?.content && typeof data.data.content === "string") {
      try {
        result = JSON.parse(data.data.content);
      } catch {
        result = data;
      }
    }

    // Extract and truncate content for command surface (T114)
    const fullContent =
      result.response || result.response_text || "No response generated.";
    const truncatedContent =
      fullContent.length > 300
        ? fullContent.slice(0, 300) + "..."
        : fullContent;

    return {
      type: "text",
      content: truncatedContent,
      citations: (result.provisions_cited || []).map(
        (p: { title: string; authority_level: string }) => ({
          label: p.title,
          authority: p.authority_level,
        }),
      ),
      riskTier: result.risk_tier,
    };
  } catch {
    return {
      type: "error",
      content: "Connection error. Please check your internet and try again.",
    };
  }
}

/* ── Provider ─────────────────────────────────────────────── */

const MAX_RECENT_COMMANDS = 10;

export function ShadowAgentProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [hasAttention, setHasAttention] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recentCommands, setRecentCommands] = useState<string[]>([]);

  const isAdvisoryPage = pathname === "/advisory";

  const openCommand = useCallback(() => setIsCommandOpen(true), []);
  const closeCommand = useCallback(() => setIsCommandOpen(false), []);
  const toggleCommand = useCallback(
    () => setIsCommandOpen((prev) => !prev),
    [],
  );
  const setAttention = useCallback(
    (value: boolean) => setHasAttention(value),
    [],
  );

  const submitCommand = useCallback(
    async (query: string): Promise<CommandResult | null> => {
      setIsProcessing(true);

      // Track recent commands
      setRecentCommands((prev) => {
        const updated = [query, ...prev.filter((c) => c !== query)];
        return updated.slice(0, MAX_RECENT_COMMANDS);
      });

      try {
        // Classify intent using the action registry (T113)
        const intent = classifyIntent(query);

        switch (intent.type) {
          case "navigate": {
            // T116: Enhanced navigation with confirmation
            const target = intent.navigateTo || "/";
            router.push(target);
            return {
              type: "navigation",
              content: `Navigating to ${intent.label.replace("Navigate to ", "")}...`,
              navigateTo: target,
            };
          }

          case "calculate": {
            // T115: Calculator dispatch
            return await handleCalculate(intent);
          }

          case "compliance": {
            // Compliance check
            return await handleCompliance();
          }

          case "document": {
            // Document generation — navigate to documents page
            const target = intent.navigateTo || "/documents";
            router.push(target);
            return {
              type: "navigation",
              content: "Opening document templates...",
              navigateTo: target,
            };
          }

          case "advisory":
          default: {
            // T114: Advisory in command mode
            return await handleAdvisory(query);
          }
        }
      } catch {
        return {
          type: "error",
          content: "Something went wrong. Please try again.",
        };
      } finally {
        setIsProcessing(false);
      }
    },
    [router],
  );

  const value: ShadowAgentContextValue = {
    isCommandOpen,
    hasAttention,
    isProcessing,
    isAdvisoryPage,
    recentCommands,
    openCommand,
    closeCommand,
    toggleCommand,
    submitCommand,
    setAttention,
  };

  return (
    <ShadowAgentCtx.Provider value={value}>{children}</ShadowAgentCtx.Provider>
  );
}

/* ── Hook ─────────────────────────────────────────────────── */

export function useShadowAgent(): ShadowAgentContextValue {
  const context = useContext(ShadowAgentCtx);
  if (!context) {
    throw new Error("useShadowAgent must be used within ShadowAgentProvider");
  }
  return context;
}
