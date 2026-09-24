import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { beforeEach, describe, expect, it } from 'vitest';
import { normalizeSiteFont, siteFont, SITE_FONTS } from './siteFont.svelte';

const KEY = 'ochorus:site-font';

beforeEach(() => {
	localStorage.clear();
	delete document.documentElement.dataset.siteFont;
});

describe('siteFont store', () => {
	it('normalises unknown and absent values to the house style', () => {
		expect(normalizeSiteFont(null)).toBe('house');
		expect(normalizeSiteFont('papyrus')).toBe('house');
		expect(normalizeSiteFont('classic')).toBe('classic');
	});

	it('applies a style to the root and persists it', () => {
		siteFont.set('hyperlegible');
		expect(document.documentElement.dataset.siteFont).toBe('hyperlegible');
		expect(localStorage.getItem(KEY)).toBe('hyperlegible');
	});

	it('clears the attribute and the key for the house style', () => {
		siteFont.set('classic');
		siteFont.set('house');
		expect(document.documentElement.dataset.siteFont).toBeUndefined();
		expect(localStorage.getItem(KEY)).toBeNull();
	});

	it('hydrates from storage', () => {
		localStorage.setItem(KEY, 'classic');
		siteFont.init();
		expect(siteFont.current).toBe('classic');
		expect(document.documentElement.dataset.siteFont).toBe('classic');
	});

	it('agrees with the app.html boot script on which styles exist', () => {
		// The boot script restates the list (it runs before any module loads);
		// a style added here and not there would flash the house face first.
		const html = readFileSync(join(process.cwd(), 'src/app.html'), 'utf-8');
		for (const f of SITE_FONTS.filter((f) => f !== 'house')) {
			expect(html, `app.html's boot script does not apply '${f}'`).toContain(`sf === '${f}'`);
		}
		expect(html).toContain(`getItem('${KEY}')`);
	});
});
