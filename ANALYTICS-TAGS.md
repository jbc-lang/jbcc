# Analytics tags for jbc-lang.org and online.jbc-lang.org

Both Google Analytics properties are in the GA account **Sites**
(`a416880891`).

| Site | GA property | Stream ID | Measurement ID | Live tag |
| --- | --- | --- | --- | --- |
| [Documentation](https://jbc-lang.org/) | jbc-lang.org `565446118` | `16391222138` | `G-YJPRDTN9RM` | Tag Manager `GTM-MKW38C6B` |
| [Playground](https://online.jbc-lang.org/) | online.jbc-lang.org `565843356` | `16412629520` | `G-NCPVZT08XG` | Direct Google tag |

## Playground

The [standalone playground](https://github.com/jbc-lang/jbc-playground)
embeds `gtag.js` in its production HTML. It sends one explicit cookieless
`page_view` for `https://online.jbc-lang.org/` after setting denied
Analytics and advertising consent defaults. It skips URLs with query
strings to avoid sending search terms through Enhanced Measurement.
The Google script runs in the editor's origin. The Wasm runner uses its
own sandbox.

A live browser test observed one accepted page view with HTTP 204 and
zero browser cookies. A staged browser test also verified that no
sample project data appeared in Analytics requests. The published
Google tag configuration has user-provided data collection disabled.
Google notes that DebugView can omit events while Analytics cookie
consent is denied.
[Google DebugView guidance](https://support.google.com/analytics/answer/7201382)

The former playground container `GTM-5QTPTVWF` was used by the
`playground-metrics` iframe and the old tag-check page. The live site
uses the direct tag and the same GA4 stream.
[Repository cutover](PLAYGROUND-REPO.md)

## Documentation site

The docs site loads `GTM-MKW38C6B` from `site/head.html`. The November
verification confirmed that it sent data and that user-provided data
collection was disabled. The standard `gtm.start` event is absent in
the docs snippet, and page views were observed.

The older pair `GTM-MTVGQN94` and `G-WCXYWY5LFQ` is retired. Its GA4
property **rk86.ru › jbc-lang.org** (`565815301`) was moved to the GA
Bin on 2026-11-25.
