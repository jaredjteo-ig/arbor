"use client";

/**
 * Public apply page (T-R046) — no auth required.
 * Applicants can submit their application + resume + screening responses.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Briefcase,
  Loader2,
  CheckCircle2,
  ArrowLeft,
  MapPin,
} from "lucide-react";
import {
  recruitmentApi,
  type PublicJobSummary,
  type ScreeningQuestion,
} from "@/services/api/recruitment";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export default function PublicApplyPage() {
  const params = useParams<{ slug: string; jobSlug: string }>();
  const slug = params?.slug || "";
  const jobSlug = params?.jobSlug || "";

  const [job, setJob] = useState<PublicJobSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [resume, setResume] = useState<File | null>(null);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [pdpaConsent, setPdpaConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{
    referenceNumber: string;
  } | null>(null);

  useEffect(() => {
    if (!slug || !jobSlug) return;
    setLoading(true);
    setError(null);
    recruitmentApi
      .getPublicJob(slug, jobSlug)
      .then((j) => {
        setJob(j);
        // Pre-initialise answers
        const init: Record<number, string> = {};
        for (const q of j.questions || []) init[q.id] = "";
        setAnswers(init);
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : "Job not found";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [slug, jobSlug]);

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    setResumeError(null);
    const f = e.target.files?.[0] ?? null;
    if (f && f.size > MAX_FILE_SIZE) {
      setResumeError("Resume must be 10 MB or smaller.");
      e.target.value = "";
      setResume(null);
      return;
    }
    setResume(f);
  }

  function setAnswer(qid: number, value: string) {
    setAnswers((prev) => ({ ...prev, [qid]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);

    if (!pdpaConsent) {
      setSubmitError("You must agree to the data-handling notice to apply.");
      return;
    }
    if (!name.trim() || !email.trim()) {
      setSubmitError("Name and email are required.");
      return;
    }
    if (!resume) {
      setSubmitError("Please attach your resume.");
      return;
    }
    // Validate required screening questions
    for (const q of job?.questions || []) {
      if (q.is_required && !(answers[q.id] || "").trim()) {
        setSubmitError(`Please answer: "${q.question_text}"`);
        return;
      }
    }

    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("name", name.trim());
      fd.append("email", email.trim());
      fd.append("phone", phone.trim());
      fd.append("resume", resume);
      fd.append(
        "screening_responses",
        JSON.stringify(
          Object.entries(answers).map(([qid, answer]) => ({
            question_id: Number(qid),
            answer,
          })),
        ),
      );
      fd.append("pdpa_consent", "true");

      const res = await recruitmentApi.submitPublicApplication(
        slug,
        jobSlug,
        fd,
      );
      setSuccess({ referenceNumber: res.reference_number });
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to submit application";
      setSubmitError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-[var(--color-surface-base)]">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--color-gray-400)]" />
      </main>
    );
  }

  if (error || !job) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-[var(--color-surface-base)] px-4">
        <div className="text-center max-w-md">
          <Briefcase className="h-12 w-12 text-[var(--color-gray-300)] mx-auto mb-3" />
          <h1 className="text-xl font-semibold text-[var(--color-gray-900)]">
            Job not available
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-2">
            {error || "This job listing may have been closed or moved."}
          </p>
          <Link
            href={`/careers/${slug}`}
            className="inline-flex items-center gap-1 mt-4 text-sm text-[var(--color-primary)] hover:underline"
          >
            <ArrowLeft className="h-4 w-4" /> Back to careers
          </Link>
        </div>
      </main>
    );
  }

  if (success) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-[var(--color-surface-base)] px-4">
        <div className="max-w-md w-full text-center bg-[var(--color-surface-card)] border border-[var(--color-gray-200)] rounded-2xl p-8">
          <div className="mx-auto w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center mb-4">
            <CheckCircle2 className="w-8 h-8 text-emerald-600" />
          </div>
          <h1 className="text-xl font-bold text-[var(--color-gray-900)] mb-2">
            Application submitted
          </h1>
          <p className="text-sm text-[var(--color-gray-600)] mb-4">
            Thank you for applying. We&apos;ll review your application and reach
            out if there&apos;s a fit.
          </p>
          <div className="rounded-lg bg-[var(--color-gray-50)] border border-[var(--color-gray-200)] p-3 mb-4">
            <p className="text-xs text-[var(--color-gray-500)] mb-0.5">
              Reference number
            </p>
            <p className="text-sm font-mono font-semibold text-[var(--color-gray-900)]">
              {success.referenceNumber}
            </p>
          </div>
          <Link
            href={`/careers/${slug}`}
            className="inline-flex items-center gap-1 text-sm text-[var(--color-primary)] hover:underline"
          >
            <ArrowLeft className="h-4 w-4" /> Back to all openings
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[var(--color-surface-base)]">
      <div className="max-w-2xl mx-auto px-6 py-10">
        <Link
          href={`/careers/${slug}`}
          className="inline-flex items-center gap-1 text-sm text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back to all openings
        </Link>

        {/* Job header */}
        <div className="bg-[var(--color-surface-card)] border border-[var(--color-gray-200)] rounded-2xl p-6 mb-6">
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            {job.title}
          </h1>
          <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-[var(--color-gray-500)]">
            {job.department && <span>{job.department}</span>}
            {job.location && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3 w-3" /> {job.location}
              </span>
            )}
            {job.employment_type && (
              <span className="capitalize">
                {job.employment_type.replace(/_/g, " ")}
              </span>
            )}
          </div>
          {job.description && (
            <div className="mt-4 text-sm text-[var(--color-gray-700)] whitespace-pre-wrap">
              {job.description}
            </div>
          )}
          {job.requirements && (
            <div className="mt-4">
              <h3 className="text-xs font-semibold uppercase text-[var(--color-gray-500)] mb-1">
                Requirements
              </h3>
              <div className="text-sm text-[var(--color-gray-700)] whitespace-pre-wrap">
                {job.requirements}
              </div>
            </div>
          )}
        </div>

        {/* Application form */}
        <form
          onSubmit={handleSubmit}
          className="bg-[var(--color-surface-card)] border border-[var(--color-gray-200)] rounded-2xl p-6 space-y-4"
        >
          <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
            Apply for this role
          </h2>

          <div>
            <label
              htmlFor="apply-name"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Full name *
            </label>
            <input
              id="apply-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="apply-email"
                className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
              >
                Email *
              </label>
              <input
                id="apply-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
                required
              />
            </div>
            <div>
              <label
                htmlFor="apply-phone"
                className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
              >
                Phone
              </label>
              <input
                id="apply-phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="apply-resume"
              className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
            >
              Resume * (PDF, DOC, DOCX — max 10 MB)
            </label>
            <input
              id="apply-resume"
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={handleFile}
              className="block w-full text-sm text-[var(--color-gray-600)] file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-[var(--color-gray-200)] file:text-sm file:font-medium file:bg-[var(--color-gray-50)] file:text-[var(--color-gray-700)] hover:file:bg-[var(--color-gray-100)]"
              required
            />
            {resume && (
              <p className="text-xs text-[var(--color-gray-500)] mt-1">
                {resume.name} ({(resume.size / 1024).toFixed(0)} KB)
              </p>
            )}
            {resumeError && (
              <p className="text-xs text-red-600 mt-1">{resumeError}</p>
            )}
          </div>

          {/* Screening questions */}
          {(job.questions || []).length > 0 && (
            <div className="border-t border-[var(--color-gray-200)] pt-4 space-y-3">
              <h3 className="text-sm font-semibold text-[var(--color-gray-700)]">
                Screening questions
              </h3>
              {(job.questions || []).map((q: ScreeningQuestion) => (
                <ApplyQuestion
                  key={q.id}
                  question={q}
                  value={answers[q.id] || ""}
                  onChange={(val) => setAnswer(q.id, val)}
                />
              ))}
            </div>
          )}

          {/* PDPA consent (required) */}
          <div className="border-t border-[var(--color-gray-200)] pt-4">
            <label className="flex items-start gap-2 text-sm text-[var(--color-gray-700)] cursor-pointer">
              <input
                type="checkbox"
                checked={pdpaConsent}
                onChange={(e) => setPdpaConsent(e.target.checked)}
                className="mt-0.5 rounded border-[var(--color-gray-300)]"
                required
              />
              <span>
                I consent to the collection, use and disclosure of my personal
                data for the purpose of evaluating this application, in
                accordance with the Singapore Personal Data Protection Act
                (PDPA). *
              </span>
            </label>
          </div>

          {submitError && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
              {submitError}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting || !pdpaConsent}
            className="w-full px-4 py-2.5 rounded-lg bg-[var(--color-primary)] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? "Submitting…" : "Submit application"}
          </button>
        </form>
      </div>
    </main>
  );
}

