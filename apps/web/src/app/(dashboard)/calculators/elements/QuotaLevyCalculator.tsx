"use client";

/* ── Quota & Levy Calculator ─────────────────────────────── */
/* Checks foreign worker quota (DRC) and estimates levy based  */
/* on sector and headcount breakdown.                          */

import { useState } from "react";
import { AppCard, AppButton, AppInput } from "@/components/design-system";
import { ResultPanel } from "./ResultPanel";
import { ResultRow } from "./ResultRow";

/* ── Sector DRC limits & levy rates ──────────────────────── */

interface SectorConfig {
  label: string;
  drcLimit: number;
  sPassSubDrc: number;
  levyTier1: number;
  levyTier2: number;
  levyTier1Threshold: number;
}

const SECTORS: Record<string, SectorConfig> = {
  manufacturing: {
    label: "Manufacturing",
    drcLimit: 0.6,
    sPassSubDrc: 0.15,
    levyTier1: 300,
    levyTier2: 600,
    levyTier1Threshold: 0.25,
  },
  services: {
    label: "Services",
    drcLimit: 0.35,
    sPassSubDrc: 0.1,
    levyTier1: 300,
    levyTier2: 600,
    levyTier1Threshold: 0.15,
  },
  construction: {
    label: "Construction",
    drcLimit: 0.8338,
    sPassSubDrc: 0.15,
    levyTier1: 300,
    levyTier2: 700,
    levyTier1Threshold: 0.25,
  },
  marine: {
    label: "Marine Shipyard",
    drcLimit: 0.7778,
    sPassSubDrc: 0.15,
    levyTier1: 300,
    levyTier2: 400,
    levyTier1Threshold: 0.25,
  },
  process: {
    label: "Process",
    drcLimit: 0.8338,
    sPassSubDrc: 0.15,
    levyTier1: 300,
    levyTier2: 600,
    levyTier1Threshold: 0.25,
  },
};

