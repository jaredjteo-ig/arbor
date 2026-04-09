/* Service Worker for Web Push notifications.
 *
 * Registered by the usePushNotifications hook. Handles incoming push
 * events and notification click actions. Runs in its own thread —
 * independent of the React app lifecycle.
 */

// ── Push event ──────────────────────────────────────────────

self.addEventListener("push", function (event) {
  let data = { title: "New Alert", body: "You have a new notification." };

  if (event.data) {
    try {
      data = event.data.json();
    } catch (_) {
      // If the payload is plain text, use it as the body
      data = { title: "New Alert", body: event.data.text() };
    }
  }

  const title = data.title || "Arbor HR";
  const options = {
    body: data.body || "",
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    tag: data.update_id || "arbor-notification",
    data: {
      url: data.url || "/alerts",
    },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// ── Notification click ──────────────────────────────────────

self.addEventListener("notificationclick", function (event) {
  event.notification.close();

  const url = event.notification.data?.url || "/alerts";

  // Focus an existing window or open a new one
  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then(function (clientList) {
        // If the app is already open, navigate it
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && "focus" in client) {
            client.focus();
            client.navigate(url);
            return;
          }
        }
        // Otherwise open a new window
        if (self.clients.openWindow) {
          return self.clients.openWindow(url);
        }
      }),
  );
});

// ── Notification close (optional analytics) ─────────────────

self.addEventListener("notificationclose", function (_event) {
  // Could send analytics about dismissed notifications
});
