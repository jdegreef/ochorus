import { describe, expect, it } from 'vitest';
import { absUrl, jsonLd, breadcrumb } from './seo';
import { SITE_URL } from './config';

describe('absUrl', () => {
	it('makes a root-relative path absolute against the site origin', () => {
		expect(absUrl('/books/humility')).toBe(`${SITE_URL}/books/humility`);
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
			item: `${SITE_URL}/books/humility`
		});
	});
});
