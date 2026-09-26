import { describe, it, expect } from 'vitest';
import { languageFallback } from './languageFallback';

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
