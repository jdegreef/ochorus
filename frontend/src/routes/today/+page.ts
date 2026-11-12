// Prerendered SHELL, client-side readings — the /search pattern.
//
// This was `prerender = false; ssr = false`, so /today was served the SPA stub
// (200.html), whose raw HTML says noindex ($lib/fallbackShell): no crawler ever
// saw the page. The day still can't be prerendered — "today" is the reader's
// LOCAL date ($lib/dailyDate), and a build would freeze on its own day — but
// nothing date-bound runs during prerender: DailyShelf fetches the readings in
// onMount, so the build emits the header and tagline only, and the client
// fills in the day's cards (and the title/description that name them).
// render.yaml rewrites /today and /:lang/today to this file; /today/<slug>
// (one book's day, with `?d=`) stays client-only.
export const prerender = true;
