import { expect, test, type Page } from '@playwright/test';

/**
 * The reader's core path, executed in a real browser against the BUILT site and
 * a real API.
 *
 * Scope is deliberately narrow: each test covers something no other gate can
 * see — that the app hydrates and routes on the client, and that a live fetch
 * against the Django API returns usable data. Assertions lean on roles and
 * visible prose rather than CSS classes, so a styling change doesn't fail the
 * suite but a broken API contract does.
 *
 * Known scope limit: the API under test runs on SQLite, so the search test
 * exercises the icontains fallback in library/search.py rather than the Postgres
 * `search_vector` path production uses. It still proves the endpoint, its
 * payload shape and the client rendering — the parts that actually drift.
 */

// A published English book with chapters, present in the seeded fixture.
const BOOK = 'godliness';

/**
 * The reader's sticky bar, and so the line a restored paragraph is parked on.
 * Mirrors `HEADER_OFFSET` in `$lib/reading.ts`, which cannot be imported here:
 * that module pulls in a rune module, and this spec runs outside the Svelte
 * compiler. Keep the two in step — a change there wants a change here.
 */
const HEADER_OFFSET = 64;

/**
 * Count document loads. A client-side (SvelteKit) navigation does NOT load a new
 * document, so a count that is UNCHANGED across a click proves the app hydrated
 * and took over routing — something a plain `<a href>` click would satisfy even
 * with the JS bundle dead.
 *
 * Compared as a delta around the click, never against a literal 1: anything that
 * legitimately reloads before the click (a service worker taking control, say)
 * would otherwise fail the assertion for the wrong reason.
 */
function documentLoads(page: Page): () => number {
	let loads = 0;
	page.on('load', () => loads++);
	return () => loads;
}

/** Give the client bundle a chance to hydrate before interacting. */
async function hydrated(page: Page) {
	await page.waitForLoadState('networkidle');
}

/**
 * Read the scrolling layout rather than page-turn mode.
 *
 * Page-turn is the first-run default at this viewport and has no scroll
 * position at all, so any test that talks about scrolling has to say so. Two
 * tests below learned this the hard way.
 */
async function scrollingLayout(page: Page) {
	await page.addInitScript(() =>
		localStorage.setItem('ochorus:reader-prefs', JSON.stringify({ paged: false }))
	);
}

/**
 * Select the opening of one paragraph of the prose, as a reader dragging over a
 * sentence does, and return exactly what was selected.
 *
 * A real Range rather than a mouse drag: a drag selects whatever sits between
 * two pixel coordinates, which is a different string at a different viewport or
 * font size — and the assertions below quote what was selected back. Setting the
 * selection through the API still fires `selectionchange`, which is what
 * SelectionBar listens for, so the bar appears exactly as it does for a reader.
 */
async function selectWithin(page: Page, paragraph: number, chars = 40): Promise<string> {
	return page.evaluate(
		({ paragraph, chars }) => {
			const el = document.querySelector('.reading')?.children[paragraph];
			if (!el) throw new Error(`no paragraph ${paragraph} in the prose`);
			const node = document.createTreeWalker(el, NodeFilter.SHOW_TEXT).nextNode() as Text | null;
			if (!node) throw new Error(`paragraph ${paragraph} has no text`);
			const end = Math.min(chars, node.data.length);
			const range = document.createRange();
			range.setStart(node, 0);
			range.setEnd(node, end);
			const sel = window.getSelection();
			sel?.removeAllRanges();
			sel?.addRange(range);
			return node.data.slice(0, end);
		},
		{ paragraph, chars }
	);
}

test('home page hydrates and routes on the client', async ({ page }) => {
	const loads = documentLoads(page);
	await page.goto('/');
	await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
	await hydrated(page);

	const before = loads();
	await page.getByRole('link', { name: /^books$/i }).first().click();
	await expect(page).toHaveURL(/\/books\/?$/);
	// No new document → SvelteKit handled the navigation, so JS is alive.
	expect(loads()).toBe(before);
});

