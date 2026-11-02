import { describe, expect, it } from 'vitest';
import { BOOK_ROUTE, shouldFly } from './coverFlight';

/**
 * A tapped cover flies only into the book page its link named, and only where
 * the browser can and the reader is happy to see motion. Everything else is an
 * ordinary navigation.
 */
const to = (routeId: string | null, href: string) =>
	({ to: { route: { id: routeId }, url: new URL(href) } }) as Parameters<typeof shouldFly>[0];
const ok = { canTransition: true, reducedMotion: false };
const tapped = { href: 'https://ochorus.com/es/books/the-pilgrims-progress' };

describe('cover flight', () => {
	it('flies into the book page the tapped link named', () => {
		expect(shouldFly(to(BOOK_ROUTE, 'https://ochorus.com/es/books/the-pilgrims-progress'), tapped, ok)).toBe(true);
		// A hash on either side is the same page.
		expect(shouldFly(to(BOOK_ROUTE, 'https://ochorus.com/es/books/the-pilgrims-progress#contents'), tapped, ok)).toBe(true);
	});

	it('stays put for anything else', () => {
		// No cover was tapped (a text link, the search box, back).
		expect(shouldFly(to(BOOK_ROUTE, tapped.href), null, ok)).toBe(false);
		// A cover linking to a chapter (Continue reading), or another book.
		expect(shouldFly(to('/books/[slug]/[order]', `${tapped.href}/3`), tapped, ok)).toBe(false);
		expect(shouldFly(to(BOOK_ROUTE, 'https://ochorus.com/es/books/holiness'), tapped, ok)).toBe(false);
	});

	it('stays put without View Transitions, or for a reader who asks for less motion', () => {
		const nav = to(BOOK_ROUTE, tapped.href);
		expect(shouldFly(nav, tapped, { canTransition: false, reducedMotion: false })).toBe(false);
		expect(shouldFly(nav, tapped, { canTransition: true, reducedMotion: true })).toBe(false);
	});
});
