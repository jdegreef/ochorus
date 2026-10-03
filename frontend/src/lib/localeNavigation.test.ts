import { describe, expect, it } from 'vitest';
import { crossesLocale } from './localeNavigation';

const u = (path: string, origin = 'https://ochorus.com') => new URL(path, origin);

describe('crossesLocale', () => {
	it('flags a hop between locale prefixes, both ways', () => {
		expect(crossesLocale(u('/ar/books/x'), u('/books/x'))).toBe(true);
		expect(crossesLocale(u('/books/x'), u('/ar/books/x'))).toBe(true);
		expect(crossesLocale(u('/es/'), u('/sw/sermons/y'))).toBe(true);
	});

	it('leaves same-locale navigation client-side', () => {
		expect(crossesLocale(u('/ar/books/x'), u('/ar/books/x/2'))).toBe(false);
		expect(crossesLocale(u('/books/x'), u('/sermons/y?edition=modern'))).toBe(false);
	});

	it('ignores other origins and missing ends', () => {
		expect(crossesLocale(u('/ar/'), u('/', 'https://example.com'))).toBe(false);
		expect(crossesLocale(undefined, u('/ar/'))).toBe(false);
		expect(crossesLocale(u('/ar/'), undefined)).toBe(false);
	});
});
