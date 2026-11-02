import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { OnNavigate } from '@sveltejs/kit';
import { BOOK_ROUTE, COVER_NAME, flyCover, noteCoverTap, shouldFly } from './coverFlight';

/**
 * A tapped cover flies only into the book page its link named, and the shared
 * view-transition name is only ever on the elements in flight: the tapped
 * cover for the old snapshot, the landing for the new one, and nothing after.
 */
const nav = (routeId: string | null, href: string, complete: Promise<void> = Promise.resolve(), type = 'link') =>
	({ type, to: { route: { id: routeId }, url: new URL(href) }, complete }) as unknown as OnNavigate;
const BOOK = 'http://localhost:3000/es/books/the-pilgrims-progress';

describe('when a cover flies', () => {
	const tapped = { href: BOOK };
	it('flies into the book page the tapped link named (a hash is the same page)', () => {
		expect(shouldFly(nav(BOOK_ROUTE, BOOK), tapped)).toBe(true);
		expect(shouldFly(nav(BOOK_ROUTE, `${BOOK}#contents`), tapped)).toBe(true);
	});
	it('stays put for anything else', () => {
		expect(shouldFly(nav(BOOK_ROUTE, BOOK), null)).toBe(false);
		expect(shouldFly(nav('/books/[slug]/[order]', `${BOOK}/3`), tapped)).toBe(false);
		expect(shouldFly(nav(BOOK_ROUTE, 'http://localhost:3000/es/books/holiness'), tapped)).toBe(false);
		// Not the link being followed: a goto(), back/forward.
		expect(shouldFly(nav(BOOK_ROUTE, BOOK, undefined, 'goto'), tapped)).toBe(false);
		expect(shouldFly(nav(BOOK_ROUTE, BOOK, undefined, 'popstate'), tapped)).toBe(false);
	});
	it('names the group app.css times', () => {
		const css = readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8');
		expect(css).toContain(`::view-transition-group(${COVER_NAME})`);
	});
});

describe('the name handoff', () => {
	let cover: HTMLElement;
	let snapshots: string[][];
	const named = () => [...document.querySelectorAll<HTMLElement>('*')].filter((e) => e.style.viewTransitionName === COVER_NAME).map((e) => e.id);

	beforeEach(() => {
		document.body.innerHTML = `<a id="link" href="${BOOK}"><div id="shelf-cover" class="cover-edge"></div></a>`;
		cover = document.getElementById('shelf-cover')!;
		snapshots = [];
		Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
		// A stand-in for the browser: record who carries the name before and after the update.
		document.startViewTransition = ((update: () => Promise<void>) => {
			snapshots.push(named());
			const updateCallbackDone = Promise.resolve().then(update);
			const finished = updateCallbackDone.then(() => snapshots.push(named()));
			return { updateCallbackDone, finished, ready: finished, skipTransition() {} };
		}) as unknown as typeof document.startViewTransition;
	});
	afterEach(() => {
		// @ts-expect-error — the test's stand-in only
		delete document.startViewTransition;
	});

	const tap = (init: MouseEventInit = {}) => {
		const e = new MouseEvent('click', { bubbles: true, button: 0, ...init });
		Object.defineProperty(e, 'target', { value: cover });
		noteCoverTap(e);
	};

	it('moves the name from the tapped cover to the landing, then takes it off both', async () => {
		tap();
		const landed = Promise.resolve().then(() => {
			document.body.innerHTML = '<div id="hero" data-cover-landing></div>';
		});
		await flyCover(nav(BOOK_ROUTE, BOOK, landed));
		await vi.waitFor(() => expect(snapshots).toHaveLength(2));
		expect(snapshots).toEqual([['shelf-cover'], ['hero']]);
		expect(named()).toEqual([]);
		expect(cover.style.viewTransitionName).toBe('');
	});

	it('flies nothing for a modified click (a new tab)', () => {
		tap({ metaKey: true });
		expect(flyCover(nav(BOOK_ROUTE, BOOK))).toBeUndefined();
		expect(snapshots).toEqual([]);
	});

	it('leaves no name behind when the navigation fails', async () => {
		tap();
		const failed = Promise.reject(new Error('superseded'));
		failed.catch(() => {});
		await flyCover(nav(BOOK_ROUTE, BOOK, failed));
		await vi.waitFor(() => expect(snapshots).toHaveLength(2));
		expect(named()).toEqual([]);
	});
});
