// Prerendered SHELL, client-side results.
//
// This was `prerender = false; ssr = false`, which meant /search served a 4KB
// SPA stub: no <h1>, no description, nothing for a crawler. It is a top-level
// destination in the nav AND listed in sitemap.xml, so it was the one browse
// page we advertise to search engines with no content in it at all.
//
// Prerendering is safe because nothing depending on the query string runs
// during it: the `?q=` read lives in an $effect and the topic/popular fetches
// live in onMount — both client-only. The build emits the empty state (title,
// tagline, search box, ways-in) and the client then hydrates, reads the URL and
// runs the actual search. Same pattern /biographies already uses for its
// `?q=&filter=&sort=` controls.
export const prerender = true;
