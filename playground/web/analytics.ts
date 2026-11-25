async function loadAnalytics() {
  const address = document.documentElement.dataset.analyticsFrame;
  if (!address) return;
  const url = new URL(address);
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
