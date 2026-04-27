"use client";

import { redirect } from "next/navigation";

/**
 * /recruitment/candidates/[id] — full candidate profile page.
 * Currently redirects to the main recruitment page.
 * Will become the dedicated candidate detail view with resume,
 * activity timeline, feedback, and communications.
 */
export default function CandidateDetailPage() {
  redirect("/recruitment");
}
