import { describe, expect, it } from 'vitest';
import { tileFace, type BookTile } from './library-public';

const tile: BookTile = {
	kind: 'book',
	slug: 'rooted-1',
	title: 'Rooted',
	cover_url: '/covers/rooted-1.svg',
	cover_color: '#2f5d3a'
};

describe('tileFace', () => {
	it('is null for a tile from an API that sends only the ground', () => {
		expect(tileFace(tile)).toBeNull();
	});

	it('is the tile itself once it carries the cover fields', () => {
		const full: BookTile = {
			...tile,
			language: 'en',
			subtitle: '',
			cover_title: '',
			series_position: 1,
			author: { slug: 'ochorus', name: 'Ochorus', birth_year: null }
		};
		expect(tileFace(full)).toBe(full);
	});
});