const fmt = (n: number) =>
  `$${(n ?? 0).toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

interface QuotaResult {
  totalWorkers: number;
  localCore: number;
  foreignWorkers: number;
  currentRatio: number;
  drcLimit: number;
  withinLimit: boolean;
  wpAllowed: number;
  levyEstimate: number;
  notes: string[];
}

export function QuotaLevyCalculator() {
  const [sector, setSector] = useState("services");
  const [localCount, setLocalCount] = useState("");
  const [prCount, setPrCount] = useState("");
  const [epCount, setEpCount] = useState("");
  const [spCount, setSpCount] = useState("");
  const [wpCount, setWpCount] = useState("");
  const [result, setResult] = useState<QuotaResult | null>(null);

  const calculate = () => {
    const local = parseInt(localCount) || 0;
    const pr = parseInt(prCount) || 0;
    const ep = parseInt(epCount) || 0;
    const sp = parseInt(spCount) || 0;
    const wp = parseInt(wpCount) || 0;

    if (local + pr + ep + sp + wp === 0) return;

    const config = SECTORS[sector];
    const localCore = local + pr;
    const foreignWorkers = sp + wp;
    const totalWorkers = localCore + ep + foreignWorkers;
    const currentRatio =
      localCore > 0
        ? foreignWorkers / localCore
        : foreignWorkers > 0
          ? Infinity
          : 0;

    const drcLimit = config.drcLimit;
    const maxForeign = Math.floor(localCore * (drcLimit / (1 - drcLimit)));
    const withinLimit = foreignWorkers <= maxForeign;

    // Levy estimation (simplified)
    let levyEstimate = 0;
    const tier1Max = Math.floor(localCore * config.levyTier1Threshold);
    const wpInTier1 = Math.min(wp, tier1Max);
    const wpInTier2 = Math.max(0, wp - tier1Max);
    levyEstimate += wpInTier1 * config.levyTier1;
    levyEstimate += wpInTier2 * config.levyTier2;
    // S Pass levy (simplified flat rate)
    levyEstimate += sp * 450;

    const notes: string[] = [];
    notes.push(
      `${config.label} sector DRC limit: ${(drcLimit * 100).toFixed(1)}%. Maximum foreign workers for your local core: ${maxForeign}.`,
    );
    if (!withinLimit) {
      notes.push(
        "Your current foreign worker count exceeds the DRC limit. You may need to reduce foreign headcount or hire more local workers.",
      );
    }
    notes.push(
      "Levy estimates are approximate. Actual levy rates depend on worker qualifications and MOM assessment.",
    );

    setResult({
      totalWorkers,
      localCore,
      foreignWorkers,
      currentRatio: isFinite(currentRatio) ? currentRatio : 0,
      drcLimit,
      withinLimit,
      wpAllowed: maxForeign,
      levyEstimate,
      notes,
    });
  };

  return (
    <div className="space-y-6">
      <AppCard variant="standard">
        <div className="space-y-4">
          <AppInput
            label="Sector"
            variant="select"
            value={sector}
            onChange={(e) => setSector((e.target as HTMLSelectElement).value)}
            options={Object.entries(SECTORS).map(([key, val]) => ({
              value: key,
              label: val.label,
            }))}
          />

          <p className="text-sm font-medium text-[var(--color-gray-700)]">
            Headcount Breakdown
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <AppInput
              label="Local (SC)"
              variant="number"
              placeholder="0"
              value={localCount}
              onChange={(e) =>
                setLocalCount((e.target as HTMLInputElement).value)
              }
              min="0"
            />
            <AppInput
              label="PR"
              variant="number"
              placeholder="0"
              value={prCount}
              onChange={(e) => setPrCount((e.target as HTMLInputElement).value)}
              min="0"
            />
            <AppInput
              label="EP"
              variant="number"
              placeholder="0"
              value={epCount}
              onChange={(e) => setEpCount((e.target as HTMLInputElement).value)}
              min="0"
            />
            <AppInput
              label="S Pass"
              variant="number"
              placeholder="0"
              value={spCount}
              onChange={(e) => setSpCount((e.target as HTMLInputElement).value)}
              min="0"
            />
            <AppInput
              label="Work Permit"
              variant="number"
              placeholder="0"
              value={wpCount}
              onChange={(e) => setWpCount((e.target as HTMLInputElement).value)}
              min="0"
            />
          </div>

          <AppButton onClick={calculate} className="w-full sm:w-auto">
            Calculate Quota & Levy
          </AppButton>
        </div>
      </AppCard>

      {result && (
        <ResultPanel
          title="Quota & Levy Results"
          citations={[
            {
              label: "Employment of Foreign Manpower Act",
              authority: "statutory",
            },
            { label: "MOM Levy Schedule", authority: "guideline" },
          ]}
          advisoryQuery="What are the current foreign worker quota limits and levy rates for my sector?"
          notes={result.notes}
        >
          <ResultRow
            label="Total Workforce"
            value={result.totalWorkers.toString()}
          />
          <ResultRow
            label="Local Core (SC + PR)"
            value={result.localCore.toString()}
          />
          <ResultRow
            label="Foreign Workers (SP + WP)"
            value={result.foreignWorkers.toString()}
          />
          <ResultRow
            label="Current DRC Ratio"
            value={`${(result.currentRatio * 100).toFixed(1)}%`}
          />
          <ResultRow
            label="DRC Limit"
            value={`${(result.drcLimit * 100).toFixed(1)}%`}
          />
          <ResultRow
            label="Within Quota"
            value={result.withinLimit ? "Yes" : "No -- over limit"}
            bold
            highlight
          />
          <ResultRow
            label="Max Foreign Workers Allowed"
            value={result.wpAllowed.toString()}
          />
          <ResultRow
            label="Estimated Monthly Levy"
            value={fmt(result.levyEstimate)}
            bold
          />
        </ResultPanel>
      )}
    </div>
  );
}
