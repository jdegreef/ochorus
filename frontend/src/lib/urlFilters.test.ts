/**
 * The URL-filter encoding.
 *
 * Two things have to hold or a shared link is worse than none: a pristine shelf
 * must produce a clean URL (else every link anyone copies carries `?q=&source=all`
 * forever), and a hand-edited or stale query string must never put the shelf
 * into a state its own controls cannot get back out of.
 */
import { describe, expect, it } from 'vitest';
import { filterKey, writeFilters, readFilters } from './urlFilters';

const DEFAULTS = { q: '', source: 'all', topic: '' };
const ALLOWED = { source: ['all', 'public_domain', 'translated'] } as const;

const params = (search: string) => new URLSearchParams(search);
const url = (href = 'https://ochorus.com/books') => new URL(href);

describe('writeFilters', () => {
	it('leaves a pristine view as a clean URL', () => {
		expect(writeFilters(url(), DEFAULTS, DEFAULTS).search).toBe('');
	});

	it('writes only what differs from the default', () => {
		const out = writeFilters(url(), { ...DEFAULTS, source: 'translated' }, DEFAULTS);
		expect(out.search).toBe('?source=translated');
	});

	it('drops a filter that has gone back to its default', () => {
		const out = writeFilters(url('https://ochorus.com/books?source=translated&q=grace'), {
			...DEFAULTS,
			q: 'grace'
		}, DEFAULTS);
		expect(out.searchParams.get('source')).toBeNull();
		expect(out.searchParams.get('q')).toBe('grace');
	});

	it('trims the search term rather than encoding whitespace', () => {
		expect(writeFilters(url(), { ...DEFAULTS, q: '  prayer  ' }, DEFAULTS).search).toBe('?q=prayer');
	});

	it('keeps query params it was not given', () => {
		// The locale router and campaign tags live on the same URL.
		const out = writeFilters(url('https://ochorus.com/books?ref=newsletter'), DEFAULTS, DEFAULTS);
		expect(out.searchParams.get('ref')).toBe('newsletter');
	});

	it('does not mutate the URL it was handed', () => {
		const original = url();
		writeFilters(original, { ...DEFAULTS, q: 'grace' }, DEFAULTS);
		expect(original.search).toBe('');
	});
});

describe('readFilters', () => {
	it('returns the defaults for an empty query string', () => {
		expect(readFilters(params(''), DEFAULTS, ALLOWED)).toEqual(DEFAULTS);
	});

	it('reads values that are on the list', () => {
		expect(readFilters(params('?q=grace&source=translated'), DEFAULTS, ALLOWED)).toEqual({
			q: 'grace',
			source: 'translated',
			topic: ''
		});
	});

	it('refuses an enum value that is not on the list', () => {
		// A hand-edited or stale link must not select a filter the controls
		// cannot show, or the reader is stuck looking at nothing.
		expect(readFilters(params('?source=nonsense'), DEFAULTS, ALLOWED).source).toBe('all');
	});

	it('takes free-text keys as given', () => {
		// A topic slug is not an enum — the list depends on the shelf.
		expect(readFilters(params('?topic=prayer'), DEFAULTS, ALLOWED).topic).toBe('prayer');
	});

	it('ignores query params it does not know', () => {
		const out = readFilters(params('?ref=newsletter&q=grace'), DEFAULTS, ALLOWED);
		expect(out).toEqual({ q: 'grace', source: 'all', topic: '' });
	});

	it('round-trips through writeFilters', () => {
		const values = { q: 'holy living', source: 'translated', topic: 'prayer' };
		const written = writeFilters(url(), values, DEFAULTS);
		expect(readFilters(written.searchParams, DEFAULTS, ALLOWED)).toEqual(values);
	});
});

describe('filterKey', () => {
	it('is stable regardless of key order', () => {
		expect(filterKey({ q: 'a', source: 'all' })).toBe(filterKey({ source: 'all', q: 'a' }));
	});

	it('ignores whitespace, so typing a trailing space is not a navigation', () => {
		expect(filterKey({ q: 'grace ' })).toBe(filterKey({ q: 'grace' }));
	});

	it('separates values that would otherwise concatenate', () => {
		expect(filterKey({ a: 'x', b: 'y' })).not.toBe(filterKey({ a: 'xy', b: '' }));
	});
});
