if (window.parent !== window) {
  const container = "GTM-5QTPTVWF";
  const measurement = "G-NCPVZT08XG";
  const pageLocation = "https://online.jbc-lang.org/";
  window.dataLayer = window.dataLayer || [];

  function gtag() {
    window.dataLayer.push(arguments);
  }

  // A new client ID on each opt-in page load avoids a persistent analytics ID
  // and lets the tag send a page view from the cross-origin frame.
  const clientID = Array.from(crypto.getRandomValues(new Uint32Array(2))).join(".");
  gtag("consent", "default", {
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: "denied",
  });
  // Disable automatic page views before GTM initializes its Google tag.
  gtag("set", { send_page_view: false, page_location: pageLocation });
  gtag("js", new Date());
  gtag("config", measurement, {
    client_id: clientID,
    send_page_view: false,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
  });
  gtag("event", "page_view", {
    send_to: measurement,
    page_location: pageLocation,
    page_title: "jBC Playground",
  });
  window.dataLayer.push({ "gtm.start": Date.now(), event: "gtm.js" });

  const script = document.createElement("script");
  script.async = true;
  script.referrerPolicy = "no-referrer";
  script.src = `https://www.googletagmanager.com/gtm.js?id=${container}`;
  document.head.append(script);
}
