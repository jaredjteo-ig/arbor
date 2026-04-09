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
  sPassRatio: number;
  sPassSubDrcLimit: number;
  sPassWithinLimit: boolean;
  maxSPass: number;
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

    // S Pass sub-quota
    const sPassSubDrcLimit = config.sPassSubDrc;
    const maxSPass = Math.floor(
      localCore * (sPassSubDrcLimit / (1 - sPassSubDrcLimit)),
    );
    const sPassRatio = localCore > 0 ? sp / (localCore + sp) : sp > 0 ? 1 : 0;
    const sPassWithinLimit = sp <= maxSPass;

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
    // S Pass sub-quota warning
    if (sp > 0) {
      const sPassUsage = maxSPass > 0 ? (sp / maxSPass) * 100 : 100;
      if (!sPassWithinLimit) {
        notes.push(
          `S Pass sub-quota exceeded. You have ${sp} S Pass holders but the maximum for your local core is ${maxSPass}.`,
        );
      } else if (sPassUsage >= 80) {
        notes.push(
          `Approaching S Pass sub-quota: ${sp} of ${maxSPass} slots used (${sPassUsage.toFixed(0)}%). The next S Pass hire may bring you to the ceiling.`,
        );
      }
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
      sPassRatio: isFinite(sPassRatio) ? sPassRatio : 0,
      sPassSubDrcLimit,
      sPassWithinLimit,
      maxSPass,
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
            label="Within Overall Quota"
            value={result.withinLimit ? "Yes" : "No -- over limit"}
            bold
            highlight
          />
          <ResultRow
            label="S Pass Sub-Quota Ratio"
            value={`${(result.sPassRatio * 100).toFixed(1)}% of ${(result.sPassSubDrcLimit * 100).toFixed(1)}% limit`}
          />
          <ResultRow
            label="S Pass Within Sub-Quota"
            value={result.sPassWithinLimit ? "Yes" : "No -- over S Pass limit"}
            bold
            highlight
          />
          <ResultRow
            label="Max S Pass Allowed"
            value={result.maxSPass.toString()}
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

      {/* What-if scenario */}
      {result && (
        <WhatIfScenario
          currentResult={result}
          sector={sector}
          localCount={parseInt(localCount) || 0}
          prCount={parseInt(prCount) || 0}
          epCount={parseInt(epCount) || 0}
          spCount={parseInt(spCount) || 0}
          wpCount={parseInt(wpCount) || 0}
        />
      )}
    </div>
  );
}

/* ── What-If Scenario ──────────────────────────────────── */

