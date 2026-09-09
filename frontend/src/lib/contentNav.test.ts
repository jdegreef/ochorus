import { describe, it, expect } from 'vitest';
import { PRIMARY_NAV, ENGLISH_HUBS } from './contentNav';

/**
 * The nav, the footer Explore group and the command palette all `.map` these
 * two arrays, so this pins the ONE order they share. If a destination is added,
 * removed or reordered, that is a real chrome change and this test should be
 * updated deliberately — the point of F2 is that the order lives in exactly one
 * place, and this guards that it is the intended one.
 */
describe('contentNav', () => {
	it('keeps the primary nav order Books · Topics · Plans · Sermons · Biographies', () => {
		expect(PRIMARY_NAV.map((d) => d.href)).toEqual([
			'/books',
			'/topics',
			'/plans',
			'/sermons',
			'/biographies'
		]);
	});

	it('keeps the English-hub order Articles · Scripture · Quotes', () => {
		expect(ENGLISH_HUBS.map((d) => d.href)).toEqual(['/articles', '/scripture', '/quotes']);
	});

	it('gives every primary destination a label key and an icon', () => {
		for (const d of PRIMARY_NAV) {
			expect(d.labelKey).toMatch(/^[a-z]+\.[a-zA-Z]+$/);
			expect(d.icon).toBeTruthy();
		}
	});

	it('gives every hub a label key (no icon — hubs never sit in the top nav)', () => {
		for (const d of ENGLISH_HUBS) {
			expect(d.labelKey).toMatch(/^[a-z]+\.[a-zA-Z]+$/);
		}
	});

	it('uses canonical, trailing-slash-free hrefs (each surface adds its own)', () => {
		for (const d of [...PRIMARY_NAV, ...ENGLISH_HUBS]) {
			expect(d.href.startsWith('/')).toBe(true);
			expect(d.href.endsWith('/')).toBe(false);
		}
	});
});
