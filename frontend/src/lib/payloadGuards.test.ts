import { describe, expect, it } from 'vitest';
import {
	BOOK_FIELDS,
	CHAPTER_FIELDS,
	PayloadError,
	requireFields,
	SERMON_FIELDS
} from './payloadGuards';

const chapter = (over: Record<string, unknown> = {}) => ({
	order: 3,
	title: 'The Path',
	body_html: '<p>Prose.</p>',
	book_title: 'Humility',
	book_slug: 'humility',
	author_name: 'Andrew Murray',
	// Fields the guard deliberately ignores — their loss is cosmetic.
	available_languages: ['en', 'es'],
	prev: null,
	next: null,
	...over
});

describe('requireFields', () => {
	it('passes a payload through unchanged', () => {
		const c = chapter();
		expect(requireFields('chapter humility/3', c, CHAPTER_FIELDS)).toBe(c);
	});

	// The failure this exists for: a DRF field rename ships a reader that
	// renders `undefined` with no error anywhere.
	it('catches a renamed field', () => {
		const { body_html, ...rest } = chapter();
		expect(() =>
			requireFields('chapter humility/3', { ...rest, body: body_html }, CHAPTER_FIELDS)
		).toThrow(PayloadError);
	});

	it('names the endpoint and every bad field at once', () => {
		// A skew usually renames several together; one report that lists them
		// all is one deploy to fix rather than three.
		try {
			requireFields(
				'chapter humility/3',
				chapter({ body_html: undefined, book_title: undefined }),
				CHAPTER_FIELDS
			);
			expect.unreachable('should have thrown');
		} catch (e) {
			expect(e).toBeInstanceOf(PayloadError);
			const err = e as PayloadError;
			expect(err.what).toBe('chapter humility/3');
			expect(err.fields).toEqual(['body_html (string)', 'book_title (string)']);
			expect(err.message).toContain('different releases');
		}
	});

	it('catches a field whose type changed', () => {
		// `order` arriving as "3" would break the resume anchor silently.
		expect(() => requireFields('c', chapter({ order: '3' }), CHAPTER_FIELDS)).toThrow(
			PayloadError
		);
	});

	it('accepts an empty string, which is a legitimate value', () => {
		// A chapter may genuinely have no title — the content audit reports that
		// as a quality finding, not a broken payload.
		expect(() => requireFields('c', chapter({ title: '' }), CHAPTER_FIELDS)).not.toThrow();
	});

	it('accepts zero and false rather than treating them as absent', () => {
		expect(() =>
			requireFields('x', { n: 0, b: false }, { n: 'number', b: 'boolean' })
		).not.toThrow();
	});

	it('rejects a response that is not an object at all', () => {
		for (const bad of [null, undefined, 'a string', 42, ['an', 'array']]) {
			expect(() => requireFields('c', bad, CHAPTER_FIELDS)).toThrow(PayloadError);
		}
	});

	it('does not care about fields it was not asked to check', () => {
		// Losing `available_languages` costs an hreflang, not the page — taking a
		// working chapter down over that would be the worse trade.
		const { available_languages: _dropped, ...without } = chapter();
		expect(() => requireFields('c', without, CHAPTER_FIELDS)).not.toThrow();
	});

	it('rejects an array where an array is required', () => {
		expect(() =>
			requireFields('book humility', { slug: 'h', title: 'H', language: 'en' }, BOOK_FIELDS)
		).toThrow(/chapters \(array\)/);
	});
});

describe('the guarded shapes', () => {
	// Each names the thing whose absence makes the page a lie.
	it('a chapter is guarded on its prose', () => {
		expect(CHAPTER_FIELDS.body_html).toBe('string');
	});

	it('a book is guarded on its table of contents', () => {
		expect(BOOK_FIELDS.chapters).toBe('array');
	});

	it('a sermon is guarded on its prose', () => {
		expect(SERMON_FIELDS.body_html).toBe('string');
	});

	it('guards stay narrow — the cosmetic fields are left out', () => {
		for (const spec of [CHAPTER_FIELDS, BOOK_FIELDS, SERMON_FIELDS]) {
			expect(spec).not.toHaveProperty('available_languages');
			expect(spec).not.toHaveProperty('topics');
		}
	});
});
