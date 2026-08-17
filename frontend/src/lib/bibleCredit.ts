/**
 * Credit lines for Bible texts whose licence asks for one.
 *
 * Ochorus is a public-domain library and its Bibles were public domain too —
 * KJV, Van Dyck, Kulish, Almeida — right up until Hindi. The Indian Revised
 * Version is the only Hindi text on Take Root that is not somebody's
 * proprietary edition, and it is CC BY-SA 4.0. Share-Alike binds derivatives of
 * the Bible text itself rather than a library that quotes it, but BY still
 * wants the credit carried wherever the verses appear — and they appear inside
 * ordinary sermon and biography prose, not in a Bible widget we could hang a
 * notice on. So the credit goes in the footer, which is on every page.
 *
 * The strings are duplicated from `Language.bible_attribution` in the backend
 * seed, deliberately and with a test holding them equal
 * (`library.tests_bible_credit`). They cannot simply be fetched: the reader is
 * a prerendered static site, and a licence notice that depends on a runtime API
 * call is a licence notice that is missing whenever the call fails.
 *
 * Empty (a locale absent from the map) is the normal case and means public
 * domain — nothing owed, nothing shown.
 */
export const BIBLE_CREDIT: Readonly<Record<string, string>> = {
	hi:
		'Scripture quotations are from the Indian Revised Version (IRV), ' +
		'© 2017–2019 Bridge Connectivity Solutions, licensed under ' +
		'CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).'
};

/** The credit line for a locale, or '' when its Bible is public domain. */
export const bibleCredit = (locale: string): string => BIBLE_CREDIT[locale] ?? '';

export interface CreditPart {
	text: string;
	/** Set when this run of text is a URL and should render as a link. */
	href?: string;
}

/**
 * Split a credit into text and link runs.
 *
 * The URL lives inside the sentence rather than in a separate field so the
 * string stays byte-identical to `Language.bible_attribution` and the two can be
 * compared directly. Linkifying at render time costs one regex and gets the
 * licence URI CC BY-SA 4.0 §3(a)(1)(A)(iii) asks for — a bare URL printed as
 * text is arguably compliant and definitely worse for the reader.
 */
export function creditParts(credit: string): CreditPart[] {
	const parts: CreditPart[] = [];
	let last = 0;
	for (const m of credit.matchAll(/https?:\/\/[^\s)]+/g)) {
		const at = m.index ?? 0;
		if (at > last) parts.push({ text: credit.slice(last, at) });
		parts.push({ text: m[0], href: m[0] });
		last = at + m[0].length;
	}
	if (last < credit.length) parts.push({ text: credit.slice(last) });
	return parts;
}
