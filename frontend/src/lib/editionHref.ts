import { lang } from './lang.svelte';
import { localizeHref } from './href';
import { MODERN_EDITION, baseEdition } from './reading-schema';
import { authorPath } from './originals';
import { readerPrefs } from './readerPrefs.svelte';
import type { EntrySource } from './journal';
import type { PlanDay } from './library-public';
import type { WorkKind } from './reading-schema';

/** The locale union `localizeHref` accepts; `lang.isAvailable` is its runtime check. */
type UiLocale = NonNullable<Parameters<typeof localizeHref>[1]>['locale'];

/**
 * A link into the EDITION a highlight or note was made in, not the page's.
 *
 * Without this the Notebook sends the reader to a text their mark is not in —
 * the modern edition needs its query flag, and a mark made in another language
 * belongs to that language's pages. An edition whose language the UI does not
 * carry falls back to the current locale rather than building a URL for a
 * locale that does not route.
 */
export function editionHref(path: string, edition: string): string {
	const modern = edition === MODERN_EDITION;
	const withEdition = modern ? `${path}${path.includes('?') ? '&' : '?'}edition=modern` : path;
	const locale = modern ? 'en' : baseEdition(edition);
	// `isAvailable` IS the check the type wants; a content language can be
	// added in the admin without a frontend deploy, so the set of editions is
	// wider than the compiled locales and this cannot be proven statically.
	return lang.isAvailable(locale)
		? localizeHref(withEdition, { locale: locale as UiLocale })
		: localizeHref(withEdition);
}

/**
 * The page a work of any kind lives on (unlocalized). `order` is a book's
 * chapter; the single-document kinds ignore it. A Record, not a ternary
 * chain: a new kind is a compile error here rather than a link that quietly
 * falls through to another kind's route.
 */
export function workPath(kind: WorkKind, slug: string, order?: number): string {
	const path: Record<WorkKind, string> = {
		book: order ? `/books/${slug}/${order}` : `/books/${slug}`,
		sermon: `/sermons/${slug}`,
		bio: authorPath(slug),
		article: `/articles/${slug}/`
	};
	return path[kind];
}

/** Where a Notebook entry's source passage lives — built from its parts only. */
export function sourceHref(s: EntrySource): string {
	return editionHref(`${workPath(s.kind, s.slug, s.order)}?p=${s.p}`, s.edition);
}

/**
 * A book chapter's path (unlocalized) that honours "Prefer Modern English":
 * when the preference is on and the work HAS a Modern English edition, the link
 * opens that edition. Every way into a chapter — the book page's contents, the
 * resume cards, the Bookshelf, plan days — goes through this, so the choice
 * isn't kept by one button and dropped by the rest. `hasModern` must come from
 * the data: asked for a modern edition that doesn't exist, the reader shows the
 * original under a Modern label. `query` is extra params, without the `?`.
 */
export function chapterPath(
	slug: string,
	order: number,
	hasModern: boolean | undefined,
	query = '',
	/** Open the Modern edition whatever the preference — carrying on in it. */
	stayModern = false
): string {
	const params = new URLSearchParams(query);
	if (hasModern && (stayModern || readerPrefs.preferModern)) params.set('edition', 'modern');
	const q = params.toString();
	return `${workPath('book', slug, order)}${q ? `?${q}` : ''}`;
}

/**
 * A plan day's path (unlocalized), carrying the plan context (`?plan=&day=`)
 * its reading surface needs to mark the day done and move on. A day reads a
 * book chapter (through `chapterPath`, so "Prefer Modern English" holds) or an
 * article; every link into a plan day goes through here, so no entry point
 * handles one kind and drops the other.
 */
export function planDayPath(
	planSlug: string,
	d: Pick<PlanDay, 'day' | 'book_slug' | 'chapter_order' | 'article_slug' | 'has_modern_edition'>,
	/** Open a chapter's Modern edition whatever the preference — carrying on in it. */
	stayModern = false
): string {
	const query = `plan=${encodeURIComponent(planSlug)}&day=${d.day}`;
	if (d.article_slug) return `${workPath('article', d.article_slug)}?${query}`;
	return chapterPath(d.book_slug, d.chapter_order ?? 1, d.has_modern_edition, query, stayModern);
}

