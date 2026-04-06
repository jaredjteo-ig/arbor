/**
 * Error humanization utility.
 *
 * Translates raw API / network errors into user-friendly messages
 * that avoid leaking internal details (stack traces, endpoint paths, etc.).
 */

/* ── Budget Exceeded Error ──────────────────────────────────── */

/**
 * Thrown when the free-tier LLM budget has been exhausted.
 * ChatContainer detects this by type to render a helpful info card
 * instead of a generic error message.
 */
export class BudgetExceededError extends Error {
  constructor(message?: string) {
    super(
      message ??
        "You\u2019ve reached the free advisory limit for this month. " +
          "To continue using the AI advisor, go to Settings \u203A AI to " +
          "add your own API key or set up a local AI model.",
    );
    this.name = "BudgetExceededError";
  }
}

export function humanizeError(error: unknown): string {
  /* Budget exceeded has its own UI treatment — pass through the message */
  if (error instanceof BudgetExceededError) {
    return error.message;
  }
  // HTTP response errors (Response object or error-like with `status`)
  if (
    error instanceof Response ||
    (error !== null && typeof error === "object" && "status" in error)
  ) {
    const status = (error as { status: number }).status;
    if (status === 401 || status === 403)
      return "Your session has expired. Please log in again.";
    if (status === 429)
      return "You have sent too many requests. Please wait a moment.";
    if (status === 500 || status === 503)
      return "Central is temporarily unavailable. Please try again in a few minutes.";
  }

  // Standard Error instances
  if (error instanceof Error) {
    if (error.name === "AbortError") return "The request was cancelled.";
    const msg = error.message.toLowerCase();
    if (msg.includes("network") || msg.includes("fetch"))
      return "Connection lost. Check your internet and try again.";
    if (msg.includes("timeout"))
      return "The response took too long. Try a shorter question.";
  }

  // Fallback
  return "Something went wrong. Please try again.";
}
