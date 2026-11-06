/**
 * The first sentence of a summary: the author page's one-line "who they
 * were" under the name (design review #13). There is no tagline field, so the
 * line is the summary's own opening rather than new copy.
 *
 * A sentence ends at `. ! ? । ؟ ።`, optionally followed by a closing quote or
 * bracket, then a space or the end. A full stop does not end it after an
 * initial ("C. S. Lewis", "أ. و. توزر"), a "c." date or a title ("Dr", "St",
 * "डॉ"), or before a lowercase letter. A long sentence is cut on a word
 * boundary at `max`, with an ellipsis.
 */
const ABBREVIATION = /^(?:jr|sr|st|ste|dr|mr|mrs|ms|rev|revd|fr|mt|ca|vs|etc|no|vol|ed|डॉ)$/i;
/** One letter with its combining marks: an initial. */
const INITIAL = /^\p{L}\p{M}*$/u;
const END = /[.!?।؟።]["”’»)]*(?= |$)/g;

export function firstSentence(text: string, max = 180): string {
	const clean = (text ?? '').replace(/\s+/g, ' ').trim();
	let sentence = clean;
	for (const m of clean.matchAll(END)) {
		const end = m.index + m[0].length;
		if (m[0] === '.') {
			// The token before the stop, without an opening bracket or quote.
			const token = (clean.slice(0, m.index).match(/(\S+)$/)?.[1] ?? '').replace(/^["“‘«(]+/, '');
			if (INITIAL.test(token) || ABBREVIATION.test(token)) continue;
			if (/^\p{Ll}/u.test(clean.slice(end + 1))) continue;
		}
		sentence = clean.slice(0, end);
		break;
	}
	if (sentence.length <= max) return sentence;
	const cut = sentence.slice(0, max);
	const space = cut.lastIndexOf(' ');
	return (space > 0 ? cut.slice(0, space) : cut).replace(/[\s,;:—–-]+$/, '') + '…';
}
