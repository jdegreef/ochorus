import { describe, expect, it } from 'vitest';
import { loginHref } from './loginHref';

const redirectOf = (href: string) =>
	new URLSearchParams(href.split('?')[1] ?? '').get('redirect');

describe('loginHref', () => {
	it('carries the current page as the redirect target', () => {
		expect(redirectOf(loginHref('/books/humility/3/'))).toBe('/books/humility/3/');
	});

	it('offers no self-redirect when already on the login page', () => {
		expect(loginHref('/login')).toBe('/login');
	});

	it('recognises the login page in every locale, not just English', () => {
		// The bug: `/es/login` did not start with '/login', so the link became
		// `?redirect=/es/login` and sign-in landed back on the login page.
		for (const locale of ['es', 'pt', 'sw', 'lg']) {
			expect(loginHref(`/${locale}/login`)).toBe('/login');
		}
	});

	it('keeps the locale prefix in the redirect for a normal page', () => {
		// De-localizing is only how the shape is judged — a Spanish reader must
		// come back to the Spanish page, not its English twin.
		expect(redirectOf(loginHref('/es/books/humility/'))).toBe('/es/books/humility/');
	});

	it('preserves the query string', () => {
		expect(redirectOf(loginHref('/search', '?q=grace'))).toBe('/search?q=grace');
		expect(redirectOf(loginHref('/es/search', '?q=gracia'))).toBe('/es/search?q=gracia');
	});
});
