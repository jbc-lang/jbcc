const control = document.getElementById("analytics") as HTMLButtonElement;
const preference = "jbcc.playground.analytics";
let frame: HTMLIFrameElement | undefined;
let analyticsOrigin: string;

function applyAnalytics(enabled: boolean) {
  control.setAttribute("aria-pressed", String(enabled));
  if (!enabled) {
    frame?.remove();
    frame = undefined;
    return;
  }
  if (frame) return;
  frame = document.createElement("iframe");
  frame.hidden = true;
  frame.title = "Google Analytics";
  frame.sandbox.add("allow-scripts", "allow-same-origin");
  frame.referrerPolicy = "no-referrer";
  frame.src = analyticsOrigin;
  document.body.append(frame);
}

async function enableAnalyticsControl() {
  const response = await fetch("/api/v1/analytics");
  if (response.status !== 200) return;
  analyticsOrigin = await response.text();
  if (new URL(analyticsOrigin).origin === location.origin) return;
  control.hidden = false;
  try {
    applyAnalytics(localStorage.getItem(preference) === "on");
  } catch {
    // Analytics can still be enabled for this page.
  }
  control.addEventListener("click", () => {
    const enabled = control.getAttribute("aria-pressed") !== "true";
    applyAnalytics(enabled);
    try {
      if (enabled) localStorage.setItem(preference, "on");
      else localStorage.removeItem(preference);
    } catch {
      // Respect the choice for this page.
    }
  });
}

void enableAnalyticsControl().catch(() => {});
