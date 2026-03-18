/**
 * Error humanization utility.
 *
 * Translates raw API / network errors into user-friendly messages
 * that avoid leaking internal details (stack traces, endpoint paths, etc.).
 */

export function humanizeError(error: unknown): string {
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
      return "Arbor is temporarily unavailable. Please try again in a few minutes.";
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
