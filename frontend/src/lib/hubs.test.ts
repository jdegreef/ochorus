import { describe, expect, it } from 'vitest';
import { findHub, hubPath, hubShelf, hubWriters, placeGroups, relatedPlaces } from './hubs';
import type { AuthorBio, BookSummary, Hub } from './library-public';

const hub = (kind: Hub['kind'], slug: string, extra: Partial<Hub> = {}): Hub => ({
	kind,
	slug,
	region: null,
	name: slug,
	intro: '',
	qa: [],
	members: [],
	available_languages: ['en'],
	...extra
});

const author = (slug: string, birth: number | null): AuthorBio =>
	({ slug, name: slug, birth_year: birth, death_year: null }) as AuthorBio;
const book = (slug: string, by: string) => ({ slug, author: { slug: by } }) as BookSummary;

const HUBS = [
	hub('tradition', 'puritans'),
	hub('region', 'britain'),
	hub('place', 'wales', { region: 'britain' }),
	hub('place', 'england', { region: 'britain' }),
	hub('place', 'uganda', { region: 'east-africa' })
];

describe('hubs', () => {
	it('routes traditions and places to their own segment', () => {
		expect(hubPath({ kind: 'tradition', slug: 'puritans' })).toBe('/biographies/tradition/puritans');
		expect(hubPath({ kind: 'region', slug: 'britain' })).toBe('/biographies/place/britain');
		expect(hubPath({ kind: 'place', slug: 'wales' })).toBe('/biographies/place/wales');
	});

	it('finds a hub only under its own route', () => {
		expect(findHub(HUBS, 'wales', 'place')?.slug).toBe('wales');
		expect(findHub(HUBS, 'britain', 'place')?.slug).toBe('britain');
		expect(findHub(HUBS, 'wales', 'tradition')).toBeUndefined();
		expect(findHub(HUBS, 'puritans', 'place')).toBeUndefined();
	});

	it('lists members earliest-born first, undated last, and skips unlisted writers', () => {
		const h = hub('tradition', 't', { members: ['c', 'a', 'b', 'gone'] });
		const got = hubWriters(h, [author('a', 1700), author('b', null), author('c', 1600), author('z', 1500)]);
		expect(got.map((a) => a.slug)).toEqual(['c', 'a', 'b']);
	});

	it('shelves one book per writer, in writer order, capped', () => {
		const writers = [author('a', 1), author('b', 2), author('c', 3)];
		const books = [book('b1', 'b'), book('a1', 'a'), book('a2', 'a'), book('x', 'x')];
		expect(hubShelf(writers, books).map((b) => b.slug)).toEqual(['a1', 'b1']);
		expect(hubShelf(writers, books, 1).map((b) => b.slug)).toEqual(['a1']);
	});

	it('relates a region to its places and a place to its region and siblings', () => {
		expect(relatedPlaces(HUBS[1], HUBS).map((h) => h.slug)).toEqual(['wales', 'england']);
		expect(relatedPlaces(HUBS[2], HUBS).map((h) => h.slug)).toEqual(['britain', 'england']);
		expect(relatedPlaces(HUBS[0], HUBS)).toEqual([]);
	});

	it('groups places under their region, keeping a place whose region has no page', () => {
		const groups = placeGroups(HUBS);
		expect(groups.map((g) => [g.region?.slug ?? null, g.places.map((p) => p.slug)])).toEqual([
			['britain', ['wales', 'england']],
			[null, ['uganda']]
		]);
	});
});
