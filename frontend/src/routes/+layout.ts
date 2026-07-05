// Public pages are prerendered to static HTML at build time for SEO (the load
// functions fetch from the API during the build). The reader and search opt out
// (prerender=false + ssr=false) and run as a client-side SPA.
export const prerender = true;
