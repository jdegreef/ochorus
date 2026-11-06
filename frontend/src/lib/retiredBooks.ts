import { bookChapterPath } from './reading-schema';

/**
 * Books retired as duplicates of another work, and where their URLs go now.
 *
 * Mirrors `corrections.RETIRED_BOOKS` in the backend (kept in step by
 * `tests_fixture.RetiredBookTests`): every edition stays in the database,
 * unpublished, so readers' saved places keep a row to resolve to, and the book
 * and chapter pages forward an old link to the same text in the successor.
 * `offset` maps a retired chapter's order onto the successor's; `chapters` is
 * how many the retired book had (orders 1..chapters), so only a chapter that
 * existed is forwarded and any other order still 404s. The English book URL
 * also has a 301 in render.yaml; chapter URLs and the localized forms are
 * forwarded here, by the pages' own loads.
 */
export const RETIRED_BOOKS: Record<string, { to: string; offset: number; chapters: number }> = {
	// Lessons 1-4 of With Christ in the School of Prayer (its chapter 1 is the
	// Preface), retired 2026-11 as a modernized paraphrase of Murray's text.
	'lord-teach-us-to-pray-2': { to: 'school-of-prayer', offset: 1, chapters: 4 }
};

/** The successor's book page (no `order`), or its chapter for a retired
 * chapter's `order`; null when the slug is not retired or the order is not one
 * of its chapters. Always the successor's ORIGINAL edition, for a modern URL
 * too: a successor need not have a Modern English edition (school-of-prayer
 * has none), and forwarding to one it lacks would only bounce again. Paths are
 * unlocalized and unslashed, like `bookChapterPath`'s; pass them through
 * `localizeHref`. */
export function retiredBookPath(slug: string, order?: number): string | null {
	const r = Object.hasOwn(RETIRED_BOOKS, slug) ? RETIRED_BOOKS[slug] : undefined;
	if (!r) return null;
	if (order === undefined) return `/books/${r.to}/`;
	if (!Number.isInteger(order) || order < 1 || order > r.chapters) return null;
	return bookChapterPath(r.to, order + r.offset, false);
}

/** `retiredBookPath` for a chapter URL, carrying its query (`search`, e.g.
 * `url.search`; pass '' at build time) minus `?p=` — a paragraph index into
 * the retired text, not the successor's — and `?edition=`, which would only
 * bounce off a successor with no Modern edition. Plan context (`?plan=&day=`)
 * survives. Null as `retiredBookPath`. */
export function retiredChapterHref(slug: string, order: number, search: string): string | null {
	const path = retiredBookPath(slug, order);
	if (!path) return null;
	const qs = new URLSearchParams(search);
	qs.delete('p');
	qs.delete('edition');
	const q = qs.toString();
	return q ? `${path}?${q}` : path;
}
