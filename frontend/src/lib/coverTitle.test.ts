import { describe, expect, it } from 'vitest';
import { coverTitle } from './coverTitle';

describe('coverTitle', () => {
	const title = 'Rooted – 30 Days with God for Youth – Book 1';

	it('sets the short cover title when the book has one', () => {
		expect(coverTitle({ title, cover_title: 'Rooted' })).toBe('Rooted');
	});

	it('falls back to the title when it is blank, null or absent', () => {
		for (const cover_title of ['', null, undefined]) {
			expect(coverTitle({ title, cover_title })).toBe(title);
		}
	});
});
