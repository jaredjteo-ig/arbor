"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, HelpCircle } from "lucide-react";
import { AppButton } from "@/components/design-system/AppButton";
import { AppInput } from "@/components/design-system/AppInput";
import { AppCard } from "@/components/design-system/AppCard";

export interface CompanyProfileData {
  companyName: string;
  sector: string;
  totalHeadcount: number;
  headcountLocal: number;
  headcountPR: number;
  headcountEP: number;
  headcountSP: number;
  headcountWP: number;
  salaryRangeMin: number;
  salaryRangeMax: number;
}

interface CompanyProfileStepProps {
  onNext: (data: CompanyProfileData) => void;
  onBack: () => void;
  initialData?: Partial<CompanyProfileData>;
}

const SECTORS = [
  { value: "", label: "Select your sector" },
  { value: "services", label: "Services (F&B, retail, hospitality, etc.)" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "construction", label: "Construction" },
  { value: "process", label: "Process (chemicals, pharmaceuticals)" },
  { value: "marine", label: "Marine (shipyard, offshore)" },
  { value: "tech", label: "Technology / IT" },
  { value: "finance", label: "Financial Services" },
  { value: "healthcare", label: "Healthcare" },
  { value: "education", label: "Education" },
  { value: "other", label: "Other" },
];

function WhyWeAsk({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      type="button"
      onClick={() => setOpen(!open)}
      className="flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline mt-1"
    >
      <HelpCircle className="w-3.5 h-3.5" />
      <span>Why do we ask this?</span>
      {open ? (
        <ChevronUp className="w-3 h-3" />
      ) : (
        <ChevronDown className="w-3 h-3" />
      )}
      {open && (
        <span className="block text-[var(--color-gray-500)] text-xs font-normal ml-1">
          {text}
        </span>
      )}
    </button>
  );
}

