import { getLocale } from '$lib/paraglide/runtime';

/**
 * UI-string access: `t('nav.books')` resolves the `nav_books` message in the
 * URL's locale. Keys are the same dotted names the app already uses, mapped to
 * the catalogue's snake_case at lookup.
 *
 * Backed by ONE locale's catalogue (messages/<locale>.json), loaded before the
 * page renders — not by Paraglide's compiled messages. Those carry every
 * locale inside every message function, and a lookup by a computed key can't
 * be tree-shaken, so `import * as messages` here put all ~1,600 strings in all
 * twelve languages (1.4 MB of JavaScript) on every page, for every reader. A
 * phone spent hundreds of milliseconds parsing it while the reader's first taps
 * waited — Search Console's mobile INP failure (2026-10). A document's locale
 * is fixed (a cross-locale navigation is a full load; see +layout.svelte), so
 * one catalogue per document is all a page ever needs.
 *
 * The catalogue is loaded by `loadUiCatalog`: in `hooks.client.ts`'s `init`
 * (before hydration), in `hooks.server.ts`'s `handle` (before the prerender
 * renders), and in the vitest setup. Components that call Paraglide's `m.*()`
 * directly are unaffected — those imports tree-shake to the messages they use.
 *
 * messageCatalogues.test.ts fails when a locale lacks a key English has, so
 * no English fallback is carried here; an unknown key renders as itself.
 */

type Catalog = Record<string, string>;

const loaders = import.meta.glob<Catalog>('/messages/*.json', { import: 'default' });
const catalogs = new Map<string, Catalog>();

const loaderFor = (locale: string) => loaders[`/messages/${locale}.json`];

/** Load (once) the UI catalogue for `locale`. Resolves when `t` can serve it. */
export async function loadUiCatalog(locale: string): Promise<void> {
	if (catalogs.has(locale)) return;
	const load = loaderFor(locale);
	if (!load) return;
	catalogs.set(locale, await load());
}

const toSnake = (key: string): string =>
	key
		.replace(/([a-z0-9])([A-Z])/g, '$1_$2')
		.replace(/\./g, '_')
		.toLowerCase();

class I18n {
	t = (key: string): string => catalogs.get(getLocale())?.[toSnake(key)] ?? key;
}

export const i18n = new I18n();
