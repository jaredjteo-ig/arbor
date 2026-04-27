"use client";

import { redirect } from "next/navigation";

/**
 * /recruitment/interviews — interview calendar view.
 * Currently redirects to the main recruitment page.
 * Will become the dedicated calendar view for all scheduled interviews.
 */
export default function InterviewsPage() {
  redirect("/recruitment");
}
