import { describe, it, expect } from 'vitest';
import { authorCardUrl, authorData, cardQuote } from './authorCard';

const inlined = (url: string, body: unknown, status = 200) =>
	`<script type="application/json" data-sveltekit-fetched data-url="${url}" data-hash="1">` +
	JSON.stringify({ status, statusText: '', headers: {}, body: JSON.stringify(body) }) +
	'</script>';

const API = 'https://api.ochorus.com/api/library/authors';

describe('author share card', () => {
	it('lives at one path per author per language', () => {
		expect(authorCardUrl('andrew-murray', 'es')).toBe('/og/authors/es/andrew-murray.jpg');
	});

	it('reads the author a prerendered page was rendered from', () => {
		const author = { slug: 'andrew-murray', name: 'Andrew Murray', books: [] };
		const html = inlined(`${API}/andrew-murray/?language=es`, author);
		expect(authorData(html)).toEqual({ author, language: 'es' });
	});

	it('skips the 404 a language with no row inlines, and takes the English fallback', () => {
		const author = { slug: 'isaac-watts', name: 'Isaac Watts' };
		const html =
			inlined(`${API}/isaac-watts/?language=lg`, { detail: 'Not found.' }, 404) +
			inlined(`${API}/isaac-watts/?language=en`, author);
		expect(authorData(html)).toEqual({ author, language: 'en' });
	});

	it('declines a page with no author on it', () => {
		expect(authorData('<html></html>')).toBeNull();
		expect(authorData(inlined(`${API}/`, [{ slug: 'x', name: 'X' }]))).toBeNull();
	});

	it('quotes the first line short enough to set whole', () => {
		const long = 'x'.repeat(200);
		expect(
			cardQuote([
				{ text: long },
				{ text: 'Too short.' },
				{ text: '  God always meets His children where they are.  ' }
			])
		).toBe('God always meets His children where they are.');
		expect(cardQuote([{ text: long }])).toBeNull();
	});
});
