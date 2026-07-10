import * as messages from '$lib/paraglide/messages.js';

/**
 * UI-string access, backed by Paraglide (URL-prefixed locales: /es, /sw, /lg).
 *
 * The active locale comes from the URL, so this is a thin facade over the
 * compiled Paraglide messages: `t('nav.books')` resolves the `nav_books`
 * message in the URL's locale. Keys are the same dotted names the app already
 * uses, mapped to Paraglide's snake_case at lookup.
 *
 * Kept as a facade (rather than rewriting every call site to `m.nav_books()`)
 * to hold the migration diff down; message functions are param-free. Locale
 * switching lives in lang.svelte.ts (`lang.set`).
 */

const toSnake = (key: string): string =>
	key
		.replace(/([a-z0-9])([A-Z])/g, '$1_$2')
		.replace(/\./g, '_')
		.toLowerCase();

type MessageFn = () => string;
const dict = messages as unknown as Record<string, MessageFn>;

class I18n {
	t = (key: string): string => {
		const fn = dict[toSnake(key)];
		return fn ? fn() : key;
	};
}

export const i18n = new I18n();
