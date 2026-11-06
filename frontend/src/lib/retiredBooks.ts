/**
 * Books retired as duplicates of another work, and where their URLs go now.
 *
 * Mirrors `corrections.RETIRED_BOOKS` in the backend (kept in step by
 * `tests_fixture.RetiredBookTests`): every edition stays in the database,
 * unpublished, so readers' saved places keep a row to resolve to, and the book
 * and chapter pages forward an old link to the same text in the successor.
 * `offset` maps a retired chapter's order onto the successor's. The English
 * book URL also has a 301 in render.yaml; chapter URLs and the localized forms
 * are forwarded here, by the pages' own loads.
 */
export const RETIRED_BOOKS: Record<string, { to: string; offset: number }> = {
	// Lessons 1-4 of With Christ in the School of Prayer (its chapter 1 is the
	// Preface), retired 2026-11 as a modernized paraphrase of Murray's text.
	'lord-teach-us-to-pray-2': { to: 'school-of-prayer', offset: 1 }
};

/** The successor's book page, or its chapter for `order`, for a retired slug;
 * null when the slug is not retired. Paths are unlocalized and unslashed, like
 * `bookChapterPath`'s; pass them through `localizeHref`. */
export function retiredBookPath(slug: string, order?: number, modern = false): string | null {
	const r = Object.hasOwn(RETIRED_BOOKS, slug) ? RETIRED_BOOKS[slug] : undefined;
	if (!r) return null;
	if (order === undefined || !Number.isInteger(order)) return `/books/${r.to}/`;
	return `/books/${r.to}/${modern ? 'modern/' : ''}${order + r.offset}`;
}
