import { beforeEach, describe, expect, it } from 'vitest';
import { marks } from './marks.svelte';
import {
	MARKS_KEY,
	ANCHOR_KEY,
	LEGACY_SERMON_MARKS_KEY,
	LEGACY_SERMON_ANCHOR_KEY,
	SERMON_CHAPTER_ORDER
} from './reading-schema';
import { getScrollAnchor } from './progress';

beforeEach(() => localStorage.clear());

describe('sermon marks via the unified store (kind="sermon")', () => {
	it('adds a selection as one group, toggles and removes it', () => {
		marks.load('faith', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		const id = marks.add([
			{ p: 0, s: 0, e: 5 },
			{ p: 1, s: 0, e: 3 }
		]);
		expect(id).toBeTruthy();
		expect(marks.list).toHaveLength(2);
		expect(marks.groupCovering([{ p: 0, s: 0, e: 5 }, { p: 1, s: 0, e: 3 }])).toBe(id);

		marks.remove(id);
		expect(marks.list).toHaveLength(0);
	});

	it('keeps a sermon and a book with the same slug apart', () => {
		marks.load('free-grace', 1, 'en', 'book');
		marks.add([{ p: 0, s: 0, e: 2 }]);
		marks.load('free-grace', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		expect(marks.list).toHaveLength(0); // the book's mark doesn't bleed over
		marks.add([{ p: 3, s: 0, e: 4 }]);

		const all = marks.all('en');
		expect(new Set(all.map((m) => `${m.kind}:${m.slug}`))).toEqual(
			new Set(['book:free-grace', 'sermon:free-grace'])
		);
	});

	it('scopes marks per sermon slug and persists across loads', () => {
		marks.load('a', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		marks.add([{ p: 0, s: 0, e: 2 }]);
		marks.load('b', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		expect(marks.list).toHaveLength(0); // b has none
		marks.load('a', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		expect(marks.list).toHaveLength(1); // a's mark survived
	});

	it('migrates the legacy device-local sermon stores once', () => {
		localStorage.setItem(
			LEGACY_SERMON_MARKS_KEY,
			JSON.stringify({ faith: [{ id: 'x', p: 2, s: 0, e: 5 }] })
		);
		localStorage.setItem(LEGACY_SERMON_ANCHOR_KEY, JSON.stringify({ faith: 7 }));

		marks.load('faith', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		expect(marks.list).toHaveLength(1);
		expect(marks.list[0].p).toBe(2);
		expect(localStorage.getItem(LEGACY_SERMON_MARKS_KEY)).toBeNull();

		expect(getScrollAnchor('faith', SERMON_CHAPTER_ORDER, 'sermon')).toBe(7);
		expect(localStorage.getItem(LEGACY_SERMON_ANCHOR_KEY)).toBeNull();

		// Folded into the unified keys, not lost.
		expect(JSON.parse(localStorage.getItem(MARKS_KEY)!)['sermon:faith:1']).toBeTruthy();
		expect(JSON.parse(localStorage.getItem(ANCHOR_KEY)!)['sermon:faith:1']).toBe(7);
	});
});

describe('deletion tombstones (cross-device loss #1)', () => {
	it('records a tombstone for a removed mark and retains the entry', () => {
		marks.load('humility', 2, 'en', 'book');
		const id = marks.add([{ p: 0, s: 0, e: 5 }]);
		marks.remove(id);
		const entry = JSON.parse(localStorage.getItem(MARKS_KEY)!)['humility:2'];
		// The entry survives even with no marks left, so the tombstone can ride on
		// the next sync and stop a stale device resurrecting the highlight.
		expect(entry).toBeTruthy();
		expect(entry.m).toHaveLength(0);
		expect(Object.keys(entry.d)).toContain(id);
	});

	it('does not tombstone on a plain add', () => {
		marks.load('humility', 4, 'en', 'book');
		marks.add([{ p: 0, s: 0, e: 5 }]);
		const entry = JSON.parse(localStorage.getItem(MARKS_KEY)!)['humility:4'];
		expect(entry.d).toBeUndefined();
	});
});

describe('note lifecycle on the unified store', () => {
	it('round-trips a note through setNote/getNote and clears it', () => {
		marks.load('faith', SERMON_CHAPTER_ORDER, 'en', 'sermon');
		const id = marks.add([{ p: 2, s: 1, e: 4 }], 'a thought');
		expect(marks.getNote(id)).toBe('a thought');
		marks.setNote(id, 'revised');
		expect(marks.getNote(id)).toBe('revised');
		marks.setNote(id, '');
		expect(marks.getNote(id)).toBe('');
	});
});

describe('editions share a chapter but not a text (#1085)', () => {
	// The Modern English edition of a book has the same slug and the same
	// chapter order as the original, and different words. `{p, s, e}` offsets
	// index one of those texts, so a mark has to say which.

	it('does not show the original edition’s highlight on the modern text', () => {
		marks.load('humility', 3, 'en', 'book');
		marks.add([{ p: 0, s: 10, e: 20 }]);
		expect(marks.list).toHaveLength(1);

		marks.load('humility', 3, 'en-modern', 'book');
		expect(marks.list).toHaveLength(0);
	});

	it('does not let a removal in one edition delete the other’s mark', () => {
		marks.load('humility', 3, 'en', 'book');
		const original = marks.add([{ p: 0, s: 10, e: 20 }]);

		marks.load('humility', 3, 'en-modern', 'book');
		const modern = marks.add([{ p: 0, s: 10, e: 20 }]); // same offsets, other text
		marks.remove(modern);
		expect(marks.list).toHaveLength(0);

		marks.load('humility', 3, 'en', 'book');
		expect(marks.list.map((m) => m.id)).toEqual([original]);
	});

	it('keeps both editions in storage through a write from either', () => {
		marks.load('humility', 3, 'en', 'book');
		marks.add([{ p: 1, s: 0, e: 4 }]);
		marks.load('humility', 3, 'en-modern', 'book');
		marks.add([{ p: 2, s: 0, e: 4 }]);

		// One entry, both editions, each tagged with the text it was measured on.
		const stored = JSON.parse(localStorage.getItem(MARKS_KEY)!)['humility:3'].m;
		expect(stored.map((m: { lang: string }) => m.lang).sort()).toEqual(['en', 'en-modern']);
	});

	it('separates the same book’s languages too', () => {
		marks.load('humility', 1, 'en', 'book');
		marks.add([{ p: 0, s: 0, e: 8 }]);
		marks.load('humility', 1, 'es', 'book');
		expect(marks.list).toHaveLength(0);
	});

	it('keeps untagged legacy marks in the base edition, out of the modern one', () => {
		// Everything written before editions were tagged was made against the
		// reader's plain content language. Hiding those would be a worse bug than
		// the one being fixed, so the base edition still shows them.
		localStorage.setItem(
			MARKS_KEY,
			JSON.stringify({ 'humility:2': { m: [{ id: 'old', p: 0, s: 0, e: 5 }] } })
		);

		marks.load('humility', 2, 'en', 'book');
		expect(marks.list.map((m) => m.id)).toEqual(['old']);

		marks.load('humility', 2, 'en-modern', 'book');
		expect(marks.list).toHaveLength(0);
	});

	it('survives a legacy mark being carried across a modern-edition write', () => {
		localStorage.setItem(
			MARKS_KEY,
			JSON.stringify({ 'humility:2': { m: [{ id: 'old', p: 0, s: 0, e: 5 }] } })
		);
		marks.load('humility', 2, 'en-modern', 'book');
		marks.add([{ p: 9, s: 0, e: 3 }]);

		marks.load('humility', 2, 'en', 'book');
		expect(marks.list.map((m) => m.id)).toEqual(['old']);
	});

	it('counts marks per edition for the TOC', () => {
		marks.load('humility', 4, 'en', 'book');
		marks.add([{ p: 0, s: 0, e: 2 }]);
		marks.add([{ p: 1, s: 0, e: 2 }]);
		marks.load('humility', 4, 'en-modern', 'book');
		marks.add([{ p: 5, s: 0, e: 2 }]);

		expect(marks.countFor('humility', 4, 'book', 'en')).toBe(2);
		expect(marks.countFor('humility', 4, 'book', 'en-modern')).toBe(1);
	});

	it('gives the notebook only the edition whose text it fetches', () => {
		marks.load('humility', 6, 'es', 'book');
		marks.add([{ p: 0, s: 0, e: 2 }]);
		marks.load('humility', 6, 'en', 'book');
		marks.add([{ p: 3, s: 0, e: 2 }]);

		expect(marks.all('es').flatMap((w) => w.marks).map((m) => m.p)).toEqual([0]);
		expect(marks.all('en').flatMap((w) => w.marks).map((m) => m.p)).toEqual([3]);
	});
});

describe('allByEdition — every edition, each exactly once (#1120)', () => {
	// The notebook quotes each highlight against the text it was measured on, so
	// it needs the editions, not one of them. Asking `all()` once per edition
	// would not do: an untagged mark counts as the base edition of whatever it
	// is asked about, so it would come back under every language enumerated.

	it('splits one chapter’s marks by the edition each was made in', () => {
		marks.load('humility', 3, 'en', 'book');
		marks.add([{ p: 0, s: 0, e: 5 }]);
		marks.load('humility', 3, 'en-modern', 'book');
		marks.add([{ p: 1, s: 0, e: 5 }]);

		const groups = marks.allByEdition('en');
		expect(groups).toHaveLength(2);
		expect(groups.map((g) => g.edition).sort()).toEqual(['en', 'en-modern']);
		expect(groups.every((g) => g.slug === 'humility' && g.order === 3)).toBe(true);
	});

	it('places an untagged mark in the base edition, once', () => {
		localStorage.setItem(
			MARKS_KEY,
			JSON.stringify({ 'humility:2': { m: [{ id: 'old', p: 0, s: 0, e: 5 }] } })
		);

		const groups = marks.allByEdition('en');
		expect(groups).toHaveLength(1);
		expect(groups[0].edition).toBe('en');
		expect(groups[0].marks.map((m) => m.id)).toEqual(['old']);
	});

	it('does not repeat an untagged mark across the editions on offer', () => {
		// The failure mode of enumerating editions and calling `all()` per one.
		localStorage.setItem(
			MARKS_KEY,
			JSON.stringify({
				'humility:2': { m: [{ id: 'old', p: 0, s: 0, e: 5 }, { id: 'es1', p: 1, s: 0, e: 5, lang: 'es' }] }
			})
		);

		const groups = marks.allByEdition('en');
		const ids = groups.flatMap((g) => g.marks.map((m) => m.id)).sort();
		expect(ids).toEqual(['es1', 'old']);
		expect(groups.find((g) => g.edition === 'en')!.marks.map((m) => m.id)).toEqual(['old']);
		expect(groups.find((g) => g.edition === 'es')!.marks.map((m) => m.id)).toEqual(['es1']);
	});

	it('reads an untagged mark as the base edition when the reader is on modern', () => {
		// `baseEdition('en-modern')` is 'en', so the legacy mark stays where it
		// was made and does not migrate onto the modern text.
		localStorage.setItem(
			MARKS_KEY,
			JSON.stringify({ 'humility:2': { m: [{ id: 'old', p: 0, s: 0, e: 5 }] } })
		);
		expect(marks.allByEdition('en-modern')[0].edition).toBe('en');
	});

	it('carries kind and order through for each group', () => {
		marks.load('faith', SERMON_CHAPTER_ORDER, 'es', 'sermon');
		marks.add([{ p: 0, s: 0, e: 4 }]);

		const [g] = marks.allByEdition('en');
		expect(g).toMatchObject({ kind: 'sermon', slug: 'faith', order: SERMON_CHAPTER_ORDER, edition: 'es' });
	});
});
