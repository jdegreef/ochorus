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

/**
 * Count-dependent noun forms beyond English's one/many, for the languages that
 * need them: messages/plurals/<locale>.json maps a `…_one` message key to its
 * forms by CLDR plural category. Arabic says "81 كتابًا" and "5 كتب", Russian
 * "2 книги", "5 книг", "21 книга" — none of which a one/many pair can say, so
 * every count on the site read ungrammatically there. Kept out of the main
 * catalogue (which every locale must mirror key for key) and loaded with it.
 */
type PluralForms = Record<string, Partial<Record<Intl.LDMLPluralRule, string>>>;
const pluralLoaders = import.meta.glob<PluralForms>('/messages/plurals/*.json', {
	import: 'default'
});
const plurals = new Map<string, PluralForms>();
const rules = new Map<string, Intl.PluralRules>();
const rulesFor = (locale: string) => {
	let r = rules.get(locale);
	if (!r) rules.set(locale, (r = new Intl.PluralRules(locale)));
	return r;
};

/** Load (once) the UI catalogue for `locale`. Resolves when `t` can serve it. */
export async function loadUiCatalog(locale: string): Promise<void> {
	if (catalogs.has(locale)) return;
	const load = loaderFor(locale);
	if (!load) return;
	const loadPlurals = pluralLoaders[`/messages/plurals/${locale}.json`];
	const [catalog, forms] = await Promise.all([load(), loadPlurals?.()]);
	if (forms) plurals.set(locale, forms);
	catalogs.set(locale, catalog);
}

const toSnake = (key: string): string =>
	key
		.replace(/([a-z0-9])([A-Z])/g, '$1_$2')
		.replace(/\./g, '_')
		.toLowerCase();

class I18n {
	t = (key: string): string => catalogs.get(getLocale())?.[toSnake(key)] ?? key;
	/**
	 * The noun for a count: `tn(3, 'common.bookOne', 'common.bookMany')`. The
	 * locale's own plural form when messages/plurals has one, else the one/many
	 * pair exactly as before (`n === 1` picks the first).
	 */
	tn = (n: number, oneKey: string, manyKey: string): string => {
		const locale = getLocale();
		const forms = plurals.get(locale)?.[toSnake(oneKey)];
		const form = forms?.[rulesFor(locale).select(n)];
		return form ?? this.t(n === 1 ? oneKey : manyKey);
	};
}

export const i18n = new I18n();

/** `key` in `locale`'s catalogue rather than the page's, loading it first —
 *  for text written for another language's readers (the admin's WhatsApp
 *  post, composed on an English page). */
export async function tIn(locale: string, key: string): Promise<string> {
	await loadUiCatalog(locale);
	return catalogs.get(locale)?.[toSnake(key)] ?? key;
}
