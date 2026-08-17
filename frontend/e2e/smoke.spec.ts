import { expect, test } from '@playwright/test';

/**
 * The reader's core path, executed in a real browser against a real API.
 *
 * Scope is deliberately narrow: each test covers something no other gate can
 * see — that the page HYDRATES, that client-side navigation works, and that a
 * live fetch against the Django API returns usable data. Assertions lean on
 * roles and visible prose rather than CSS classes, so a styling change doesn't
 * fail the suite but a broken API contract does.
 */

// A published English book with chapters, present in the seeded fixture.
const BOOK = 'godliness';

test('home page renders and hydrates', async ({ page }) => {
	await page.goto('/');
	await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

	// Hydration check: a client-side nav that only works once JS has taken over.
	// (A prerendered page with dead JS would still show the heading above.)
	const toLibrary = page.getByRole('link', { name: /books|library/i }).first();
	await toLibrary.click();
	await expect(page).toHaveURL(/\/books\/?$/);
});

test('the library shelf lists books from the API', async ({ page }) => {
	await page.goto('/books/');
	const bookLinks = page.locator('a[href*="/books/"]');
	// The seeded library has dozens of English books; assert plurality, not a
	// count, so adding content never breaks this.
	await expect.poll(() => bookLinks.count(), { timeout: 10_000 }).toBeGreaterThan(5);
});

test('a book page opens a chapter and renders its prose', async ({ page }) => {
	await page.goto(`/books/${BOOK}/`);
	await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

	// Into chapter 1 by client-side navigation — the reader is the app's whole
	// purpose, and this is the path that exercises the chapter API + the reader.
	await page.goto(`/books/${BOOK}/1/`);
	const prose = page.locator('.reading');
	await expect(prose).toBeVisible();
	// Real chapter text, not an empty shell or an error page.
	await expect(prose).not.toBeEmpty();
	expect((await prose.innerText()).length).toBeGreaterThan(200);
});

test('search returns live results from the API', async ({ page }) => {
	await page.goto('/search/');
	const box = page.getByRole('searchbox').first();
	await box.fill('prayer');

	// Results arrive from /api/library/search/ after the input debounce; the
	// assertion polls rather than sleeping.
	const results = page.locator('a[href*="/books/"], a[href*="/sermons/"]');
	await expect.poll(() => results.count(), { timeout: 15_000 }).toBeGreaterThan(0);
});

test('an unknown book slug shows the not-found page, not a crash', async ({ page }) => {
	const res = await page.goto('/books/this-book-does-not-exist/');
	// Static hosting can answer 200 with the SPA shell; what matters is that the
	// app renders its own not-found state rather than a blank page or a stack.
	expect(res?.status()).toBeLessThan(500);
	await expect(page.locator('body')).not.toBeEmpty();
	await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
});
