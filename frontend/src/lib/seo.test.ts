import { describe, expect, it } from 'vitest';
import { absUrl, jsonLd, breadcrumb, hreflangFor, itemList } from './seo';
import { SITE_URL } from './config';

describe('absUrl', () => {
	it('makes a root-relative path absolute against the site origin', () => {
		// Detail paths gain the trailing slash — the non-slash form is the empty
		// SPA shell, so it must never be emitted as an absolute/canonical URL.
		expect(absUrl('/books/humility')).toBe(`${SITE_URL}/books/humility/`);
	});

	it('adds the leading slash when a path lacks one', () => {
		expect(absUrl('covers/x.png')).toBe(`${SITE_URL}/covers/x.png`);
	});

	it('passes an already-absolute URL through unchanged', () => {
		expect(absUrl('https://cdn.example.com/a.jpg')).toBe('https://cdn.example.com/a.jpg');
		expect(absUrl('http://x.test/y')).toBe('http://x.test/y');
	});

	it('returns the bare origin for an empty path', () => {
		expect(absUrl('')).toBe(SITE_URL);
	});
});

describe('jsonLd', () => {
	it('wraps data in an ld+json script tag', () => {
		const out = jsonLd({ '@type': 'Thing', name: 'x' });
		expect(out.startsWith('<script type="application/ld+json">')).toBe(true);
		expect(out.endsWith('</script>')).toBe(true);
	});

	it('escapes < so content can never break out of the script tag', () => {
		const out = jsonLd({ name: 'a </script><b>evil</b>' });
		// No literal "<" survives in the serialized JSON payload — only in the
		// wrapper tags themselves.
		const inner = out.slice('<script type="application/ld+json">'.length, -'</script>'.length);
		expect(inner).not.toContain('<');
		expect(inner).toContain('\\u003c');
	});

	it('round-trips to the original object once unescaped', () => {
		const data = { '@type': 'Article', headline: 'Faith < Hope' };
		const inner = jsonLd(data).replace(/^<script[^>]*>/, '').replace(/<\/script>$/, '');
		expect(JSON.parse(inner.replace(/\\u003c/g, '<'))).toEqual(data);
	});
});

describe('hreflangFor', () => {
	// Locale order follows the canonical set (en, es, sw, lg, pt, ar); en is
	// unprefixed, other locales carry a /<loc> prefix (localizeHref's behaviour).
	it('emits an alternate only for the locales the work exists in', () => {
		const { alternates } = hreflangFor('/books/humility/', ['en', 'sw']);
		expect(alternates.map((a) => a.loc)).toEqual(['en', 'sw']);
		expect(alternates[0].href).toBe(`${SITE_URL}/books/humility/`);
		expect(alternates[1].href).toContain(`${SITE_URL}/sw/books/humility`);
	});

	it('points x-default at the English URL when the work exists in English', () => {
		const { alternates, xDefault } = hreflangFor('/books/humility/', ['en', 'lg']);
		// x-default mirrors the English alternate's href exactly.
		expect(xDefault).toBe(alternates.find((a) => a.loc === 'en')!.href);
		expect(xDefault).toBe(`${SITE_URL}/books/humility/`);
	});

	it('points x-default at the first available locale when English is absent', () => {
		// A work translated to Swahili + Luganda but never published in English:
		// x-default must not claim an English URL that would soft-404 — it points
		// at the first available locale (the Swahili alternate) instead.
		const { alternates, xDefault } = hreflangFor('/sermons/himself/', ['sw', 'lg']);
		expect(alternates.map((a) => a.loc)).toEqual(['sw', 'lg']);
		expect(xDefault).toBe(alternates[0].href);
		expect(xDefault).toContain('/sw/sermons/himself');
	});

	it('ignores unknown/foreign locale codes from the API', () => {
		const { alternates } = hreflangFor('/plans/prayer/', ['en', 'fr', 'es']);
		expect(alternates.map((a) => a.loc)).toEqual(['en', 'es']);
	});

	it('falls back to every locale when availability is empty (older API)', () => {
		const { alternates, xDefault } = hreflangFor('/books/humility/', []);
		expect(alternates.map((a) => a.loc)).toEqual(['en', 'es', 'sw', 'lg', 'pt', 'ar']);
		expect(xDefault).toBe(`${SITE_URL}/books/humility/`);
	});
});

describe('itemList', () => {
	it('builds a positioned ItemList with absolute item URLs', () => {
		const out = itemList('Books', [
			{ name: 'Humility', url: '/books/humility' },
			{ name: 'All of Grace', url: '/books/all-of-grace' }
		]);
		const inner = out.replace(/^<script[^>]*>/, '').replace(/<\/script>$/, '');
		const data = JSON.parse(inner.replace(/\\u003c/g, '<'));
		expect(data['@type']).toBe('ItemList');
		expect(data.numberOfItems).toBe(2);
		expect(data.itemListElement[0]).toMatchObject({
			position: 1,
			name: 'Humility',
			url: `${SITE_URL}/books/humility/`
		});
		expect(data.itemListElement[1].position).toBe(2);
	});

	it('wraps the payload as an ld+json script', () => {
		const out = itemList('Empty', []);
		expect(out.startsWith('<script type="application/ld+json">')).toBe(true);
		expect(out.endsWith('</script>')).toBe(true);
	});
});

describe('breadcrumb', () => {
	it('builds a positioned BreadcrumbList with absolute item URLs', () => {
		const bc = breadcrumb([
			{ name: 'Home', url: '/' },
			{ name: 'Books', url: '/books' },
			{ name: 'Humility', url: '/books/humility' }
		]);
		expect(bc['@type']).toBe('BreadcrumbList');
		expect(bc.itemListElement).toHaveLength(3);
		expect(bc.itemListElement[0]).toMatchObject({ position: 1, name: 'Home', item: `${SITE_URL}/` });
		expect(bc.itemListElement[2]).toMatchObject({
			position: 3,
			name: 'Humility',
			item: `${SITE_URL}/books/humility/`
		});
	});
});
