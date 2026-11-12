// Prerendered SHELL, the gift read client-side — the /search and /today pattern.
//
// A gift link (/gift/#g=…, $lib/gift) carries the whole gift in its fragment,
// which never reaches the server, so every gift is the same document: this
// empty page (generic title, `noindex`, never in a sitemap). onMount reads the
// fragment, checks the book against the API and draws the gift.
//
// Prerendered rather than client-only so it needs no render.yaml rewrite (the
// service is at its route budget, renderRoutes.test.ts): slashed, it builds
// to gift/index.html, which the static host serves for `/gift/` directly. It
// also answers 200 with a real <title> to the link-preview fetch a messaging
// app makes when the link is pasted. Nothing links to it, so svelte.config.js
// seeds it in every locale.
export const prerender = true;
export const trailingSlash = 'always';
