import { redirect } from "next/navigation";

/**
 * /recruitment/jobs — focused view of the jobs section.
 * Server-side redirect to the recruitment page with the "jobs" tab pre-selected.
 * The recruitment page reads ?tab= from URL search params and switches view.
 */
export default function JobsPage() {
  redirect("/recruitment?tab=jobs");
}
