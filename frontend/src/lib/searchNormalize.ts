/**
 * Text normalization for the in-book search index — the device rung of
 * device → book → library (see SearchDrawer). Two levels, and which applies is
 * the caller's call:
 *
 *   - `foldText` is SAFE FOR EVERY SCRIPT: case-fold, strip combining diacritics,
 *     and straighten curly quotes/apostrophes. So "Béni" matches "beni", and a
 *     smart-quoted "don’t" matches a typed "don't". Nothing here is
 *     language-specific, so it runs for all content.
 *   - `stemWord` is the Porter stemmer — it folds ENGLISH inflections onto one
 *     root, so "promise / promises / promised / promising" all match, and
 *     "pray / prays / praying / prayed" all match. It runs ONLY on English
 *     content (the caller gates it): its suffix rules would mangle Arabic or
 *     Devanagari. It is a real, well-known algorithm precisely because guessing
 *     at stems ad hoc is worse than none (the stance `searchHits` takes for
 *     highlighting); different roots ("praying" ↔ "prayer") still don't fold and
 *     are left to the server's Postgres FTS, one click away via "search wider".
 *
 * All pure and unit-tested; the drawer builds its index and its query through
 * `normalizeForSearch`, and locates the matched word for highlighting through
 * `firstMatchSpan`.
 */

/** Case-fold, strip diacritics, straighten quotes. Length-preserving for ASCII,
 *  so a fold-space index maps 1:1 back to the raw text for English content. */
export function foldText(s: string): string {
	return s
		.toLowerCase()
		.normalize('NFD')
		.replace(/[̀-ͯ]/g, '') // combining diacritical marks
		.replace(/[‘’ʼ]/g, "'") // curly / modifier apostrophes
		.replace(/[“”]/g, '"'); // curly double quotes
}

// --- Porter stemmer ---------------------------------------------------------
// A faithful port of M.F. Porter's 1980 algorithm ("An algorithm for suffix
// stripping"). Operates on a lowercased ASCII word. Consistency across a root's
// inflections is the whole point — the exact stem string ("happi", "promis") is
// never shown, only compared, so the algorithm's known-quirky outputs are fine.

const isConsonant = (w: string, i: number): boolean => {
	const c = w[i];
	if (c === 'a' || c === 'e' || c === 'i' || c === 'o' || c === 'u') return false;
	if (c === 'y') return i === 0 ? true : !isConsonant(w, i - 1);
	return true;
};

/** m(): the number of VC sequences in the stem — Porter's "measure". */
function measure(w: string): number {
	let n = 0;
	let prevVowel = false;
	for (let i = 0; i < w.length; i++) {
		const vowel = !isConsonant(w, i);
		if (prevVowel && !vowel) n++;
		prevVowel = vowel;
	}
	return n;
}

const hasVowel = (w: string): boolean => {
	for (let i = 0; i < w.length; i++) if (!isConsonant(w, i)) return true;
	return false;
};

const endsDoubleConsonant = (w: string): boolean =>
	w.length >= 2 && w[w.length - 1] === w[w.length - 2] && isConsonant(w, w.length - 1);

/** *o — stem ends consonant-vowel-consonant where the last is not w, x or y. */
const endsCVC = (w: string): boolean => {
	const n = w.length;
	if (n < 3) return false;
	if (!isConsonant(w, n - 1) || isConsonant(w, n - 2) || !isConsonant(w, n - 3)) return false;
	const c = w[n - 1];
	return c !== 'w' && c !== 'x' && c !== 'y';
};

/** Replace `suf` with `rep` iff m(stem) satisfies `cond`. Returns the new word or null. */
function replaceIf(w: string, suf: string, rep: string, cond?: (stem: string) => boolean): string | null {
	if (!w.endsWith(suf)) return null;
	const stem = w.slice(0, w.length - suf.length);
	if (cond && !cond(stem)) return null;
	return stem + rep;
}

const STEP2: [string, string][] = [
	['ational', 'ate'], ['tional', 'tion'], ['enci', 'ence'], ['anci', 'ance'],
	['izer', 'ize'], ['bli', 'ble'], ['alli', 'al'], ['entli', 'ent'], ['eli', 'e'],
	['ousli', 'ous'], ['ization', 'ize'], ['ation', 'ate'], ['ator', 'ate'],
	['alism', 'al'], ['iveness', 'ive'], ['fulness', 'ful'], ['ousness', 'ous'],
	['aliti', 'al'], ['iviti', 'ive'], ['biliti', 'ble'], ['logi', 'log']
];
const STEP3: [string, string][] = [
	['icate', 'ic'], ['ative', ''], ['alize', 'al'], ['iciti', 'ic'],
	['ical', 'ic'], ['ful', ''], ['ness', '']
];
const STEP4: string[] = [
	'al', 'ance', 'ence', 'er', 'ic', 'able', 'ible', 'ant', 'ement', 'ment', 'ent',
	'ou', 'ism', 'ate', 'iti', 'ous', 'ive', 'ize'
];