export function CompanyProfileStep({
  onNext,
  onBack,
  initialData,
}: CompanyProfileStepProps) {
  const [companyName, setCompanyName] = useState(
    initialData?.companyName ?? "",
  );
  const [sector, setSector] = useState(initialData?.sector ?? "");
  const [totalHeadcount, setTotalHeadcount] = useState(
    initialData?.totalHeadcount ?? 0,
  );
  const [headcountLocal, setHeadcountLocal] = useState(
    initialData?.headcountLocal ?? 0,
  );
  const [headcountPR, setHeadcountPR] = useState(initialData?.headcountPR ?? 0);
  const [headcountEP, setHeadcountEP] = useState(initialData?.headcountEP ?? 0);
  const [headcountSP, setHeadcountSP] = useState(initialData?.headcountSP ?? 0);
  const [headcountWP, setHeadcountWP] = useState(initialData?.headcountWP ?? 0);
  const [salaryRangeMin, setSalaryRangeMin] = useState(
    initialData?.salaryRangeMin ?? 0,
  );
  const [salaryRangeMax, setSalaryRangeMax] = useState(
    initialData?.salaryRangeMax ?? 0,
  );

  const [showWorkforce, setShowWorkforce] = useState(false);
  const [showSalary, setShowSalary] = useState(false);

  const canProceed = companyName.trim() !== "" && sector !== "";

  function handleSubmit() {
    onNext({
      companyName,
      sector,
      totalHeadcount,
      headcountLocal,
      headcountPR,
      headcountEP,
      headcountSP,
      headcountWP,
      salaryRangeMin,
      salaryRangeMax,
    });
  }

  return (
    <div className="max-w-lg mx-auto">
      <h2 className="text-xl font-bold text-[var(--color-gray-900)] mb-1">
        Company Profile
      </h2>
      <p className="text-sm text-[var(--color-gray-500)] mb-6">
        Tell us about your company so we can tailor our advice. Only company
        name and sector are required — you can fill in the rest later.
      </p>

      <div className="space-y-5">
        {/* Company name */}
        <AppInput
          label="Company Name"
          value={companyName}
          onChange={(e) => setCompanyName((e.target as HTMLInputElement).value)}
          placeholder="e.g. Acme Pte Ltd"
        />

        {/* Sector */}
        <div>
          <AppInput
            variant="select"
            label="Sector"
            options={SECTORS}
            value={sector}
            onChange={(e) => setSector((e.target as HTMLSelectElement).value)}
          />
          <WhyWeAsk text="Your sector determines foreign worker quota limits and levy rates." />
        </div>

        {/* Total headcount */}
        <div>
          <AppInput
            variant="number"
            label="Total Employees"
            value={totalHeadcount || ""}
            onChange={(e) =>
              setTotalHeadcount(
                parseInt((e.target as HTMLInputElement).value) || 0,
              )
            }
            placeholder="e.g. 25"
          />
          <WhyWeAsk text="We use this to calculate your foreign worker quota headroom." />
        </div>

        {/* Workforce breakdown (optional, collapsible) */}
        <div>
          <button
            type="button"
            onClick={() => setShowWorkforce(!showWorkforce)}
            className="flex items-center gap-2 text-sm font-medium text-[var(--color-primary)] hover:underline"
          >
            {showWorkforce ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
            Workforce Breakdown (optional)
          </button>

          {showWorkforce && (
            <AppCard variant="flat" className="mt-3">
              <div className="grid grid-cols-2 gap-3">
                <AppInput
                  variant="number"
                  label="Local (SC)"
                  value={headcountLocal || ""}
                  onChange={(e) =>
                    setHeadcountLocal(
                      parseInt((e.target as HTMLInputElement).value) || 0,
                    )
                  }
                />
                <AppInput
                  variant="number"
                  label="PR"
                  value={headcountPR || ""}
                  onChange={(e) =>
                    setHeadcountPR(
                      parseInt((e.target as HTMLInputElement).value) || 0,
                    )
                  }
                />
                <AppInput
                  variant="number"
                  label="EP"
                  value={headcountEP || ""}
                  onChange={(e) =>
                    setHeadcountEP(
                      parseInt((e.target as HTMLInputElement).value) || 0,
                    )
                  }
                />
                <AppInput
                  variant="number"
                  label="S Pass"
                  value={headcountSP || ""}
                  onChange={(e) =>
                    setHeadcountSP(
                      parseInt((e.target as HTMLInputElement).value) || 0,
                    )
                  }
                />
                <AppInput
                  variant="number"
                  label="WP"
                  value={headcountWP || ""}
                  onChange={(e) =>
                    setHeadcountWP(
                      parseInt((e.target as HTMLInputElement).value) || 0,
                    )
                  }
                />
              </div>
            </AppCard>
          )}
        </div>

        {/* Salary range (optional, collapsible) */}
        <div>
          <button
            type="button"
            onClick={() => setShowSalary(!showSalary)}
            className="flex items-center gap-2 text-sm font-medium text-[var(--color-primary)] hover:underline"
          >
            {showSalary ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
            Salary Range (optional)
          </button>

          {showSalary && (
            <AppCard variant="flat" className="mt-3">
              <div className="grid grid-cols-2 gap-3">
                <AppInput
                  variant="number"
                  label="Minimum ($)"
                  value={salaryRangeMin || ""}
                  onChange={(e) =>
                    setSalaryRangeMin(
                      parseInt((e.target as HTMLInputElement).value) || 0,
                    )
                  }
                  placeholder="e.g. 2000"
                />
                <AppInput
                  variant="number"
                  label="Maximum ($)"
                  value={salaryRangeMax || ""}
                  onChange={(e) =>
                    setSalaryRangeMax(
                      parseInt((e.target as HTMLInputElement).value) || 0,
                    )
                  }
                  placeholder="e.g. 8000"
                />
              </div>
            </AppCard>
          )}
        </div>
      </div>

      <div className="flex gap-3 mt-8">
        <AppButton variant="outlined" onClick={onBack}>
          Back
        </AppButton>
        <AppButton
          onClick={handleSubmit}
          disabled={!canProceed}
          className="flex-1"
        >
          Continue
        </AppButton>
      </div>
    </div>
  );
}
