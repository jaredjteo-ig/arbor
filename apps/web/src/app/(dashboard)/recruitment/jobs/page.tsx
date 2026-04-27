"use client";

import { redirect } from "next/navigation";

/**
 * /recruitment/jobs — redirects to the main recruitment page which
 * currently handles jobs, candidates, and interviews in a tabbed layout.
 * This route will become the dedicated jobs list once the recruitment
 * module is fully restructured into multi-page navigation.
 */
export default function JobsPage() {
  redirect("/recruitment");
}
