"use client";

import { redirect } from "next/navigation";

/**
 * /recruitment/candidates — global candidate pool (searchable).
 * Currently redirects to the main recruitment page.
 * Will become the dedicated cross-job candidate search view.
 */
export default function CandidatesPage() {
  redirect("/recruitment");
}
