import { redirect } from "next/navigation";

/**
 * /recruitment/candidates — focused candidate pipeline view.
 * Server-side redirect to the recruitment page with candidates tab selected.
 */
export default function CandidatesPage() {
  redirect("/recruitment?tab=candidates");
}
