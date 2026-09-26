import { describe, expect, it } from 'vitest';
import { accountHref, ACCOUNT_NAV } from './accountNav';
import { withSignup } from './loginHref';

const params = (href: string) => new URLSearchParams(href.split('?')[1] ?? '');

describe('accountHref', () => {
	it('goes straight to the page when signed in', () => {
		expect(accountHref('/notebook', true, true)).toBe('/notebook');
	});

	it('routes a signed-out reader through /login with a redirect back', () => {
		const href = accountHref('/settings', false);
		expect(href.startsWith('/login')).toBe(true);
		expect(params(href).get('redirect')).toBe('/settings');
		expect(params(href).get('mode')).toBeNull();
	});

	it('opens the sign-up form for the pages that pitch an account', () => {
		const href = accountHref('/favorites', false, true);
		expect(params(href).get('redirect')).toBe('/favorites');
		expect(params(href).get('mode')).toBe('signup');
	});

	it('lists the reader pages in footer order', () => {
		expect(ACCOUNT_NAV.map((d) => d.path)).toEqual(['/favorites', '/notebook', '/settings']);
	});
});

describe('withSignup', () => {
	it('joins with ? or & as the href needs', () => {
		expect(withSignup('/login')).toBe('/login?mode=signup');
		expect(withSignup('/login?redirect=%2Fx')).toBe('/login?redirect=%2Fx&mode=signup');
	});
});
