import glossaryData from './glossary.json';

/**
 * The Ochorus glossary — archaic and theological words from the classics, each
 * with one plain-English definition (`glossary.json`, curated by hand).
 *
 * Two readers of the same file: the chapter reader's tap-to-define popover
 * (`define.svelte.ts`) and the public pages at /glossary/ and
 * /glossary/<term>/. English only, like the words: there is no translated
 * glossary, so the pages are English-only, as the quote and scripture hubs are.
 *
 * The file's ORDER is curated too — the pronouns together, then the
 * where-/there- words, then the vocabulary of prayer, of the farm, of
 * doctrine — which is what "related terms" reads (see `relatedTerms`).
 */

const raw = glossaryData as Record<string, string>;

/** Every term, in the file's curated (thematic) order. Keys starting `_` are notes. */
const CURATED: string[] = Object.keys(raw).filter((k) => !k.startsWith('_'));

/** Every term, A–Z. */
export const GLOSSARY_TERMS: string[] = [...CURATED].sort((a, b) => a.localeCompare(b, 'en'));

export const isGlossaryTerm = (term: string): boolean => CURATED.includes(term);

/** A term's definition, or '' for a word not in the glossary. */
export const definitionOf = (term: string): string => (isGlossaryTerm(term) ? raw[term] : '');

/** The term's own page. Slashed: it prerenders to glossary/<term>/index.html. */
export const glossaryHref = (term: string): string => `/glossary/${term}/`;

/**
 * The glossary entry a word from the text belongs to — itself, or with a light
 * plural/possessive strip ("covenants", "sinner's") — or null.
 */
export function glossaryTermFor(word: string): string | null {
	if (word.startsWith('_')) return null;
	if (isGlossaryTerm(word)) return word;
	const stripped = word.replace(/['’]s$/, '').replace(/s$/, '');
	return isGlossaryTerm(stripped) ? stripped : null;
}

/** The term as a title ("Wherefore", "Mercy-seat"). */
export const titleCase = (term: string): string => term.charAt(0).toUpperCase() + term.slice(1);

/** Terms grouped under their initial letter, A–Z. */
export function byLetter(): { letter: string; terms: string[] }[] {
	const groups: { letter: string; terms: string[] }[] = [];
	for (const term of GLOSSARY_TERMS) {
		const letter = term.charAt(0).toUpperCase();
		const last = groups[groups.length - 1];
		if (last?.letter === letter) last.terms.push(term);
		else groups.push({ letter, terms: [term] });
	}
	return groups;
}

/** Same family: one is the other plus an ending or a prefix (abide/abideth,
 *  circumcision/uncircumcision), or they share a long stem (beseech/besought
 *  doesn't; importunate/importunity does). */
const FAMILY_STEM = 5;
function sameFamily(a: string, b: string): boolean {
	const [short, long] = a.length < b.length ? [a, b] : [b, a];
	if (short.length >= 4 && long.includes(short)) return true;
	return a.length >= FAMILY_STEM && b.length >= FAMILY_STEM && a.slice(0, FAMILY_STEM) === b.slice(0, FAMILY_STEM);
}

/**
 * Up to `max` related terms: the word's own family first (abide → abideth),
 * then its neighbours in the glossary's curated order, which groups the words
 * by theme (wherefore → whence, wherein). Never the term itself.
 */
export function relatedTerms(term: string, max = 6): string[] {
	const at = CURATED.indexOf(term);
	if (at < 0) return [];
	const family = CURATED.filter((t) => t !== term && sameFamily(t, term));
	const near: string[] = [];
	for (let d = 1; d <= CURATED.length && near.length < max; d++) {
		for (const i of [at - d, at + d]) if (CURATED[i]) near.push(CURATED[i]);
	}
	return [...new Set([...family, ...near])].slice(0, max);
}