test('the library shelf lists books from the API', async ({ page }) => {
	await page.goto('/books/');
	// The seeded library has dozens of English books; assert plurality, not an
	// exact count, so adding content never breaks this.
	const bookLinks = page.locator('a[href*="/books/"]');
	await expect.poll(() => bookLinks.count(), { timeout: 15_000 }).toBeGreaterThan(5);
});

test('a chapter opens by client-side navigation and renders its prose', async ({ page }) => {
	const loads = documentLoads(page);
	await page.goto(`/books/${BOOK}/`);
	await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
	await hydrated(page);

	// Into the reader the way a reader gets there: clicking a chapter.
	const before = loads();
	await page.locator(`a[href^="/books/${BOOK}/"]`).first().click();
	await expect(page).toHaveURL(new RegExp(`/books/${BOOK}/\\d+/?$`));
	expect(loads()).toBe(before);

	const prose = page.locator('.reading');
	await expect(prose).toBeVisible();
	// Real chapter text, not an empty shell or an error page.
	expect((await prose.innerText()).length).toBeGreaterThan(200);
});

test('search returns live results from the API', async ({ page }) => {
	// Driven by ?q= rather than typing: the query runs on load, so the assertion
	// can't race the input debounce or a hydration-time reset of the bound value.
	// What matters here is the live API round-trip, not the keystroke handling.
	await page.goto('/search/?q=prayer');
	const results = page.locator('a[href*="/books/"], a[href*="/sermons/"]');
	await expect.poll(() => results.count(), { timeout: 20_000 }).toBeGreaterThan(0);
});

test('a resume point records the paragraph the reader is actually on', async ({ page }) => {
	// An off-by-one, and invisible to every other gate: it needs a real browser
	// laying out real text.
	//
	// The save asked "first paragraph whose TOP has passed the header line, minus
	// one" while the restore parks a paragraph exactly ON that line — so the two
	// halves of one contract disagreed by one, and the resume point recorded a
	// paragraph the reader had already scrolled past.
	await page.addInitScript(() =>
		// Page-turn mode is the first-run default on a wide viewport and has no
		// scroll position at all; this is the scrolling layout's contract.
		localStorage.setItem('ochorus:reader-prefs', JSON.stringify({ paged: false }))
	);
	await page.goto(`/books/${BOOK}/1/`);
	await hydrated(page);

	// Park paragraph 12 on the header line — where a restore leaves it, and where
	// a reader who has just read paragraph 11 ends up.
	await page.evaluate((offset) => {
		const el = document.querySelector('.reading')?.children[12];
		el?.scrollIntoView({ block: 'start' });
		window.scrollBy(0, -offset);
	}, HEADER_OFFSET);

	await expect
		.poll(
			() =>
				page.evaluate(
					(book) => JSON.parse(localStorage.getItem('ochorus:anchors') ?? '{}')[`${book}:1`],
					BOOK
				),
			{ timeout: 15_000 }
		)
		.toBe(12);
});

test('a deep link lands on its paragraph even when the fonts arrive late', async ({ page }) => {
	// `await tick()` waits for Svelte to write the DOM, not for the browser to
	// finish laying it out — and this is a reading app whose prose faces load
	// after first paint. Measured with the faces delayed: the document grew
	// 6,010px to 6,673px on the following frame, carrying the target paragraph
	// 209px down, so the reader landed 35px low and the save recorded N-1.
	//
	// The delay is the point of the test. On a warm cache the restore and the
	// fonts race and the bug hides; on the connections this library is read over
	// it does not.
	await page.route(/\.(woff2?|ttf|otf)$/i, async (route) => {
		await new Promise((r) => setTimeout(r, 900));
		await route.continue();
	});
	await page.addInitScript(() =>
		localStorage.setItem('ochorus:reader-prefs', JSON.stringify({ paged: false }))
	);

	await page.goto(`/books/${BOOK}/1/?p=8`);
	await hydrated(page);

	// Recorded where it was asked to go...
	await expect
		.poll(
			() =>
				page.evaluate(
					(book) => JSON.parse(localStorage.getItem('ochorus:anchors') ?? '{}')[`${book}:1`],
					BOOK
				),
			{ timeout: 20_000 }
		)
		.toBe(8);

	// ...and actually put it there, once the reflow had happened.
	//
	// The distance FROM the line, so the bound is two-sided: a one-sided "not far
	// below it" would also accept a restore that overshot and left the paragraph
	// above the fold. 12px is loose enough for rendering differences between
	// machines and a third of the 35px the unfixed restore misses by — measured
	// at 0px here at CPU throttling up to 20x.
	await expect
		.poll(
			() =>
				page.evaluate((offset) => {
					const top = document.querySelector('.reading')?.children[8]?.getBoundingClientRect().top;
					return top === undefined ? Number.POSITIVE_INFINITY : Math.abs(top - offset);
				}, HEADER_OFFSET),
			{ timeout: 20_000 }
		)
		.toBeLessThanOrEqual(12);
});

