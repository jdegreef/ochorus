import type { OnNavigate } from '@sveltejs/kit';

/**
 * The cover a reader taps flies into the book page it opens: the shelf's
 * cover and the book page's hero cover share a view-transition name for that
 * one navigation, so the browser carries the one into the place of the other
 * (app.css, `book-cover`) while the rest of the page crossfades.
 *
 * Every shelf draws covers its own way (BookCard, ShelfBook, CoverStrip, the
 * home hero…), so nothing is threaded through them: a capture-phase click on
 * the document notes the cover inside the link that was tapped, and the
 * layout's onNavigate flies it when — and only when — that link's book page is
 * where the navigation lands. Anything else (a chapter link, a modified click,
 * another page) is an ordinary navigation, as it is wherever the browser has
 * no View Transitions or the reader asks for less motion.
 */

/** The book page's route, whose hero cover (`[data-cover-landing]`) is the landing. */
export const BOOK_ROUTE = '/books/[slug]';
/** The shared name; the hero carries it in its CSS, the tapped cover inline. */
export const COVER_NAME = 'book-cover';
/** The cover's drawn box (BookCover's root). */
const COVER = '.cover-edge';

let tapped: { el: HTMLElement; href: string } | null = null;

/** Capture-phase document click: remember a cover inside the link tapped. */
export function noteCoverTap(e: MouseEvent): void {
	const link = e.target instanceof Element ? e.target.closest<HTMLAnchorElement>('a[href]') : null;
	const cover = link?.querySelector<HTMLElement>(COVER);
	tapped = link && cover ? { el: cover, href: link.href } : null;
}

/** Whether a navigation should fly the tapped cover: it lands on the book
 *  page that the tapped link named, and the browser and reader allow it. */
export function shouldFly(
	nav: Pick<OnNavigate, 'to'>,
	from: { href: string } | null,
	env: { canTransition: boolean; reducedMotion: boolean }
): boolean {
	return (
		!!from &&
		env.canTransition &&
		!env.reducedMotion &&
		nav.to?.route.id === BOOK_ROUTE &&
		stripHash(nav.to.url.href) === stripHash(from.href)
	);
}

const stripHash = (href: string) => href.split('#')[0];

/** The layout's onNavigate: fly the tapped cover into the book page, or
 *  return nothing and let the navigation happen as usual. */
export function flyCover(nav: OnNavigate): Promise<void> | void {
	const from = tapped;
	tapped = null;
	const doc = document;
	const ok = shouldFly(nav, from, {
		canTransition: typeof doc.startViewTransition === 'function' && doc.visibilityState === 'visible',
		reducedMotion: !!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches
	});
	if (!ok || !from) return;

	// Names must be unique in each snapshot. Leaving one book page for another
	// (its "read next" covers), the old hero also carries the name: let the
	// tapped cover hold it alone in the old snapshot, then hand it back.
	const heroes = [...doc.querySelectorAll<HTMLElement>('[data-cover-landing]')];
	heroes.forEach((h) => (h.style.viewTransitionName = 'none'));
	from.el.style.viewTransitionName = COVER_NAME;

	// The new snapshot: only the new hero (CSS) carries the name. Also on the
	// way out of a transition that was skipped or threw, so nothing keeps it.
	const handBack = () => {
		from.el.style.viewTransitionName = '';
		heroes.forEach((h) => (h.style.viewTransitionName = ''));
	};
	return new Promise<void>((resolve) => {
		const t = doc.startViewTransition(async () => {
			resolve();
			await nav.complete;
			handBack();
		});
		t.finished.then(handBack, handBack);
	});
}
