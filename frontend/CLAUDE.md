# Ochorus frontend — SvelteKit conventions

Static-adapter SPA (`adapter-static`, `fallback: 200.html`) against the Django
API. Public content routes are prerendered for SEO (`prerender = true` + an
`entries()` generator); private/admin routes are client-only
(`prerender = false; ssr = false`).

## Data & API

- Every call to the Django API goes through `$lib/api.ts`: `apiFetch` (attaches
  the Supabase Bearer token, forces a JSON content-type) and `apiFetchRaw`
  (multipart / blob — e.g. uploads, CSV). Don't hand-roll `fetch` to the
  backend; auth and error normalisation live in one place.
- Typed domain helpers live in `library-public.ts` / `library-admin.ts` — add
  a helper there rather than an inline endpoint string.

## Svelte 5 runes

- `$derived` for anything computable from existing state; reserve `$effect` for
  genuine side-effects (DOM measurement, subscriptions, storage). An `$effect`
  that writes state is usually a `$derived` in disguise.
- Type `$props()` explicitly; data flows down (callbacks up), never child→parent
  mutation.

## i18n

- Paraglide, URL-prefixed locales (`/es /sw /lg`). The generated `$lib/paraglide`
  is gitignored and produced by Vite — **compile it before `svelte-check`**
  (`npm run check` does this). Chrome i18n (message catalogs) is separate from
  *content* localization (per-language DB rows / translation side-tables).

## Safety & style

- `{@html}` only for server-sanitized content (chapter / sermon body), with a
  comment saying so. Never for untrusted input.
- Component styles stay scoped; colours, spacing and type live in the shared
  tokens (`app.css` / STYLE_GUIDE.md) — so a rebrand or a legibility fix is one
  edit, not a hunt.

## Gates & verification

- `npm run check` must be 0 errors. `npm run test` (vitest) currently **fails
  locally** under jsdom/Node but passes in CI — CI is the gate; don't chase the
  local red (see the `verify-local` skill).
- Verify user-visible changes in the browser (`verify-local` skill). Beware the
  localized-page trap: a persistent session's stored `en` preference
  de-localizes `/lg` URLs — wipe storage or use `curl` for ground truth.