test('a highlight survives a reload and turns up in the notebook', async ({ page }) => {
	// The app's signature feature, and the longest thing it does: a DOM text
	// selection becomes character offsets in a paragraph, is written to
	// localStorage, is re-rendered over freshly fetched prose on the next visit,
	// and is quoted back on a different page that has to re-derive the text from
	// those offsets. Every step of that is invisible to the unit tests, which see
	// the store but never a Selection or a re-render.
	await scrollingLayout(page);
	await page.goto(`/books/${BOOK}/1/`);
	await hydrated(page);

	const quoted = await selectWithin(page, 3);
	expect(quoted.length, 'precondition: there is prose to select').toBeGreaterThan(10);

	const bar = page.getByRole('toolbar');
	await expect(bar).toBeVisible();
	await bar.locator('.hl-swatch').first().click();

	// It is in the prose, and it is the text that was selected — not merely SOME
	// mark somewhere, which would pass with the offsets off by any amount.
	const mark = page.locator('.reading mark').first();
	await expect(mark).toBeVisible();
	expect(quoted).toContain((await mark.innerText()).trim().slice(0, 20));

	// It survives the round trip through storage and a fresh render.
	await page.reload();
	await hydrated(page);
	await expect(page.locator('.reading mark').first()).toBeVisible();

	// And the notebook can rebuild the quotation from the stored offsets alone —
	// it re-fetches the chapter and slices it, so a drift between what was saved
	// and how the prose is split shows up here and nowhere else.
	await page.goto('/notebook/');
	await hydrated(page);
	const entry = page.locator(`a[href*="/books/${BOOK}/1"]`).first();
	await expect(entry).toBeVisible({ timeout: 20_000 });
	expect(await entry.getAttribute('href')).toMatch(/\?p=3$/);
	expect(quoted).toContain((await entry.innerText()).replace(/[“”]/g, '').trim().slice(0, 20));
});

test('switching language from the footer serves that language', async ({ page }) => {
	// Locale lives in the URL prefix, the content is per-language rows with NO
	// English fallback, and the whole site is prerendered — so "switch language"
	// means a different set of built pages, not a runtime toggle. Nothing else in
	// CI clicks that path end to end.
	await page.goto('/');
	await hydrated(page);

	// By its autonym, which is what the strip renders: a reader who needs this
	// control cannot read "Spanish".
	const spanish = page.getByRole('link', { name: 'Español' });
	await expect(spanish).toBeVisible();
	await spanish.click();

	await expect(page).toHaveURL(/\/es(\/|$)/);
	// The document must actually declare the locale — this is what a screen
	// reader and a search engine act on, and it is set from the URL prefix.
	await expect.poll(() => page.evaluate(() => document.documentElement.lang)).toBe('es');

	// And the chrome is translated, so this is a real locale and not just a prefix.
	await expect(page.getByRole('link', { name: /^libros$/i }).first()).toBeVisible();
});

