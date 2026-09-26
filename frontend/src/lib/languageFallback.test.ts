import { describe, it, expect } from 'vitest';
import { editionSeo, languageFallback } from './languageFallback';

describe('languageFallback', () => {
	it('is null when the page shows the language its URL asks for', () => {
		expect(languageFallback('es', 'es')).toBeNull();
		expect(languageFallback('en', 'en')).toBeNull();
	});

	it('reports the English fallback under a localized URL', () => {
		expect(languageFallback('hi', 'en')).toEqual({ requested: 'hi', shown: 'en' });
	});

	it('treats the Modern English edition as English, not as a fallback', () => {
		expect(languageFallback('en-modern', 'en-modern')).toBeNull();
		expect(languageFallback('en', 'en-modern')).toBeNull();
		// Asking for the modern edition under /es still shows English there.
		expect(languageFallback('es', 'en-modern')).toEqual({ requested: 'es', shown: 'en' });
	});
});

describe('editionSeo', () => {
	it('canonicalizes a fallback page onto the edition it shows', () => {
		const { canonical } = editionSeo('/books/x/', ['en', 'es'], { requested: 'sw', shown: 'en' });
		expect(canonical.endsWith('/books/x/')).toBe(true);
		expect(canonical).not.toContain('/sw/');
	});

	it('keeps the self-referential canonical when nothing fell back', () => {
		const { canonical, hreflang } = editionSeo('/books/x/', ['en', 'es'], null);
		expect(canonical).toBe(hreflang.alternates.find((a) => a.loc === 'en')?.href);
	});
});
