async function loadAnalytics() {
  const response = await fetch("/api/v1/analytics");
  if (response.status !== 200) return;

  const url = new URL(await response.text());
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
