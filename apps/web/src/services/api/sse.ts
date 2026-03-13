/* ── SSE Streaming Client ────────────────────────────────── */
/* Uses fetch + ReadableStream to handle server-sent events   */
/* over POST requests with auth headers (EventSource only     */
/* supports GET without custom headers).                      */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── Types ───────────────────────────────────────────────── */

export interface SSECallbacks<
  TStart = unknown,
  TComplete = unknown,
> {
  onStart?: (data: TStart) => void;
  onToken?: (token: string, index: number) => void;
  onComplete?: (data: TComplete) => void;
  onError?: (error: Error) => void;
}

interface SSEEvent {
  event: string;
  data: string;
}

/* ── Parser ──────────────────────────────────────────────── */

/**
 * Parse raw SSE text into structured events.
 * Handles multi-line `data:` fields and event boundaries (blank lines).
 */
function parseSSEChunk(text: string): SSEEvent[] {
  const events: SSEEvent[] = [];
  const lines = text.split("\n");

  let currentEvent = "";
  let currentData = "";

  for (const line of lines) {
    if (line.startsWith("event:")) {
      currentEvent = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      const dataPart = line.slice(5).trim();
      currentData = currentData ? `${currentData}\n${dataPart}` : dataPart;
    } else if (line.trim() === "" && (currentEvent || currentData)) {
      events.push({
        event: currentEvent || "message",
        data: currentData,
      });
      currentEvent = "";
      currentData = "";
    }
  }

  /* Handle trailing event without a final blank line */
  if (currentEvent || currentData) {
    events.push({
      event: currentEvent || "message",
      data: currentData,
    });
  }

  return events;
}

/* ── SSE Stream Creator ──────────────────────────────────── */

/**
 * Open a POST-based SSE connection to the given path.
 *
 * Returns an AbortController that the caller can use to cancel
 * the stream at any time (e.g., when the user navigates away).
 */
export function createSSEStream<
  TStart = unknown,
  TComplete = unknown,
>(
  path: string,
  body: unknown,
  callbacks: SSECallbacks<TStart, TComplete>,
): AbortController {
  const controller = new AbortController();

  const accessToken =
    typeof window !== "undefined"
      ? localStorage.getItem("access_token")
      : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  (async () => {
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        let detail = "Streaming request failed";
        try {
          const errorBody = (await response.json()) as { detail?: string };
          if (errorBody.detail) detail = errorBody.detail;
        } catch {
          /* body may not be JSON */
        }
        callbacks.onError?.(new Error(detail));
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError?.(new Error("No response body available for streaming"));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        /* Process complete events (delimited by double newlines) */
        const parts = buffer.split("\n\n");
        /* Keep the last part as buffer — it may be incomplete */
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          if (!part.trim()) continue;

          const events = parseSSEChunk(part);
          for (const event of events) {
            processEvent(event, callbacks);
          }
        }
      }

      /* Process any remaining buffer */
      if (buffer.trim()) {
        const events = parseSSEChunk(buffer);
        for (const event of events) {
          processEvent(event, callbacks);
        }
      }
    } catch (error: unknown) {
      /* AbortError is expected when the caller cancels — don't report it */
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      callbacks.onError?.(
        error instanceof Error ? error : new Error("Stream connection failed"),
      );
    }
  })();

  return controller;
}

/* ── Event Processor ─────────────────────────────────────── */

function processEvent<TStart, TComplete>(
  event: SSEEvent,
  callbacks: SSECallbacks<TStart, TComplete>,
): void {
  try {
    switch (event.event) {
      case "start": {
        const data = JSON.parse(event.data) as TStart;
        callbacks.onStart?.(data);
        break;
      }
      case "token": {
        const data = JSON.parse(event.data) as { token: string; index: number };
        callbacks.onToken?.(data.token, data.index);
        break;
      }
      case "complete": {
        const data = JSON.parse(event.data) as TComplete;
        callbacks.onComplete?.(data);
        break;
      }
      case "error": {
        const data = JSON.parse(event.data) as { message?: string };
        callbacks.onError?.(new Error(data.message ?? "Stream error"));
        break;
      }
      default:
        /* Unknown event type — ignore gracefully */
        break;
    }
  } catch {
    callbacks.onError?.(new Error(`Failed to parse SSE event: ${event.event}`));
  }
}
