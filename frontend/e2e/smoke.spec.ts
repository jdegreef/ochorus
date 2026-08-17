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

test('an unknown slug is served the SPA fallback and renders not-found', async ({ page }) => {
	const res = await page.goto('/books/this-book-does-not-exist/');
	// adapter-static answers unknown paths with 200.html, so the status is 200 and
	// the app renders its own not-found UI. A 404 here would mean the fallback is
	// missing; a blank page would mean the shell failed to boot.
	expect(res?.status()).toBe(200);
	await expect(page.getByRole('heading', { name: /not found/i })).toBeVisible();
});
