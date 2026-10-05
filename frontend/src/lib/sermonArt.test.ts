import { describe, expect, it } from 'vitest';
import { sermonArt, sermonCoverFace } from './sermonArt';
import { channels, contrastRatio, inkSafe, INK_MIN_CONTRAST, tintable } from './coverArt';
import { isSermonTile, type TopicCover } from './library-public';
import { EMBLEM_HUES } from './emblemHues';
import { emblemForSermon } from './emblemNames';

describe('sermonArt', () => {
	it('pairs the emblem with a hue that can actually tint', () => {
		// The pairing is the point: the raw catalogue hue for the raven is dark
		// enough to read as untinted through a 9% wash, so it must come back
		// lifted, not raw.
		const raw = EMBLEM_HUES[emblemForSermon('the-ravens-cry')];
		const art = sermonArt('the-ravens-cry');
		expect(art.emblem).toBe('ravens-bread');
		expect(art.hue).not.toBe(raw);
		expect(art.hue).toMatch(/^#[0-9a-f]{6}$/i);
	});

	it('gives an uncurated slug real art rather than nothing', () => {
		// New sermons land before anyone picks an emblem; the fallback is a
		// stable hash pick, so a fresh slug still draws.
		const art = sermonArt('a-sermon-nobody-has-curated');
		expect(art.emblem).toBeTruthy();
		expect(art.hue).toMatch(/^#[0-9a-f]{6}$/i);
	});
});

describe('isSermonTile', () => {
	const book: TopicCover = {
		kind: 'book',
		slug: 'all-of-grace',
		cover_url: '/covers/all-of-grace.svg',
		cover_color: '#b8912f',
		title: 'All of Grace'
	};
	const sermon: TopicCover = { kind: 'sermon', slug: 'the-ravens-cry', title: "The Ravens' Cry" };

	it('separates the two tile kinds', () => {
		expect(isSermonTile(sermon)).toBe(true);
		expect(isSermonTile(book)).toBe(false);
	});

	it('reads a tile with no kind as a book', () => {
		// A payload predating the sermon tile — every tile in it is a book.
		const legacy = { cover_url: '', cover_color: '#123456', title: 'Old' } as TopicCover;
		expect(isSermonTile(legacy)).toBe(false);
	});

	it('narrows, so the sermon branch has a slug without a fallback', () => {
		const tile: TopicCover = sermon;
		if (isSermonTile(tile)) {
			// Type-level assertion as much as a runtime one: `tile.slug` here is
			// `string`, which is what removes the `?? ''` at the call site.
			expect(sermonArt(tile.slug).emblem).toBe('ravens-bread');
		} else {
			throw new Error('expected a sermon tile');
		}
	});
});

describe('sermonCoverFace', () => {
	// White type sits on the ribbed base of the plate's gradient (its lightest
	// point), so that is where every emblem's hue must clear AA once floored.
	// `tintable` lifts the gold emblems to ~2.8:1 there, which is why the
	// floor exists; this fails if a new emblem hue slips past it.
	const RIB = 0.959;
	it.each(Object.entries(EMBLEM_HUES))('floors the %s hue so white type clears AA', (_, hue) => {
		const safe = channels(inkSafe(tintable(hue))).map((c) => c * RIB);
		expect(contrastRatio([255, 255, 255], safe)).toBeGreaterThanOrEqual(INK_MIN_CONTRAST);
	});

	it('leaves a colour that already passes untouched', () => {
		expect(inkSafe('#1f2a44')).toBe('#1f2a44');
	});

	it("namespaces the slug so a book's per-slug tables never match a sermon", () => {
		const face = sermonCoverFace({
			slug: 'power-in-prayer',
			language: 'en',
			title: 'Power in Prayer',
			scripture_ref: 'James 5:16',
			scripture_book: null,
			scripture_book_order: null,
			summary: '',
			preached_on: null,
			word_count: 1,
			author: { slug: 'torrey', name: 'R. A. Torrey', bio: '', photo_url: '', birth_year: 1856, death_year: 1928 },
			topics: [],
			created_at: ''
		});
		expect(face.slug).toBe('sermon:power-in-prayer');
		expect(face.cover_url).toBe('');
		expect(face.subtitle).toBe('James 5:16');
		expect(face.cover_color).toBe(inkSafe(sermonArt('power-in-prayer').hue));
	});
});
