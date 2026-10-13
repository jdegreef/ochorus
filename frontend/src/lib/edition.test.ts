import { describe, it, expect } from 'vitest';
import { childrensReading, splitEdition } from './edition';

describe('splitEdition', () => {
	it('splits a children edition into base + audience', () => {
		expect(splitEdition('talks-to-the-farmer-children', 'Talks to the Farmer (For Children)')).toEqual(
			{ base: 'Talks to the Farmer', audience: 'For Children', kind: 'children' }
		);
	});

	it('splits a teens edition', () => {
		expect(splitEdition('pilgrims-progress-teens', "Pilgrim's Progress (For Teens)")).toEqual({
			base: "Pilgrim's Progress",
			audience: 'For Teens',
			kind: 'teens'
		});
	});

	it('reads the audience from the (already-translated) title, whatever the language', () => {
		expect(
			splitEdition('pilgrims-progress-teens', 'Le Voyage du pèlerin (Pour les adolescents)')
		).toEqual({ base: 'Le Voyage du pèlerin', audience: 'Pour les adolescents', kind: 'teens' });
	});

	it('takes the trailing parenthetical, not an earlier one', () => {
		expect(splitEdition('x-children', 'A Book (Abridged) (For Children)')).toEqual({
			base: 'A Book (Abridged)',
			audience: 'For Children',
			kind: 'children'
		});
	});

	it('returns null for a non-edition slug', () => {
		expect(splitEdition('talks-to-the-farmer', 'Talks to the Farmer')).toBeNull();
	});

	it('returns null when an edition slug has no trailing parenthetical', () => {
		// A real work whose own title ends "…for Children" (slug suffix, no "(…)").
		expect(splitEdition('divine-songs-for-children', 'Divine Songs for Children')).toBeNull();
	});
});

describe('childrensReading', () => {
	it('is a children’s edition, or a book in a young-readers series', () => {
		expect(childrensReading('children', undefined)).toBe(true);
		expect(childrensReading(null, 'young_readers')).toBe(true);
	});

	it('is never a teens edition, even in a young-readers series', () => {
		expect(childrensReading('teens', 'young_readers')).toBe(false);
	});

	it('is not an ordinary book, or one served by an API without the field', () => {
		expect(childrensReading(null, 'adults')).toBe(false);
		expect(childrensReading(null, '')).toBe(false);
		expect(childrensReading(null, undefined)).toBe(false);
	});
});
