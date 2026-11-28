import glossaryData from './glossary.json';
import headsData from './glossaryHeads.json';

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

/** A word's family alone (abide → abideth, abase → abasement) — the term
 *  page's "Same family" row; `relatedTerms` leads with these too. */
export const wordFamily = (term: string): string[] =>
	isGlossaryTerm(term) ? CURATED.filter((t) => t !== term && sameFamily(t, term)) : [];

/**
 * A term's dictionary head: part of speech, a plain respelling (stress in
 * capitals) and a one-line origin (`glossaryHeads.json` — drafted, for the
 * founder to check). Null for a word without one.
 */
export interface GlossaryHead {
	pos: string;
	say: string;
	origin: string;
}
const heads = headsData as Record<string, GlossaryHead | string>;
export const headOf = (term: string): GlossaryHead | null => {
	const h = isGlossaryTerm(term) ? heads[term] : undefined;
	return h && typeof h === 'object' ? h : null;
};

/**
 * The index's two shelves, cut where the file's curated order turns from the
 * old English of the King James Bible (thou … betoken) to the vocabulary of
 * doctrine (covenant onward).
 */
const FAITH_FROM = 'covenant';
const cut = CURATED.indexOf(FAITH_FROM);
export const OLD_WORDS: string[] = cut > 0 ? CURATED.slice(0, cut) : [];
export const FAITH_WORDS: string[] = cut > 0 ? CURATED.slice(cut) : [];

/**
 * "Ten words every new Christian should know": the great words of the gospel in
 * the order they tell it (God's covenant, the Mediator, the atonement, and what
 * it gives the believer). Editorial, so a list in code; a word dropped from the
 * glossary is skipped rather than shown as a dead link.
 */
const TEN_WORDS = [
	'covenant',
	'mediator',
	'atonement',
	'propitiation',
	'regeneration',
	'justification',
	'adoption',
	'sanctification',
	'intercession',
	'providence'
];
export const KEY_WORDS: string[] = TEN_WORDS.filter(isGlossaryTerm);

/**
 * The index's find-as-you-type: words that begin with the query first, then
 * words that contain it, then words whose definition uses it. Case-insensitive;
 * an empty query matches nothing (the page shows the full A–Z instead).
 */
export function findTerms(query: string): string[] {
	const q = query.trim().toLowerCase();
	if (!q) return [];
	const starts = GLOSSARY_TERMS.filter((t) => t.startsWith(q));
	const contains = GLOSSARY_TERMS.filter((t) => !t.startsWith(q) && t.includes(q));
	const seen = new Set([...starts, ...contains]);
	const inDefinition = GLOSSARY_TERMS.filter(
		(t) => !seen.has(t) && definitionOf(t).toLowerCase().includes(q)
	);
	return [...starts, ...contains, ...inDefinition];
}

/** The word of the day, the same for every reader on a date (`dayIndex`). */
export const wordOfTheDay = (index: number): string => GLOSSARY_TERMS[index % GLOSSARY_TERMS.length];

/**
 * The glossary words a chapter uses, for the "Words in this chapter" links at
 * its end — the crawlable path to the term pages, which the reader otherwise
 * reaches only by tapping a word (`define.svelte.ts`). Doctrine first (the
 * words people search the meaning of: "sanctification", "propitiation"), then
 * the old English that fills a slot left over; each group by how often the
 * chapter uses it. `text` is plain text, or HTML (tags are dropped).
 */
export function glossaryTermsIn(text: string, max = 5): string[] {
	const counts = new Map<string, number>();
	const plain = text.replace(/<[^>]*>/g, ' ').toLowerCase();
	for (const word of plain.match(/[a-z][a-z'’-]*[a-z]|[a-z]/g) ?? []) {
		const term = glossaryTermFor(word);
		if (term) counts.set(term, (counts.get(term) ?? 0) + 1);
	}
	const faith = new Set(FAITH_WORDS);
	const ranked = (inFaith: boolean) =>
		[...counts.entries()]
			.filter(([term]) => faith.has(term) === inFaith)
			.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'en'))
			.map(([term]) => term);
	return [...ranked(true), ...ranked(false)].slice(0, max);
}
