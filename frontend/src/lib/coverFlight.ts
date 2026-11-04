import type { OnNavigate } from '@sveltejs/kit';
import { canViewTransition } from './crossfade';
import { isPlainPrimaryClick } from './plainClick';

/**
 * The cover a reader taps flies into the book page it opens: for that one
 * navigation the shelf's cover and the book page's hero cover share a
 * view-transition name, so the browser carries the one into the place of the
 * other (app.css, `book-cover`) while the rest of the page crossfades.
 *
 * Every shelf draws covers its own way (BookCard, ShelfBook, CoverStrip, the
 * home hero…), so nothing is threaded through them: a capture-phase click on
 * the document notes the cover inside the link that was tapped, and the
 * layout's onNavigate flies it when — and only when — that link's book page is
 * where the navigation lands. Anything else (a chapter link, a modified click,
 * another page) is an ordinary navigation, as it is wherever the browser has
 * no View Transitions or the reader asks for less motion.
 *
 * The name is only ever on what is in flight (so it stays unique on a
 * book-to-book jump, and a theme crossfade never lifts the hero): the tapped
 * cover for the old snapshot, the landing (`[data-cover-landing]`) for the new.
 * Covers on a book page's edition ladder fly into its hero the same way.
 */

/** The book page's route, whose hero cover is the landing. */
export const BOOK_ROUTE = '/books/[slug]';
/** The shared name (app.css times its group). */
export const COVER_NAME = 'book-cover';
/** The cover's drawn box (BookCover's root). */
const COVER = '.cover-edge';
const LANDING = '[data-cover-landing]';
/** How long the new snapshot waits for the hero's image to be ready. */
const DECODE_WAIT_MS = 150;

let tapped: { el: HTMLElement; href: string } | null = null;

/** Capture-phase document click: remember a cover inside the link tapped —
 *  a plain primary-button tap only (a modified click opens a tab instead). */
export function noteCoverTap(e: MouseEvent): void {
	tapped = null;
	if (!isPlainPrimaryClick(e)) return;
	const link = e.target instanceof Element ? e.target.closest<HTMLAnchorElement>('a[href]') : null;
	const cover = link?.querySelector<HTMLElement>(COVER);
	if (link && cover && !link.target) tapped = { el: cover, href: link.href };
}

/** Whether a navigation should fly the tapped cover: a link was followed
 *  (SvelteKit's word for it), and it lands on the book page that link named. */
export function shouldFly(nav: Pick<OnNavigate, 'to' | 'type'>, from: { href: string } | null): boolean {
	return (
		!!from &&
		nav.type === 'link' &&
		nav.to?.route.id === BOOK_ROUTE &&
		stripHash(nav.to.url.href) === stripHash(from.href)
	);
}

const stripHash = (href: string) => href.split('#')[0];

/** Resolve once `img` can paint, or after DECODE_WAIT_MS — whichever is first. */
function ready(img: HTMLImageElement | null): Promise<void> {
	if (!img || img.complete) return Promise.resolve();
	return Promise.race([img.decode().catch(() => {}), new Promise<void>((r) => setTimeout(r, DECODE_WAIT_MS))]);
}

/** The layout's onNavigate: fly the tapped cover into the book page, or
 *  return nothing and let the navigation happen as usual. */
export function flyCover(nav: OnNavigate): Promise<void> | void {
	const from = tapped;
	tapped = null;
	if (!from || !shouldFly(nav, from) || !canViewTransition()) return;

	from.el.style.viewTransitionName = COVER_NAME;
	let landing: HTMLElement | null = null;
	const clear = () => {
		from.el.style.viewTransitionName = '';
		if (landing) landing.style.viewTransitionName = '';
	};

	return new Promise<void>((resolve) => {
		const t = document.startViewTransition(async () => {
			resolve();
			from.el.style.viewTransitionName = '';
			try {
				await nav.complete;
			} catch {
				return; // superseded or failed: the page settles without a flight
			}
			landing = document.querySelector<HTMLElement>(LANDING);
			if (!landing) return;
			landing.style.viewTransitionName = COVER_NAME;
			await ready(landing.querySelector('img'));
		});
		t.finished.then(clear, clear);
	});
}
