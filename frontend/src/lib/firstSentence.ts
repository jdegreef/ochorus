import { truncateMeta } from '$lib/seo';

/**
 * The first sentence of a summary — the author page's one-line "who they
 * were" under the name (design review #13). There is no tagline field, so the
 * line is the summary's own opening rather than new copy.
 *
 * A full stop ends the sentence only where it can: not after an initial
 * ("C. S. Lewis", "أ. و. توزر"), a "c." date or a title ("Dr", "St"), and not
 * before a lowercase letter. The sentence ends at `. ! ? । ؟` followed by a
 * space or the end. A long one is held to `max` on a word boundary.
 */
const ABBREVIATION = /^(?:jr|sr|st|ste|dr|mr|mrs|ms|rev|revd|fr|mt|ca|vs|etc|no|vol|ed|डॉ)$/i;

export function firstSentence(text: string, max = 240): string {
	const clean = (text ?? '').replace(/\s+/g, ' ').trim();
	for (const m of clean.matchAll(/[.!?।؟](?= |$)/g)) {
		const end = m.index + 1;
		if (m[0] === '.') {
			const word = (clean.slice(0, m.index).match(/(\p{L}+)$/u) ?? ['', ''])[1];
			if ([...word].length <= 1 || ABBREVIATION.test(word)) continue;
			if (/^\p{Ll}/u.test(clean.slice(end + 1))) continue;
		}
		return truncateMeta(clean.slice(0, end), max);
	}
	return truncateMeta(clean, max);
}
