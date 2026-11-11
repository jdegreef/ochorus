import { locales } from '$lib/paraglide/runtime';

/**
 * Near-miss slug recovery for the not-found page.
 *
 * A link to `/authors/charles-spurgeon/` 404s: the page is
 * `/authors/charles-h-spurgeon/`. The 404 is the SPA shell (scripts/build-404.mjs),
 * so the app's own not-found page runs, and it already holds — or can cheaply
 * fetch — the shelf the slug should have named. This finds the slug that was
 * meant:
 *
 *   * an ALIAS — the same words once initials ("h", "l"), "saint"/"st", a
 *     leading "the", accents, case and punctuation are set aside. When exactly
 *     one slug is the asked one's alias, the page forwards to it.
 *   * otherwise NEAR slugs — a small edit distance, or one's words contained in
 *     the other's ("spurgeon" → "charles-h-spurgeon") — offered as "Did you
 *     mean…" links, never followed on their own.
 *
 * Pure, so the not-found page stays markup and this stays tested.
 */

/** The sections whose detail page this can recover — each has a list endpoint. */
export const RECOVERABLE = ['authors', 'books', 'sermons'] as const;
export type RecoverableSection = (typeof RECOVERABLE)[number];

/** Words that never tell two slugs apart. Single letters (initials) go too. */
const NOISE = new Set(['saint', 'st', 'the']);

/** A slug's comparable words: accents folded, initials and noise dropped. */
export function slugWords(slug: string): string[] {
	return slug
		.normalize('NFD')
		.replace(/[̀-ͯ]/g, '')
		.toLowerCase()
		.split(/[^a-z0-9]+/)
		.filter((w) => w && !/^[a-z]$/.test(w) && !NOISE.has(w));
}

/** The alias key: two slugs with the same key name the same thing. */
export const slugKey = (slug: string): string => slugWords(slug).join('-');

/** Levenshtein distance, bailing out once it passes `max`. */
export function editDistance(a: string, b: string, max = Infinity): number {
	if (Math.abs(a.length - b.length) > max) return max + 1;
	let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
	for (let i = 1; i <= a.length; i++) {
		const row = [i];
		let best = i;
		for (let j = 1; j <= b.length; j++) {
			const v = Math.min(
				prev[j] + 1,
				row[j - 1] + 1,
				prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)
			);
			row.push(v);
			if (v < best) best = v;
		}
		if (best > max) return max + 1;
		prev = row;
	}
	return prev[b.length];
}

/** How far `cand` is from `asked` (0 = alias), or null when it is no near miss. */
function distance(askedKey: string, askedWords: string[], cand: string): number | null {
	const key = slugKey(cand);
	if (!key) return null;
	if (key === askedKey) return 0;
	const words = slugWords(cand);
	// Every word of one inside the other: a surname for a full name, a short
	// title for a long one. Ranked behind a typo of the whole slug.
	const inside = (xs: string[], ys: string[]) => xs.every((x) => ys.includes(x));
	if (inside(askedWords, words) || inside(words, askedWords)) return 0.5;
	// The same, with a one-letter slip in a longer word ("humilty" → "humility-2").
	const near = (x: string) => words.some((y) => x.length >= 5 && editDistance(x, y, 1) <= 1);
	if (askedWords.every(near)) return 0.6;
	// A typo: a quarter of the length, at least one and at most three edits.
	const max = Math.min(3, Math.max(1, Math.floor(askedKey.length / 4)));
	const d = editDistance(askedKey, key, max);
	return d <= max ? d / askedKey.length + 0.25 : null;
}

export interface SlugRecovery<T> {
	/** The one alias of the asked slug, to forward to — or null. */
	forward: T | null;
	/** Up to `max` near misses, closest first, for "Did you mean…". */
	suggestions: T[];
}

/**
 * The slug `asked` most likely meant, among `items` (anything with a `slug`).
 * Nothing when `asked` is itself one of them: then the page exists and failed
 * for another reason, and forwarding could only loop.
 */
export function recoverSlug<T extends { slug: string }>(
	asked: string,
	items: T[],
	max = 3
): SlugRecovery<T> {
	const none = { forward: null, suggestions: [] };
	const askedKey = slugKey(asked);
	if (!askedKey || items.some((it) => it.slug === asked)) return none;
	const askedWords = slugWords(asked);
	const seen = new Set<string>();
	const scored: { it: T; d: number }[] = [];
	for (const it of items) {
		// One row per slug: a shelf can carry a slug twice (two editions).
		if (seen.has(it.slug)) continue;
		seen.add(it.slug);
		const d = distance(askedKey, askedWords, it.slug);
		if (d !== null) scored.push({ it, d });
	}
	scored.sort((a, b) => a.d - b.d || a.it.slug.localeCompare(b.it.slug));
	const aliases = scored.filter((s) => s.d === 0);
	return {
		forward: aliases.length === 1 ? aliases[0].it : null,
		suggestions: scored.slice(0, max).map((s) => s.it)
	};
}

export interface MissedDetail {
	section: RecoverableSection;
	slug: string;
	/** Rebuild the missed URL around another slug, keeping locale and the rest. */
	withSlug: (slug: string) => string;
}

/**
 * The detail page a not-found path was asking for — `/authors/<slug>/`,
 * `/es/books/<slug>/3/` — or null for any other path.
 */
export function missedDetail(pathname: string): MissedDetail | null {
	const segments = pathname.split('/').filter(Boolean);
	const lang = locales.includes(segments[0] as (typeof locales)[number]) ? segments[0] : '';
	const body = lang ? segments.slice(1) : segments;
	const [section, slug, ...rest] = body;
	if (!slug || !(RECOVERABLE as readonly string[]).includes(section)) return null;
	// A sermon or author has no deeper pages; a book's are its chapters.
	if (rest.length && section !== 'books') return null;
	let decoded: string;
	try {
		decoded = decodeURIComponent(slug);
	} catch {
		return null;
	}
	return {
		section: section as RecoverableSection,
		slug: decoded,
		withSlug: (s) => `/${[lang, section, s, ...rest].filter(Boolean).join('/')}/`
	};
}
