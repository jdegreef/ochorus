import { describe, expect, it } from 'vitest';
import { cssString } from './cssString';

describe('cssString', () => {
	it('quotes an ordinary label', () => {
		expect(cssString('In prayer')).toBe("'In prayer'");
	});

	it('escapes the apostrophe that would end the string early', () => {
		// The whole point: unescaped, this closes the literal after "L" and the
		// rest of the declaration becomes garbage — silently, in one locale.
		expect(cssString("L'écoute")).toBe("'L\\'écoute'");
	});

	it('escapes backslashes before quotes, not after', () => {
		// Escaping in the wrong order turns \ into \\ and then mangles the
		// escape it just wrote.
		expect(cssString('a\\b')).toBe("'a\\\\b'");
		expect(cssString("a\\'b")).toBe("'a\\\\\\'b'");
	});

	it('replaces literal newlines, which are invalid inside a CSS string', () => {
		expect(cssString('one\ntwo')).toBe("'one\\A two'");
		expect(cssString('one\r\ntwo')).toBe("'one\\A two'");
	});

	it('leaves non-Latin text alone', () => {
		expect(cssString('في الصلاة')).toBe("'في الصلاة'");
		expect(cssString('У молитві')).toBe("'У молитві'");
	});

	it('handles an empty string', () => {
		expect(cssString('')).toBe("''");
	});
});
