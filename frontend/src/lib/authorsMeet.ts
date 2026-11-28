import { ERAS, eraOf, type Era } from './eras';

/**
 * The /authors page's two doors in, above the A–Z: "Meet these first" (a
 * handful of writers and the book to start each with) and the timeline (every
 * pictured writer by the era they lived in). Pure, so it is tested once.
 */

type Person = {
	slug: string;
	name: string;
	photo_url: string;
	birth_year: number | null;
	death_year: number | null;
};
type Book = { slug: string; title: string; author: { slug: string } };

/**
 * Editorial, so a list in code: one voice per stretch of the church's story,
 * and the book a newcomer should open first. Book slugs are shared across
 * languages; where this language lacks the named book, the writer's first book
 * here stands in, and a writer with no book here is left out.
 */
export const MEET_FIRST: { author: string; book: string }[] = [
	{ author: 'augustine-of-hippo', book: 'confessions' },
	{ author: 'thomas-a-kempis', book: 'the-imitation-of-christ' },
	{ author: 'john-bunyan', book: 'pilgrims-progress' },
	{ author: 'brother-lawrence', book: 'the-practice-of-the-presence-of-god' },
	{ author: 'charles-h-spurgeon', book: 'all-of-grace' },
	{ author: 'andrew-murray', book: 'absolute-surrender' },
	{ author: 'amy-carmichael', book: 'if' },
	{ author: 'a-w-tozer', book: 'the-pursuit-of-god' }
];

/** Below this many, the section is a list of a few names: hide it. */
export const MEET_MIN = 4;

export function meetFirst<P extends Person, B extends Book>(
	people: P[],
	books: B[]
): { author: P; book: B }[] {
	const bySlug = new Map(people.map((p) => [p.slug, p]));
	const bookBySlug = new Map(books.map((b) => [b.slug, b]));
	const picks = MEET_FIRST.flatMap(({ author, book }) => {
		const p = bySlug.get(author);
		const b = bookBySlug.get(book) ?? books.find((x) => x.author.slug === author);
		return p && b ? [{ author: p, book: b }] : [];
	});
	return picks.length >= MEET_MIN ? picks : [];
}

/**
 * The timeline: each era with its pictured writers, earliest-born first, up to
 * `per` faces and a count of the rest. Undated writers are left off (a line of
 * dates has no place for them); eras with nobody pictured are dropped.
 */
export function timeline<P extends Person>(
	people: P[],
	per = 8
): { era: Era; faces: P[]; more: number }[] {
	const dated = people
		.filter((p) => p.photo_url && p.birth_year != null)
		.sort((a, b) => a.birth_year! - b.birth_year! || a.name.localeCompare(b.name));
	return ERAS.map((era) => {
		const all = dated.filter((p) => eraOf(p.birth_year) === era.id);
		return { era, faces: all.slice(0, per), more: Math.max(0, all.length - per) };
	}).filter((row) => row.faces.length);
}
