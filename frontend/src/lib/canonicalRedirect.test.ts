import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { RENDER_HOST, canonicalRedirect, isSlashedPath } from './canonicalRedirect';

const SITE = 'https://ochorus.com';
const at = (hostname: string, pathname: string, search = '', hash = '') => ({
	hostname,
	pathname,
	search,
	hash
});

describe('canonicalRedirect', () => {
	it('sends a no-slash URL to its prerendered slash form, query and hash kept', () => {
		expect(canonicalRedirect(at('ochorus.com', '/books/humility'), SITE)).toBe('/books/humility/');
		expect(canonicalRedirect(at('ochorus.com', '/es/books/humility/3', '?x=1', '#p4'), SITE)).toBe(
			'/es/books/humility/3/?x=1#p4'
		);
		expect(canonicalRedirect(at('ochorus.com', '/authors'), SITE)).toBe('/authors/');
		expect(canonicalRedirect(at('ochorus.com', '/scripture/romans/8/28'), SITE)).toBe(
			'/scripture/romans/8/28/'
		);
	});

	it('leaves canonical URLs, index pages and app routes where they are', () => {
		for (const p of ['/books/humility/', '/books', '/', '/search', '/reading', '/admin/books', '/biographies']) {
			expect(canonicalRedirect(at('ochorus.com', p), SITE), p).toBeNull();
		}
	});

	it('never turns a doubled leading slash into another host', () => {
		expect(canonicalRedirect(at('ochorus.com', '//authors'), SITE)).toBe('/authors/');
		expect(canonicalRedirect(at('ochorus.com', '//books/x/'), SITE)).toBe('/books/x/');
	});

	it("moves the production service's Render host to the real domain", () => {
		expect(canonicalRedirect(at(RENDER_HOST, '/books/humility'), SITE)).toBe(
			'https://ochorus.com/books/humility/'
		);
		expect(canonicalRedirect(at(RENDER_HOST, '/', '?q=1'), SITE)).toBe('https://ochorus.com/?q=1');
	});

	it('never moves a preview host, or the Render host when it IS the configured site', () => {
		expect(canonicalRedirect(at('ochorus-web-pr-12.onrender.com', '/books/x/'), SITE)).toBeNull();
		expect(canonicalRedirect(at(RENDER_HOST, '/books/x/'), `https://${RENDER_HOST}`)).toBeNull();
	});
});

describe('isSlashedPath matches the route tree', () => {
	// Every route that exports trailingSlash = 'always', as a sample URL (each
	// [param] filled with "x"): the rule must claim all of them, so a new
	// slashed route that the rule misses fails here rather than shipping a
	// shell duplicate nobody redirects.
	const ROUTES = resolve(process.cwd(), 'src/routes');
	const slashed: string[] = [];
	const walk = (dir: string, url: string[]) => {
		for (const name of readdirSync(dir)) {
			const full = join(dir, name);
			if (statSync(full).isDirectory()) {
				if (!name.startsWith('(')) walk(full, [...url, name.replace(/^\[.*\]$/, 'x')]);
			} else if (name === '+page.ts' && /trailingSlash\s*=\s*'always'/.test(readFileSync(full, 'utf8'))) {
				slashed.push(`/${url.join('/')}`);
			}
		}
	};
	walk(ROUTES, []);

	it('claims every slashed route', () => {
		expect(slashed.length).toBeGreaterThan(10);
		for (const p of slashed) expect(isSlashedPath(p), p).toBe(true);
	});
});