/** Fold one ENGLISH word onto its Porter stem. Only applied by
 *  `normalizeForSearch` when the content is English. Short words are returned
 *  unchanged (nothing to strip usefully). */
export function stemWord(word: string): string {
	if (word.length <= 2) return word;
	let w = word;

	// Step 1a — plurals.
	if (w.endsWith('sses')) w = w.slice(0, -2);
	else if (w.endsWith('ies')) w = w.slice(0, -2);
	else if (w.endsWith('ss')) {
		/* keep */
	} else if (w.endsWith('s')) w = w.slice(0, -1);

	// Step 1b — -ed / -ing.
	let step1bHitEdIng = false;
	if (w.endsWith('eed')) {
		if (measure(w.slice(0, -3)) > 0) w = w.slice(0, -1);
	} else if (w.endsWith('ed') && hasVowel(w.slice(0, -2))) {
		w = w.slice(0, -2);
		step1bHitEdIng = true;
	} else if (w.endsWith('ing') && hasVowel(w.slice(0, -3))) {
		w = w.slice(0, -3);
		step1bHitEdIng = true;
	}
	if (step1bHitEdIng) {
		if (w.endsWith('at') || w.endsWith('bl') || w.endsWith('iz')) w += 'e';
		else if (endsDoubleConsonant(w) && !/(ll|ss|zz)$/.test(w)) w = w.slice(0, -1);
		else if (measure(w) === 1 && endsCVC(w)) w += 'e';
	}

	// Step 1c — y → i.
	if (w.endsWith('y') && hasVowel(w.slice(0, -1))) w = w.slice(0, -1) + 'i';

	const applyList = (rules: [string, string][], minM: number) => {
		for (const [suf, rep] of rules) {
			const next = replaceIf(w, suf, rep, (stem) => measure(stem) > minM);
			if (next !== null) {
				w = next;
				break;
			}
		}
	};
	applyList(STEP2, 0); // step 2
	applyList(STEP3, 0); // step 3

	// Step 4 — remove a suffix when m(stem) > 1.
	for (const suf of STEP4) {
		if (!w.endsWith(suf)) continue;
		const stem = w.slice(0, w.length - suf.length);
		if (measure(stem) > 1) {
			w = stem;
			break;
		}
	}
	// 'ion' is only valid after s/t; handle it explicitly (STEP4 omits it).
	if (w.endsWith('ion')) {
		const stem = w.slice(0, -3);
		if (measure(stem) > 1 && /[st]$/.test(stem)) w = stem;
	}

	// Step 5a — trailing e.
	if (w.endsWith('e')) {
		const stem = w.slice(0, -1);
		const m = measure(stem);
		if (m > 1 || (m === 1 && !endsCVC(stem))) w = stem;
	}
	// Step 5b — collapse a double 'l' when m > 1.
	if (measure(w) > 1 && endsDoubleConsonant(w) && w.endsWith('l')) w = w.slice(0, -1);

	return w;
}

/** Normalize a string for the search index or the query: fold always, and stem
 *  each ASCII word when `english`. */
export function normalizeForSearch(text: string, english: boolean): string {
	const folded = foldText(text);
	return english ? folded.replace(/[a-z']+/g, (w) => stemWord(w)) : folded;
}

/**
 * Where the query first matches in `text`, as a [start, length] span of the RAW
 * text, or null. Scans word by word and compares each word's normalized form to
 * the normalized query, so a highlight can mark the actual inflected word
 * ("prayers") that a stemmed query ("prayer") landed on. The drawer tries a
 * literal match first; this is the fallback for a match found only after
 * normalization.
 *
 * SINGLE-WORD spans only: a needle that spans a space (a multi-word query that
 * matched only after folding, e.g. a curly vs straight apostrophe) never equals
 * a single word's normalized form, so this returns null and the caller shows an
 * un-highlighted head snippet — still a correct hit, just without the window.
 */
export function firstMatchSpan(
	text: string,
	query: string,
	english: boolean
): [number, number] | null {
	const needle = normalizeForSearch(query.trim(), english);
	if (!needle) return null;
	const words = /\S+/g;
	let m: RegExpExecArray | null;
	while ((m = words.exec(text)) !== null) {
		if (normalizeForSearch(m[0], english).includes(needle)) {
			return [m.index, m[0].length];
		}
	}
	return null;
}