function ApplyQuestion({
  question,
  value,
  onChange,
}: {
  question: ScreeningQuestion;
  value: string;
  onChange: (val: string) => void;
}) {
  const id = `q-${question.id}`;
  const required = question.is_required;

  if (question.question_type === "yes_no") {
    return (
      <div>
        <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-1">
          {question.question_text}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        <div className="flex gap-3">
          {["yes", "no"].map((v) => (
            <label
              key={v}
              className="inline-flex items-center gap-1.5 text-sm cursor-pointer"
            >
              <input
                type="radio"
                name={id}
                value={v}
                checked={value === v}
                onChange={() => onChange(v)}
                required={required}
              />
              <span className="capitalize">{v}</span>
            </label>
          ))}
        </div>
      </div>
    );
  }

  if (
    question.question_type === "multiple_choice" &&
    question.options &&
    question.options.length > 0
  ) {
    return (
      <div>
        <label
          htmlFor={id}
          className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
        >
          {question.question_text}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required={required}
          className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
        >
          <option value="">Select an option</option>
          {question.options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (question.question_type === "number") {
    return (
      <div>
        <label
          htmlFor={id}
          className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
        >
          {question.question_text}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        <input
          id={id}
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required={required}
          className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
        />
      </div>
    );
  }

  // Default: text
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-[var(--color-gray-700)] mb-1"
      >
        {question.question_text}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        rows={3}
        className="w-full rounded-[8px] border px-3 py-2 text-sm bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)]"
      />
    </div>
  );
}
