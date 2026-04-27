import { redirect } from "next/navigation";

/**
 * /recruitment/interviews — focused interview view (calendar/list toggle).
 * Server-side redirect to the recruitment page with interviews tab selected.
 */
export default function InterviewsPage() {
  redirect("/recruitment?tab=interviews");
}
