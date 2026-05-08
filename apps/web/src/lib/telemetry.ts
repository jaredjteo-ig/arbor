/**
 * Minimal telemetry helper — emits structured events for product
 * analytics without coupling to any specific provider.
 *
 * Mechanism:
 *   1. Dispatches a ``CustomEvent('arbor:telemetry', { detail: ... })``
 *      on ``window`` so future analytics integrations (PostHog,
 *      Segment, Mixpanel, internal pipeline) can subscribe via a
 *      single event listener.
 *   2. In dev, also ``console.info('[telemetry] ...')`` so engineers
 *      can verify events firing in the DevTools console.
 *
 * Designed to be a no-op in environments where no listener is
 * registered. Never throws — telemetry must never break the user
 * flow it's instrumenting.
 *
 * Usage::
 *
 *     import { track } from "@/lib/telemetry";
 *     track("xero.export_attempted", { run_id: 42, force: false });
 */

export type TelemetryEvent = {
  name: string;
  props: Record<string, unknown>;
  ts: number;
};

export function track(name: string, props: Record<string, unknown> = {}): void {
  try {
    if (typeof window === "undefined") return;
    const event: TelemetryEvent = {
      name,
      props,
      ts: Date.now(),
    };
    window.dispatchEvent(new CustomEvent("arbor:telemetry", { detail: event }));
    if (process.env.NODE_ENV !== "production") {
      // eslint-disable-next-line no-console
      console.info("[telemetry]", name, props);
    }
  } catch {
    // Telemetry must never break the wrapped flow.
  }
}
