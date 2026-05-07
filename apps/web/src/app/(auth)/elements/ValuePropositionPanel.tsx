import { Wallet, Sparkles, LayoutGrid } from "lucide-react";

const features = [
  {
    icon: Wallet,
    title: "Payroll & CPF",
    description:
      "Run payroll, generate CPF files, create payslips \u2014 all built in",
  },
  {
    icon: Sparkles,
    title: "AI Compliance Advisor",
    description:
      "Answers grounded in Singapore employment law with source citations",
  },
  {
    icon: LayoutGrid,
    title: "Full HR Suite",
    description:
      "Leave, claims, attendance, shifts, employee management \u2014 everything in one place",
  },
] as const;

/**
 * Left-side value proposition panel shown on auth pages (md+ only).
 * Communicates what Arbor does before the user even logs in.
 */
export function ValuePropositionPanel() {
  return (
    <div className="hidden md:flex md:w-1/2 flex-col justify-between bg-[var(--color-primary)] px-12 py-16 lg:px-16">
      {/* Top: Logo + tagline */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="flex items-center justify-center rounded-lg border-2 border-white/30 bg-white/10 font-bold text-white w-11 h-11 text-base tracking-tight">
            HR
          </div>
          <span className="text-2xl font-bold text-white tracking-tight">
            Central
          </span>
        </div>
        <p className="mt-1 text-base text-white/70">
          Your Complete HR Platform
        </p>
      </div>

      {/* Middle: Feature highlights */}
      <div className="space-y-8">
        {features.map(({ icon: Icon, title, description }) => (
          <div key={title} className="flex gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/10">
              <Icon className="h-5 w-5 text-white" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">{title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-white/70">
                {description}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Bottom: Trust signal */}
      <p className="text-xs leading-relaxed text-white/50">
        Covering Employment Act, CPF, EFMA, WSH, TAFEP, and Tax/IRAS regulations
      </p>
    </div>
  );
}
