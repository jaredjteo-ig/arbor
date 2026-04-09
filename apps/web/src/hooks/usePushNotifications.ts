/**
 * Hook for managing browser Web Push notification subscriptions.
 *
 * Handles:
 * - Service worker registration for push events
 * - Requesting notification permission from the user
 * - Subscribing to push via the VAPID public key from the backend
 * - Sending the subscription to POST /push/subscribe
 * - Unsubscribing via DELETE /push/unsubscribe
 *
 * Usage:
 *   const { isSupported, permission, isSubscribed, subscribe, unsubscribe } = usePushNotifications();
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient } from "@/services/api/client";

/* ── Types ────────────────────────────────────────────────── */

interface PushState {
  /** Whether the browser supports Web Push. */
  isSupported: boolean;
  /** Current notification permission: 'default' | 'granted' | 'denied'. */
  permission: NotificationPermission | "unsupported";
  /** Whether the user currently has an active push subscription. */
  isSubscribed: boolean;
  /** Whether a subscribe/unsubscribe operation is in progress. */
  loading: boolean;
  /** Error message from the last operation, if any. */
  error: string | null;
  /** Subscribe to push notifications. Requests permission if needed. */
  subscribe: () => Promise<boolean>;
  /** Unsubscribe from push notifications. */
  unsubscribe: () => Promise<boolean>;
}

/* ── Helpers ──────────────────────────────────────────────── */

/**
 * Convert a base64 string to a Uint8Array (for applicationServerKey).
 * The VAPID public key comes from the server as base64url.
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const buffer = new ArrayBuffer(rawData.length);
  const outputArray = new Uint8Array(buffer);
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

function isPushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/* ── Hook ─────────────────────────────────────────────────── */

export function usePushNotifications(): PushState {
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [permission, setPermission] = useState<
    NotificationPermission | "unsupported"
  >(isPushSupported() ? Notification.permission : "unsupported");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSupported = isPushSupported();

  // Keep a ref to the service worker registration
  const swRegistrationRef = useRef<ServiceWorkerRegistration | null>(null);

  // ── On mount: register service worker and check existing subscription ──

  useEffect(() => {
    if (!isSupported) return;

    let cancelled = false;

    async function init() {
      try {
        // Register the push service worker
        const registration = await navigator.serviceWorker.register(
          "/sw-push.js",
          { scope: "/" },
        );
        if (cancelled) return;
        swRegistrationRef.current = registration;

        // Check for an existing push subscription
        const existingSub = await registration.pushManager.getSubscription();
        if (cancelled) return;

        if (existingSub) {
          setIsSubscribed(true);
        }
      } catch (err) {
        if (!cancelled) {
          // Service worker registration failure is not fatal
          console.warn("Push service worker registration failed:", err);
        }
      }
    }

    init();

    return () => {
      cancelled = true;
    };
  }, [isSupported]);

  // ── Subscribe ─────────────────────────────────────────────

  const subscribe = useCallback(async (): Promise<boolean> => {
    if (!isSupported) {
      setError("Push notifications are not supported in this browser.");
      return false;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Request notification permission
      const perm = await Notification.requestPermission();
      setPermission(perm);

      if (perm !== "granted") {
        setError(
          "Notification permission was denied. Please enable notifications in your browser settings.",
        );
        setLoading(false);
        return false;
      }

      // 2. Get the VAPID public key from the backend
      const vapidResponse = await apiClient.get<{
        public_key: string | null;
        configured: boolean;
      }>("/push/vapid-key");

      if (!vapidResponse.configured || !vapidResponse.public_key) {
        setError(
          "Push notifications are not configured on the server. Contact your administrator.",
        );
        setLoading(false);
        return false;
      }

      // 3. Ensure service worker is registered
      let registration = swRegistrationRef.current;
      if (!registration) {
        registration = await navigator.serviceWorker.register("/sw-push.js", {
          scope: "/",
        });
        swRegistrationRef.current = registration;
      }

      // Wait for the service worker to be active
      await navigator.serviceWorker.ready;

      // 4. Subscribe via PushManager
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidResponse.public_key),
      });

      // 5. Extract the subscription details
      const subJson = subscription.toJSON();
      const endpoint = subJson.endpoint ?? "";
      const p256dh = subJson.keys?.p256dh ?? "";
      const auth = subJson.keys?.auth ?? "";

      if (!endpoint || !p256dh || !auth) {
        setError("Browser returned an incomplete push subscription.");
        setLoading(false);
        return false;
      }

      // 6. Send to backend
      await apiClient.post("/push/subscribe", {
        endpoint,
        keys: { p256dh, auth },
      });

      setIsSubscribed(true);
      setLoading(false);
      return true;
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to subscribe to push notifications.";
      setError(msg);
      setLoading(false);
      return false;
    }
  }, [isSupported]);

  // ── Unsubscribe ───────────────────────────────────────────

  const unsubscribe = useCallback(async (): Promise<boolean> => {
    if (!isSupported) return false;

    setLoading(true);
    setError(null);

    try {
      const registration = swRegistrationRef.current;
      if (!registration) {
        setIsSubscribed(false);
        setLoading(false);
        return true;
      }

      const subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        setIsSubscribed(false);
        setLoading(false);
        return true;
      }

      const endpoint = subscription.endpoint;

      // Unsubscribe from the browser
      await subscription.unsubscribe();

      // Notify the backend
      try {
        await apiClient.post("/push/unsubscribe", {
          endpoint,
        });
      } catch {
        // Backend removal failure is not critical -- the subscription
        // is already removed from the browser
        console.warn("Backend push unsubscribe failed (non-critical)");
      }

      setIsSubscribed(false);
      setLoading(false);
      return true;
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to unsubscribe from push notifications.";
      setError(msg);
      setLoading(false);
      return false;
    }
  }, [isSupported]);

  return {
    isSupported,
    permission,
    isSubscribed,
    loading,
    error,
    subscribe,
    unsubscribe,
  };
}