test('a sermon opens from the list and renders its prose', async ({ page }) => {
	// The second reading surface. It shares Reader with the chapter page but
	// renders its own shell, its own data fetch and its own SEO — and until now
	// no browser test opened one at all.
	await page.goto('/sermons/');
	await hydrated(page);

	const first = page.locator('a[href*="/sermons/"]').filter({ hasNotText: /^$/ }).nth(1);
	await expect(first).toBeVisible();
	const href = await first.getAttribute('href');
	await first.click();

	await expect(page).toHaveURL(new RegExp(href!.replace(/\/$/, '')));
	await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

	// Real prose, not an empty shell: a sermon that fetched nothing still renders
	// its header, so assert on the body the page exists to show.
	//
	// Polled, not measured once. The prose arrives after the heading does, and a
	// single `evaluate` here reads an empty `.reading` on a slow machine and
	// reports one word — which is a flaky test rather than a found bug. (Seen:
	// probing straight after `networkidle` returned 1.)
	await expect
		.poll(
			() =>
				page.evaluate(
					() => (document.querySelector('.reading')?.textContent ?? '').trim().split(/\s+/).length
				),
			{ timeout: 20_000 }
		)
		.toBeGreaterThan(200);
});

test('a biography opens from the list and renders its prose', async ({ page }) => {
	// The third reading surface, and the odd one out: the prose is one band in a
	// much wider page, with its own header offset and no sticky bar. It is the
	// surface most likely to drift, and it had no browser coverage either.
	await page.goto('/authors/');
	await hydrated(page);

	const first = page.locator('a[href*="/authors/"]').nth(1);
	await expect(first).toBeVisible();
	await first.click();

	await expect(page).toHaveURL(/\/authors\/[^/]+\/?$/);
	await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
	await expect(page.locator('.reading')).toBeVisible({ timeout: 20_000 });
});

test('turning to the next chapter stays in the same book and moves the prose', async ({ page }) => {
	// Chapter-to-chapter is the motion a reader makes most, and it crosses two
	// prerendered routes on the client. A broken link here strands a reader mid
	// book with every unit test green.
	await scrollingLayout(page);
	await page.goto(`/books/${BOOK}/1/`);
	await hydrated(page);
	const firstOpening = (await page.locator('.reading').innerText()).slice(0, 120);

	const loads = documentLoads(page);
	const before = loads();
	await page.getByRole('link', { name: /next/i }).first().click();

	await expect(page).toHaveURL(new RegExp(`/books/${BOOK}/2/?`));
	expect(loads() - before, 'the turn should be a client-side navigation').toBe(0);

	// Different prose, not just a different URL — a route that renders the
	// previous chapter's body would satisfy the URL assertion on its own.
	await expect
		.poll(async () => (await page.locator('.reading').innerText()).slice(0, 120))
		.not.toBe(firstOpening);
});

test('an unknown slug is served the SPA fallback and renders not-found', async ({ page }) => {
	const res = await page.goto('/books/this-book-does-not-exist/');
	// adapter-static answers unknown paths with 200.html, so the status is 200 and
	// the app renders its own not-found UI. A 404 here would mean the fallback is
	// missing; a blank page would mean the shell failed to boot.
	expect(res?.status()).toBe(200);
	await expect(page.getByRole('heading', { name: /not found/i })).toBeVisible();
});

test("a book's share card is built and served as an image", async ({ page, request }) => {
	// The landscape card is not committed — `postbuild` composes it into the
	// build (scripts/build-share-cards.mjs). This is the check that the step ran
	// and that the page points at what it wrote. Content type, not status: an
	// unknown path is answered 200 with the SPA fallback, so a missing card
	// would pass a status check as an HTML page.
	await page.goto(`/books/${BOOK}/`);
	const og = await page.locator('meta[property="og:image"]').getAttribute('content');
	expect(og, 'the book page names no og:image').toBeTruthy();
	const path = new URL(og!).pathname;
	expect(path).toBe(`/og/covers/en/${BOOK}.jpg`);
	const res = await request.get(path);
	expect(res.status()).toBe(200);
	expect(res.headers()['content-type']).toContain('image/jpeg');
});
