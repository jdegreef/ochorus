import { describe, expect, it } from 'vitest';
import { editDistance, missedDetail, recoverSlug, slugKey } from './slugMatch';

const AUTHORS = [
	'charles-h-spurgeon',
	'dwight-l-moody',
	'andrew-murray',
	'augustine-of-hippo',
	'thomas-a-kempis',
	'charles-finney',
	'e-m-bounds'
].map((slug) => ({ slug }));
const slugs = (xs: { slug: string }[]) => xs.map((x) => x.slug);

describe('slugKey', () => {
	it('drops initials, saint/st, a leading "the", accents and punctuation', () => {
		expect(slugKey('charles-h-spurgeon')).toBe('charles-spurgeon');
		expect(slugKey('Charles_H._Spurgeon')).toBe('charles-spurgeon');
		expect(slugKey('saint-augustine-of-hippo')).toBe('augustine-of-hippo');
		expect(slugKey('st-augustine-of-hippo')).toBe('augustine-of-hippo');
		expect(slugKey('the-imitation-of-christ')).toBe('imitation-of-christ');
		expect(slugKey('thérèse-of-lisieux')).toBe('therese-of-lisieux');
	});

	it('keeps numbers: a volume is not an initial', () => {
		expect(slugKey('lord-teach-us-to-pray-2')).toBe('lord-teach-us-to-pray-2');
	});
});

describe('editDistance', () => {
	it('counts edits, and stops early past the cap', () => {
		expect(editDistance('murray', 'muray')).toBe(1);
		expect(editDistance('kitten', 'sitting')).toBe(3);
		expect(editDistance('abc', 'abcdefgh', 2)).toBe(3);
	});
});

describe('recoverSlug', () => {
	it('forwards a unique alias', () => {
		expect(recoverSlug('charles-spurgeon', AUTHORS).forward?.slug).toBe('charles-h-spurgeon');
		expect(recoverSlug('dwight-moody', AUTHORS).forward?.slug).toBe('dwight-l-moody');
		expect(recoverSlug('st-augustine-of-hippo', AUTHORS).forward?.slug).toBe('augustine-of-hippo');
		expect(recoverSlug('thomas-kempis', AUTHORS).forward?.slug).toBe('thomas-a-kempis');
	});

	it('never forwards an ambiguous alias, but offers both', () => {
		const shelf = [{ slug: 'john-wesley' }, { slug: 'john-a-wesley' }];
		const r = recoverSlug('john-b-wesley', shelf);
		expect(r.forward).toBeNull();
		expect(slugs(r.suggestions)).toEqual(['john-a-wesley', 'john-wesley']);
	});

	it('suggests, without forwarding, a typo or a partial name', () => {
		const typo = recoverSlug('andrew-muray', AUTHORS);
		expect(typo.forward).toBeNull();
		expect(slugs(typo.suggestions)).toEqual(['andrew-murray']);

		const slip = recoverSlug('humilty', [{ slug: 'humility-2' }, { slug: 'holiness' }]);
		expect(slip.forward).toBeNull();
		expect(slugs(slip.suggestions)).toEqual(['humility-2']);

		const surname = recoverSlug('spurgeon', AUTHORS);
		expect(surname.forward).toBeNull();
		expect(slugs(surname.suggestions)).toEqual(['charles-h-spurgeon']);
	});

	it('ranks an alias ahead of near misses, and caps the list', () => {
		const r = recoverSlug('charles', AUTHORS, 1);
		expect(r.suggestions).toHaveLength(1);
		const s = recoverSlug('charles-spurgeon', AUTHORS);
		expect(s.suggestions[0].slug).toBe('charles-h-spurgeon');
	});

	it('finds nothing for an unrelated slug', () => {
		expect(recoverSlug('no-such-person-at-all', AUTHORS)).toEqual({
			forward: null,
			suggestions: []
		});
	});

	it('does nothing when the asked slug exists (the page failed some other way)', () => {
		expect(recoverSlug('andrew-murray', AUTHORS)).toEqual({
			forward: null,
			suggestions: []
		});
	});

	it('does nothing for a slug that is all noise', () => {
		expect(recoverSlug('the-a', AUTHORS)).toEqual({
			forward: null,
			suggestions: []
		});
	});

	it('does not offer a slug twice when the shelf repeats it', () => {
		const r = recoverSlug('andrew-muray', [...AUTHORS, { slug: 'andrew-murray' }]);
		expect(slugs(r.suggestions)).toEqual(['andrew-murray']);
	});
});

describe('missedDetail', () => {
	it('reads the section and slug, and rebuilds the URL around another slug', () => {
		const m = missedDetail('/authors/charles-spurgeon/');
		expect(m?.section).toBe('authors');
		expect(m?.slug).toBe('charles-spurgeon');
		expect(m?.withSlug('charles-h-spurgeon')).toBe('/authors/charles-h-spurgeon/');
	});

	it('keeps the locale prefix and a book chapter', () => {
		const m = missedDetail('/es/books/imitation-of-chryst/3');
		expect(m?.section).toBe('books');
		expect(m?.withSlug('imitation-of-christ')).toBe('/es/books/imitation-of-christ/3/');
	});

	it('ignores other sections, index pages and deeper author/sermon paths', () => {
		expect(missedDetail('/topics/prayer/')).toBeNull();
		expect(missedDetail('/books/')).toBeNull();
		expect(missedDetail('/authors/x/quotes/')).toBeNull();
		expect(missedDetail('/sermons/a-sermon/')?.section).toBe('sermons');
	});

	it('survives a malformed escape', () => {
		expect(missedDetail('/books/%E0%A4%A/')).toBeNull();
	});
});
