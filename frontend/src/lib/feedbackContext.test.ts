import { describe, expect, it } from 'vitest';
import { feedbackContext } from './feedbackContext';

describe('feedbackContext', () => {
	it('reads a book chapter as kind + slug + chapter', () => {
		expect(feedbackContext('/books/the-secret-of-guidance/3')).toEqual({
			content_kind: 'book',
			content_slug: 'the-secret-of-guidance',
			chapter_ref: '3'
		});
	});

	it('reads a book detail page without a chapter', () => {
		expect(feedbackContext('/books/the-secret-of-guidance')).toEqual({
			content_kind: 'book',
			content_slug: 'the-secret-of-guidance'
		});
	});

	it('ignores a locale prefix', () => {
		expect(feedbackContext('/lg/books/humility/2')).toEqual({
			content_kind: 'book',
			content_slug: 'humility',
			chapter_ref: '2'
		});
	});

	it('reads a sermon (no chapter)', () => {
		expect(feedbackContext('/sermons/the-expulsive-power')).toEqual({
			content_kind: 'sermon',
			content_slug: 'the-expulsive-power'
		});
	});

	it('does not treat a non-numeric trailing segment as a chapter', () => {
		expect(feedbackContext('/authors/andrew-murray')).toEqual({
			content_kind: 'author',
			content_slug: 'andrew-murray'
		});
	});

	it('returns empty for a non-work page', () => {
		expect(feedbackContext('/')).toEqual({});
		expect(feedbackContext('/settings')).toEqual({});
		expect(feedbackContext('/books')).toEqual({});
	});
});
