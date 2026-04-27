"use client";

/**
 * Public careers page (T-R045) — no auth required.
 * Renders open job listings for the company at the given slug.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Briefcase, MapPin, Loader2 } from "lucide-react";
import {
  recruitmentApi,
  type PublicCompanyCareers,
} from "@/services/api/recruitment";

export default function PublicCareersPage() {
  const params = useParams<{ slug: string }>();
  const slug = params?.slug;
  const [data, setData] = useState<PublicCompanyCareers | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    recruitmentApi
      .getPublicCompanyCareers(slug)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        const msg = e instanceof Error ? e.message : "Unable to load careers";
        setError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-[var(--color-surface-base)]">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--color-gray-400)]" />
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-[var(--color-surface-base)] px-4">
        <div className="text-center max-w-md">
          <Briefcase className="h-12 w-12 text-[var(--color-gray-300)] mx-auto mb-3" />
          <h1 className="text-xl font-semibold text-[var(--color-gray-900)]">
            Careers not found
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-2">
            {error || "We couldn't find this company's careers page."}
          </p>
        </div>
      </main>
    );
  }

  const { company, jobs } = data;

  return (
    <main className="min-h-screen bg-[var(--color-surface-base)]">
      {/* Branded header */}
      <header className="bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-light)] text-white">
        <div className="max-w-4xl mx-auto px-6 py-12">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-xl bg-white/15 flex items-center justify-center text-white font-bold text-lg">
              {company.name.charAt(0).toUpperCase()}
            </div>
            <h1 className="text-3xl font-bold">{company.name}</h1>
          </div>
          <p className="text-white/85 text-base mt-2 max-w-2xl">
            {company.description ||
              `Open opportunities at ${company.name}. Find your next role with us.`}
          </p>
        </div>
      </header>

      {/* Jobs listing */}
      <section className="max-w-4xl mx-auto px-6 py-10">
        <h2 className="text-xl font-semibold text-[var(--color-gray-900)] mb-4">
          Open Positions
          <span className="ml-2 text-sm font-normal text-[var(--color-gray-500)]">
            ({jobs.length})
          </span>
        </h2>

        {jobs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] p-10 text-center">
            <Briefcase className="h-10 w-10 text-[var(--color-gray-300)] mx-auto mb-2" />
            <p className="text-sm text-[var(--color-gray-500)]">
              There are no open positions at this time. Please check back later.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {jobs.map((job) => {
              const jobSlug = job.slug || String(job.id);
              const preview =
                (job.description || "").slice(0, 200) +
                ((job.description || "").length > 200 ? "…" : "");
              return (
                <li
                  key={job.id}
                  className="rounded-xl border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] p-5 hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-[var(--color-gray-900)]">
                        {job.title}
                      </h3>
                      <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-[var(--color-gray-500)]">
                        {job.department && <span>{job.department}</span>}
                        {job.location && (
                          <span className="inline-flex items-center gap-1">
                            <MapPin className="h-3 w-3" />
                            {job.location}
                          </span>
                        )}
                        {job.employment_type && (
                          <span className="capitalize">
                            {job.employment_type.replace(/_/g, " ")}
                          </span>
                        )}
                        {(job.salary_range_min || job.salary_range_max) && (
                          <span>
                            SGD {job.salary_range_min?.toLocaleString() || "—"}
                            {" – "}
                            {job.salary_range_max?.toLocaleString() || "—"}
                            /month
                          </span>
                        )}
                      </div>
                      {preview && (
                        <p className="text-sm text-[var(--color-gray-600)] mt-3 leading-relaxed">
                          {preview}
                        </p>
                      )}
                    </div>
                    <Link
                      href={`/careers/${slug}/jobs/${jobSlug}/apply`}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium hover:opacity-90 whitespace-nowrap"
                    >
                      Apply
                    </Link>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        <footer className="mt-12 pt-6 border-t border-[var(--color-gray-200)] text-xs text-[var(--color-gray-400)] text-center">
          <p>Powered by Central HR</p>
        </footer>
      </section>
    </main>
  );
}
