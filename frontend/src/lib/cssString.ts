/**
 * Quote a value for use as a CSS string literal (e.g. `content:`).
 *
 * The reason this exists: the biography page passes localized callout labels
 * into CSS custom properties, which `::before { content: var(--label-…) }` then
 * renders. Interpolating a translation straight into `'…'` works for every
 * message we happen to ship today and breaks the moment one contains an
 * apostrophe — "L'écoute", "d'oração" — because the string terminates early and
 * takes the rest of the declaration with it. Nothing errors; the label simply
 * disappears in that one locale, which is exactly the kind of bug nobody finds.
 *
 * Escapes what CSS requires and nothing more: a backslash, the quote itself,
 * and literal newlines (a raw newline is invalid inside a CSS string).
 */
export function cssString(value: string): string {
	return `'${value.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\r?\n/g, '\\A ')}'`;
}
