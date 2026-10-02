import { describe, expect, it } from 'vitest';
import { facetCounts, hubMembers, inFacets, parseFacets, splitList, toggleIn } from './bioFacets';
import type { AuthorBio, Hub } from './library-public';

const author = (slug: string, birth_year: number | null) =>
	({ slug, name: slug, birth_year }) as unknown as AuthorBio;
const hub = (kind: Hub['kind'], slug: string, members: string[], region: string | null = null) =>
	({ kind, slug, label: slug, members, region }) as unknown as Hub;

const authors = [
	author('bunyan', 1628),
	author('baxter', 1615),
	author('wesley', 1703),
	author('slessor', 1848),
	author('mcheyne', 1813),
	author('augustine', 354)
];
const hubs = [
	hub('tradition', 'puritans', ['bunyan', 'baxter']),
	hub('tradition', 'methodists', ['wesley']),
	hub('tradition', 'missionaries', ['slessor']),
	hub('region', 'britain', ['bunyan', 'baxter', 'wesley', 'slessor', 'mcheyne']),
	hub('place', 'scotland', ['slessor', 'mcheyne'], 'britain'),
	hub('place', 'north-africa', ['augustine'])
];
const members = hubMembers(hubs);

describe('splitList / toggleIn', () => {
	it('drops blanks and repeats', () => {
		expect(splitList('a,,b, a ,')).toEqual(['a', 'b']);
		expect(splitList('')).toEqual([]);
	});
	it('toggles a value in and out of a comma list', () => {
		expect(toggleIn('', 'a')).toBe('a');
		expect(toggleIn('a', 'b')).toBe('a,b');
		expect(toggleIn('a,b', 'a')).toBe('b');
	});
});

describe('parseFacets', () => {
	it('keeps only values this language can show, in the right facet', () => {
		const f = parseFacets(
			{ trad: 'puritans,scotland,nope', place: 'britain,scotland,puritans', era: 'early,bogus' },
			hubs
		);
		expect(f).toEqual({ trad: ['puritans'], place: ['britain', 'scotland'], era: ['early'] });
	});
});

describe('inFacets', () => {
	it('ORs within a facet and ANDs across facets', () => {
		const f = { trad: ['puritans', 'methodists'], place: [], era: [] };
		expect(authors.filter((a) => inFacets(a, f, members)).map((a) => a.slug)).toEqual([
			'bunyan',
			'baxter',
			'wesley'
		]);
		const g = { trad: ['puritans', 'methodists'], place: [], era: ['awakenings'] };
		expect(authors.filter((a) => inFacets(a, g, members)).map((a) => a.slug)).toEqual(['wesley']);
	});
	it('a region tick takes in its places’ writers', () => {
		const f = { trad: [], place: ['britain'], era: [] };
		expect(authors.filter((a) => inFacets(a, f, members))).toHaveLength(5);
	});
	it('ignores the skipped facet', () => {
		const f = { trad: ['puritans'], place: [], era: ['missionary'] };
		expect(authors.filter((a) => inFacets(a, f, members))).toHaveLength(0);
		expect(authors.filter((a) => inFacets(a, f, members, 'era')).map((a) => a.slug)).toEqual([
			'bunyan',
			'baxter'
		]);
	});
});

describe('facetCounts', () => {
	it('counts each option under the OTHER facets, not its own', () => {
		const f = { trad: ['puritans'], place: ['scotland'], era: [] };
		const trad = facetCounts(authors, f, members, 'trad', ['puritans', 'missionaries']);
		// Scotland narrows tradition counts; ticking Puritans doesn't zero Missionaries.
		expect(Object.fromEntries(trad)).toEqual({ puritans: 0, missionaries: 1 });
		const era = facetCounts(authors, { trad: [], place: [], era: ['early'] }, members, 'era', ['early', 'puritans']);
		expect(Object.fromEntries(era)).toEqual({ early: 1, puritans: 2 });
	});
	it('counts within the pool it is given', () => {
		const pool = authors.filter((a) => a.slug !== 'bunyan');
		const c = facetCounts(pool, { trad: [], place: [], era: [] }, members, 'trad', ['puritans']);
		expect(c.get('puritans')).toBe(1);
	});
});
