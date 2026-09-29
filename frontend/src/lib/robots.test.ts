import { describe, expect, it } from 'vitest';
import { locales } from '$lib/paraglide/runtime';
import { APP_ONLY, appOnlyDisallows } from './robots';

describe('appOnlyDisallows', () => {
	const rules = appOnlyDisallows();

	it('disallows every app-only path in every UI locale', () => {
		expect(rules).toHaveLength(APP_ONLY.length * locales.length);
		expect(rules).toContain('Disallow: /search?');
		for (const l of locales.filter((l) => l !== 'en')) {
			expect(rules).toContain(`Disallow: /${l}/search?`);
			expect(rules).toContain(`Disallow: /${l}/admin`);
		}
	});

	it('blocks search results but leaves the page crawlable, so its noindex is read', () => {
		expect(rules).not.toContain('Disallow: /search');
	});

	it('never disallows a content page by prefix', () => {
		for (const path of ['/books/', '/sermons/', '/articles/', '/es/books/', '/scripture/']) {
			expect(rules.some((r) => path.startsWith(r.slice('Disallow: '.length)))).toBe(false);
		}
	});
});