function WhatIfScenario({
  currentResult,
  sector,
  localCount,
  prCount,
  epCount,
  spCount,
  wpCount,
}: {
  currentResult: QuotaResult;
  sector: string;
  localCount: number;
  prCount: number;
  epCount: number;
  spCount: number;
  wpCount: number;
}) {
  const [hireType, setHireType] = useState("sp");
  const [hireCount, setHireCount] = useState("1");
  const [scenario, setScenario] = useState<QuotaResult | null>(null);

  const hireOptions = [
    { value: "local", label: "Local (SC)" },
    { value: "pr", label: "Permanent Resident" },
    { value: "ep", label: "Employment Pass" },
    { value: "sp", label: "S Pass" },
    { value: "wp", label: "Work Permit" },
  ];

  function runScenario() {
    const count = parseInt(hireCount) || 0;
    if (count <= 0) return;

    const config = SECTORS[sector];
    const newLocal = localCount + (hireType === "local" ? count : 0);
    const newPr = prCount + (hireType === "pr" ? count : 0);
    const newEp = epCount + (hireType === "ep" ? count : 0);
    const newSp = spCount + (hireType === "sp" ? count : 0);
    const newWp = wpCount + (hireType === "wp" ? count : 0);

    const localCore = newLocal + newPr;
    const foreignWorkers = newSp + newWp;
    const totalWorkers = localCore + newEp + foreignWorkers;
    const currentRatio =
      localCore > 0
        ? foreignWorkers / localCore
        : foreignWorkers > 0
          ? Infinity
          : 0;

    const maxForeign = Math.floor(
      localCore * (config.drcLimit / (1 - config.drcLimit)),
    );
    const withinLimit = foreignWorkers <= maxForeign;

    const maxSPass = Math.floor(
      localCore * (config.sPassSubDrc / (1 - config.sPassSubDrc)),
    );
    const sPassRatio =
      localCore > 0 ? newSp / (localCore + newSp) : newSp > 0 ? 1 : 0;
    const sPassWithinLimit = newSp <= maxSPass;

    let levyEstimate = 0;
    const tier1Max = Math.floor(localCore * config.levyTier1Threshold);
    const wpInTier1 = Math.min(newWp, tier1Max);
    const wpInTier2 = Math.max(0, newWp - tier1Max);
    levyEstimate += wpInTier1 * config.levyTier1;
    levyEstimate += wpInTier2 * config.levyTier2;
    levyEstimate += newSp * 450;

    const notes: string[] = [];
    if (!withinLimit) {
      notes.push("This scenario would exceed the DRC limit.");
    }
    if (!sPassWithinLimit) {
      notes.push("This scenario would exceed the S Pass sub-quota.");
    }
    if (withinLimit && sPassWithinLimit) {
      notes.push("This scenario is within all quota limits.");
    }

    setScenario({
      totalWorkers,
      localCore,
      foreignWorkers,
      currentRatio: isFinite(currentRatio) ? currentRatio : 0,
      drcLimit: config.drcLimit,
      withinLimit,
      wpAllowed: maxForeign,
      sPassRatio: isFinite(sPassRatio) ? sPassRatio : 0,
      sPassSubDrcLimit: config.sPassSubDrc,
      sPassWithinLimit,
      maxSPass,
      levyEstimate,
      notes,
    });
  }

  const levyDiff = scenario
    ? scenario.levyEstimate - currentResult.levyEstimate
    : 0;

  return (
    <AppCard
      variant="standard"
      header={
        <h3 className="text-base font-semibold text-[var(--color-gray-900)]">
          What if I hire...
        </h3>
      }
    >
      <div className="space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <AppInput
            label="Pass Type"
            variant="select"
            value={hireType}
            onChange={(e) => setHireType((e.target as HTMLSelectElement).value)}
            options={hireOptions}
          />
          <AppInput
            label="How Many"
            variant="number"
            placeholder="1"
            value={hireCount}
            onChange={(e) => setHireCount((e.target as HTMLInputElement).value)}
            min="1"
          />
          <div className="flex items-end">
            <AppButton onClick={runScenario} className="w-full">
              Compare
            </AppButton>
          </div>
        </div>

        {scenario && (
          <div className="mt-4 rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-gray-50)] p-4 space-y-2">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase">
                  Current
                </p>
                <p className="font-semibold text-[var(--color-gray-900)]">
                  {currentResult.foreignWorkers} foreign /{" "}
                  {currentResult.localCore} local
                </p>
                <p
                  className={
                    currentResult.withinLimit
                      ? "text-emerald-600"
                      : "text-red-600"
                  }
                >
                  {currentResult.withinLimit ? "Within quota" : "Over quota"}
                </p>
                <p className="text-[var(--color-gray-700)]">
                  Levy: {fmt(currentResult.levyEstimate)}/mo
                </p>
              </div>
              <div>
                <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase">
                  After Hiring
                </p>
                <p className="font-semibold text-[var(--color-gray-900)]">
                  {scenario.foreignWorkers} foreign / {scenario.localCore} local
                </p>
                <p
                  className={
                    scenario.withinLimit ? "text-emerald-600" : "text-red-600"
                  }
                >
                  {scenario.withinLimit ? "Within quota" : "Over quota"}
                </p>
                <p className="text-[var(--color-gray-700)]">
                  Levy: {fmt(scenario.levyEstimate)}/mo
                  {levyDiff !== 0 && (
                    <span
                      className={
                        levyDiff > 0 ? " text-red-600" : " text-emerald-600"
                      }
                    >
                      {" "}
                      ({levyDiff > 0 ? "+" : ""}
                      {fmt(levyDiff)})
                    </span>
                  )}
                </p>
              </div>
            </div>
            {scenario.notes.map((note, i) => (
              <p key={i} className="text-xs text-[var(--color-gray-600)] mt-2">
                {note}
              </p>
            ))}
          </div>
        )}
      </div>
    </AppCard>
  );
}
