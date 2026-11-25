async function loadAnalytics() {
  const origin = document.documentElement.dataset.analyticsOrigin;
  if (!origin) return;
  const url = new URL(origin);
  if (url.protocol !== "https:" || url.origin === location.origin) return;

  const frame = document.createElement("iframe");
  frame.hidden = true;
  frame.title = "Google Analytics";
  frame.sandbox.add("allow-scripts", "allow-same-origin");
  frame.referrerPolicy = "no-referrer";
  frame.src = url.href;
  document.body.append(frame);
}

void loadAnalytics().catch(() => {});
