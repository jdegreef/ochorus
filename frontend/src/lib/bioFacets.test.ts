import { describe, expect, it } from 'vitest';
import {
	bioChips,
	cleanFacetValues,
	facetCounts,
	hubMembers,
	inFacets,
	parseFacets,
	splitList,
	toggleIn,
	type BioFilterValues
} from './bioFacets';
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

describe('cleanFacetValues — the URL cleanup', () => {
	const clean = (raw: { trad: string; place: string; era: string }) =>
		cleanFacetValues(raw, parseFacets(raw, hubs));

	it('writes nothing when every value is one this language can show', () => {
		expect(clean({ trad: 'puritans,methodists', place: 'scotland', era: 'early' })).toEqual({});
		expect(clean({ trad: '', place: '', era: '' })).toEqual({});
	});
	it('drops a hub this language does not have (a link shared from English)', () => {
		expect(clean({ trad: 'puritans,anabaptists', place: '', era: '' })).toEqual({ trad: 'puritans' });
	});
	it('empties a facet whose only value is unknown, leaving the others alone', () => {
		expect(clean({ trad: 'anabaptists', place: 'scotland', era: 'bogus' })).toEqual({
			trad: '',
			era: ''
		});
	});
	it('drops a slug sent under the wrong facet', () => {
		// scotland is a place, puritans a tradition — each only counts in its own key.
		expect(clean({ trad: 'scotland', place: 'puritans', era: '' })).toEqual({ trad: '', place: '' });
	});
	it('collapses repeats and blanks', () => {
		expect(clean({ trad: 'puritans,,puritans', place: '', era: 'early, early' })).toEqual({
			trad: 'puritans',
			era: 'early'
		});
	});
	it('settles in one pass: applying it leaves nothing more to clean', () => {
		const raw = { trad: 'anabaptists,puritans,puritans', place: 'nowhere', era: 'early,bogus' };
		const next = { ...raw, ...clean(raw) };
		expect(clean(next)).toEqual({});
	});
	it('with no hubs (a failed hub fetch) clears hub facets but keeps eras', () => {
		const raw = { trad: 'puritans', place: 'scotland', era: 'early' };
		expect(cleanFacetValues(raw, parseFacets(raw, []))).toEqual({ trad: '', place: '' });
	});
});

describe('bioChips — the removable filter chips', () => {
	const t = (k: string) => `<${k}>`;
	const values = (over: Partial<BioFilterValues> = {}): BioFilterValues => ({
		q: '',
		filter: 'all',
		full: '',
		trad: '',
		place: '',
		era: '',
		...over
	});
	const labels = new Map([
		['trad:puritans', 'Puritans'],
		['trad:methodists', 'Methodists'],
		['place:scotland', 'Scotland'],
		['era:early', 'The Early Church']
	]);
	const chips = (v: BioFilterValues, showFullLife = true) =>
		bioChips(v, parseFacets(v, hubs), { labels, showFullLife, t });

	it('is empty when nothing narrows the roster', () => {
		expect(chips(values())).toEqual([]);
	});
	it('lists every active filter in control order, labelled', () => {
		const v = values({
			q: 'wesley',
			filter: 'library',
			full: '1',
			trad: 'puritans,methodists',
			place: 'scotland',
			era: 'early'
		});
		expect(chips(v).map((c) => [c.kind, c.label])).toEqual([
			['q', '“wesley”'],
			['filter', '<bios.filterInLibrary>'],
			['full', '<bios.fullLife>'],
			['trad:puritans', 'Puritans'],
			['trad:methodists', 'Methodists'],
			['place:scotland', 'Scotland'],
			['era:early', 'The Early Church']
		]);
	});
	it('labels a legacy ?filter=bio link as Biography only', () => {
		expect(chips(values({ filter: 'bio' })).map((c) => c.label)).toEqual(['<bios.filterBioOnly>']);
	});
	it('hides the Full-life chip when its control is hidden', () => {
		expect(chips(values({ full: '1' }), false)).toEqual([]);
	});
	it('falls back to the slug when no option labels a value', () => {
		const v = values({ trad: 'missionaries' });
		expect(chips(v).map((c) => c.label)).toEqual(['missionaries']);
	});
	it('shows no chip for a value the cleanup will drop', () => {
		expect(chips(values({ trad: 'anabaptists' }))).toEqual([]);
	});
	it('each × lifts only its own value', () => {
		const v = values({ q: 'x', filter: 'bio', full: '1', trad: 'puritans,methodists', era: 'early' });
		const byKind = (k: string) => chips(v).find((c) => c.kind === k)!;

		byKind('trad:puritans').onRemove();
		expect(v.trad).toBe('methodists');
		byKind('era:early').onRemove();
		expect(v.era).toBe('');
		byKind('filter').onRemove();
		expect(v.filter).toBe('all');
		byKind('full').onRemove();
		expect(v.full).toBe('');
		byKind('q').onRemove();
		expect(v.q).toBe('');
		expect(chips(v).map((c) => c.kind)).toEqual(['trad:methodists']);
	});
});
