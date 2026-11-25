# Analytics tags for jbc-lang.org and online.jbc-lang.org

Checked on 2026-11-25 in Google Analytics, in both repositories, and on
the live sites.

All Google Analytics properties are in the GA account **Sites**
(`a416880891`).

| Site | GA property | Stream (ID) | Measurement ID | Tag Manager container |
| --- | --- | --- | --- | --- |
| <https://jbc-lang.org> (docs, GitHub Pages, repo `temenos-documentation`) | jbc-lang.org `565446118` | jbc-lang.org `16391222138` | `G-YJPRDTN9RM` | `GTM-MKW38C6B` |
| <https://online.jbc-lang.org> (playground, this repo) | online.jbc-lang.org `565843356` | online.jbc-lang.org `16412629520` | `G-NCPVZT08XG` | `GTM-5QTPTVWF` |

## Rules

- The docs site loads `GTM-MKW38C6B` from `site/head.html`. GA reports
  data flowing.
- The hosted playground loads `GTM-5QTPTVWF` on page load,
  inside an iframe at `https://jbc-online-metrics.web.app`. The frame's
  code is `playground/analytics/tag.js` and `index.html`, and
  `/api/v1/analytics` returns the frame's address.
  `playground/analytics/tag-check.html` loads the same container as a
  full page, so Google's tag installation check can see it.
- Each container sends only to its own measurement ID. Never put the
  docs IDs on the playground or the playground IDs on the docs site.
- **Retired, do not use:** `GTM-MTVGQN94` and `G-WCXYWY5LFQ`. Their
  property (rk86.ru › jbc-lang.org, `565815301`) was moved to the GA Bin
  on 2026-11-25 and can be restored for 35 days. The container is still
  published. Check its usage before retiring it.

## Deployment follow-up on 2026-11-25

- The metrics frame sends one cookieless `page_view` for
  `https://online.jbc-lang.org/`. A live browser test verified the
  destination, page location, event count, and HTTP 204 response.
- `/tag-check.html` sets denied consent defaults, suppresses automatic
  page views, and blocks analytics requests through its content security
  policy. It still loads the playground container for inspection.
- User-provided data capabilities were disabled in both containers.
  The setting was published as Version 2 in each workspace.
- GA4 Realtime visibility remains unverified. The frame keeps
  `analytics_storage` denied. Google notes that DebugView can omit
  events when analytics cookie consent is denied.
  [Google DebugView guidance](https://support.google.com/analytics/answer/7201382).

## Small issue on the docs site

`site/head.html` doesn't add the
`{'gtm.start': Date.now(), event: 'gtm.js'}` entry that Google's
standard snippet includes. Data flows anyway.
