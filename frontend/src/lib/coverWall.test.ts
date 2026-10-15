import { describe, expect, it } from 'vitest';
import { COVER_SCRIM } from './coverScrim';
import { AUTHOR_LAYOUT } from './coverLayouts';
import { PAINTER_CAP, coverFlags, groupCovers, hueOf, painterWorks } from './coverWall';
import type { AdminCover, CoverTier } from './library-admin';

const cover = (
	slug: string,
	tier: CoverTier,
	opts: { lang?: string; artist?: string; author?: string } = {}
): AdminCover => ({
	slug,
	language: opts.lang ?? 'en',
	title: slug,
	author: { slug: opts.author ?? 'nobody-framed', name: opts.author ?? 'Nobody' },
	cover_url: tier === 'plate' ? `/covers/${slug}.svg` : `/covers/art/${slug}.jpg`,
	tier,
	artwork: opts.artist
		? { artist: opts.artist, title: 't', year: '1850', source: 'aic', institution: 'AIC', object_id: 1 }
		: null
});

describe('painterWorks', () => {
	it('counts distinct works, not editions', () => {
		const works = painterWorks([
			cover('a', 'painting', { artist: 'Inness' }),
			cover('a', 'painting', { artist: 'Inness', lang: 'sw' }),
			cover('b', 'painting', { artist: 'Inness' })
		]);
		expect(works.get('Inness')?.size).toBe(2);
	});
});

describe('coverFlags', () => {
	it('flags a plate', () => {
		expect(coverFlags(cover('p', 'plate'), new Map())).toEqual(['plate']);
	});

	it(`flags a painter only past ${PAINTER_CAP} works`, () => {
		const at = Array.from({ length: PAINTER_CAP }, (_, i) => cover(`w${i}`, 'painting', { artist: 'Cap' }));
		expect(coverFlags(at[0], painterWorks(at))).not.toContain('painter');
		const over = [...at, cover('extra', 'painting', { artist: 'Cap' })];
		expect(coverFlags(over[0], painterWorks(over))).toContain('painter');
	});

	it('flags a heavy scrim on a framed cover, never on a laid-out one', () => {
		const heavy = Object.entries(COVER_SCRIM).find(([, v]) => v >= 0.85)?.[0];
		expect(heavy, 'some framed cover carries a heavy scrim').toBeDefined();
		expect(coverFlags(cover(heavy!, 'painting'), new Map())).toContain('scrim');
		// The same slug under an author with a layout has no scrim to flag.
		const laidOut = Object.keys(AUTHOR_LAYOUT)[0];
		expect(coverFlags(cover(heavy!, 'painting', { author: laidOut }), new Map())).not.toContain('scrim');
	});

	it('leaves a designed cover alone', () => {
		expect(coverFlags(cover('d', 'designed'), new Map())).toEqual([]);
	});
});

describe('groupCovers', () => {
	const wall = [
		cover('a', 'painting', { artist: 'Inness', author: 'zed' }),
		cover('b', 'painting', { artist: 'Inness', author: 'amy' }),
		cover('c', 'painting', { artist: 'Church', author: 'amy' }),
		cover('d', 'plate', { author: 'amy' })
	];

	it('leads the painter view with the most-used painter, non-paintings last', () => {
		expect(groupCovers(wall, 'painter').map((s) => s.label)).toEqual(['Inness', 'Church', 'Not a museum painting']);
	});

	it('puts plates first in the tier view', () => {
		expect(groupCovers(wall, 'tier')[0].key).toBe('plate');
	});

	it('orders by measured hue, unmeasured last', () => {
		const hues = new Map([
			['c|en', 200],
			['a|en', 20]
		]);
		expect(groupCovers(wall, 'colour', hues)[0].covers.map((c) => c.slug)).toEqual(['a', 'c', 'b', 'd']);
	});
});

describe('hueOf', () => {
	it('reads primaries and parks greys at the end', () => {
		expect(hueOf(255, 0, 0)).toBe(0);
		expect(hueOf(0, 255, 0)).toBe(120);
		expect(hueOf(0, 0, 255)).toBe(240);
		expect(hueOf(128, 128, 130)).toBe(999);
	});
});
