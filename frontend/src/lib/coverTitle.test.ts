import { describe, expect, it } from 'vitest';
import { coverTitle, editionOf } from './coverTitle';

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

describe('editionOf', () => {
	it('lifts a young edition’s bracket off the title, in any language', () => {
		expect(editionOf('absolute-surrender-teens', 'Absolute Surrender (For Teens)')).toEqual({
			words: 'Absolute Surrender',
			edition: 'For Teens'
		});
		expect(editionOf('pilgrims-progress-teens', 'El progreso del peregrino (para jóvenes)')).toEqual({
			words: 'El progreso del peregrino',
			edition: 'para jóvenes'
		});
		expect(editionOf('a-retrospect-teens', 'ወደ ኋላ መለስ ብሎ ማየት (ለወጣቶች)')).toEqual({
			words: 'ወደ ኋላ መለስ ብሎ ማየት',
			edition: 'ለወጣቶች'
		});
	});

	it('leaves every other title whole', () => {
		// Not a young edition, though it ends in a bracket.
		expect(editionOf('holiness', 'Holiness (Abridged)')).toEqual({ words: 'Holiness (Abridged)', edition: null });
		// A young-looking slug whose title has no bracket.
		expect(editionOf('come-ye-children', 'Come Ye Children')).toEqual({
			words: 'Come Ye Children',
			edition: null
		});
		// A bracket that is not at the end.
		expect(editionOf('x-teens', 'Faith (and Works) for Today')).toEqual({
			words: 'Faith (and Works) for Today',
			edition: null
		});
	});
});
