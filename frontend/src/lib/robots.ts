import { locales } from "$lib/paraglide/runtime";

/**
 * Paths with nothing to index: account/admin shells, and internal search.
 * Never advertised in the sitemap (sitemap.ts filters its static pages by this
 * list) — a URL both advertised and disallowed is a Search Console error.
 */
export const APP_ONLY = [
  "/admin",
  "/settings",
  "/login",
  "/account",
  "/notebook",
  "/favorites",
  "/welcome",
  "/reset-password",
  "/search",
] as const;

/**
 * What robots.txt blocks for an app-only path. Search is the exception: its
 * results (`?q=…`, thin and endlessly parameterised) are blocked, but the bare
 * page stays crawlable so its `noindex` can be read — a disallowed URL linked
 * from every page's nav ends up "Indexed, though blocked by robots.txt".
 */
const blocked = (path: string) => (path === "/search" ? "/search?" : path);

/**
 * One `Disallow` per app-only path per UI locale. A Disallow is a path PREFIX,
 * so `/search` never covered `/es/search?q=…` — every locale's copy was open.
 */
export const appOnlyDisallows = (): string[] =>
  APP_ONLY.flatMap((p) =>
    locales.map((l) => `Disallow: ${l === "en" ? "" : `/${l}`}${blocked(p)}`),
  );

/**
 * AI assistants and answer engines, named so the welcome is explicit rather
 * than implied by `*`: a host or CDN "block AI bots" default, or a later
 * blanket rule, would otherwise shut them out without anyone noticing. They
 * share the `*` group (several User-agent lines may open one group, RFC 9309
 * §2.2.1), so they obey exactly the same Disallows — a SEPARATE named group
 * would make each bot ignore every `*` rule.
 *
 * Search/answer fetchers first (they cite and link the page), then the
 * crawlers that gather training data, allowed too as a founder decision
 * (2026-11-16): the classics are public domain and the point is reach. To stop
 * training only, delete the second list.
 */
export const AI_SEARCH_AGENTS = [
  "OAI-SearchBot",
  "ChatGPT-User",
  "Claude-SearchBot",
  "Claude-User",
  "PerplexityBot",
  "Perplexity-User",
  "DuckAssistBot",
  "MistralAI-User",
  "Applebot",
] as const;
export const AI_TRAINING_AGENTS = [
  "GPTBot",
  "ClaudeBot",
  "Google-Extended",
  "Applebot-Extended",
  "CCBot",
  "meta-externalagent",
  "Amazonbot",
] as const;

/** The opening of the one shared group: `*`, then every named AI agent. */
export const userAgentLines = (): string[] => [
  "User-agent: *",
  ...[...AI_SEARCH_AGENTS, ...AI_TRAINING_AGENTS].map(
    (a) => `User-agent: ${a}`,
  ),
];
