"use client";

import { redirect } from "next/navigation";

/**
 * /recruitment/jobs/[id] — job detail page with Kanban pipeline.
 * Currently redirects to the main recruitment page.
 * Will become the dedicated job detail + candidate pipeline view.
 */
export default function JobDetailPage() {
  redirect("/recruitment");
}
