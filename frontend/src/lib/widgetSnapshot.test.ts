import { describe, expect, it } from 'vitest';
import {
	WIDGET_SNAPSHOT_VERSION,
	buildWidgetSnapshot,
	dateOfKey,
	dayKeys,
	mergeVerses,
	pickVerseDay,
	widgetCoverUrl,
	type SnapshotInput,
	type WidgetVerse
} from './widgetSnapshot';
import type { ResumeBook } from './resumeItems';

const verse = (date: string, text = `v ${date}`): WidgetVerse => ({ date, text, ref: 'Ps 121:3', lang: 'en' });

describe('dayKeys', () => {
	it('lists the local dates from today on', () => {
		expect(dayKeys(new Date(2026, 10, 12, 23, 59), 3)).toEqual(['2026-11-12', '2026-11-13', '2026-11-14']);
	});

	it('crosses month and year ends', () => {
		expect(dayKeys(new Date(2026, 11, 31, 0, 1), 2)).toEqual(['2026-12-31', '2027-01-01']);
		expect(dayKeys(new Date(2028, 1, 28, 8), 2)).toEqual(['2028-02-28', '2028-02-29']);
	});

	it('round-trips through dateOfKey on the same local day', () => {
		for (const key of dayKeys(new Date(2026, 2, 28), 4)) expect(dayKeys(dateOfKey(key), 1)).toEqual([key]);
	});
});

describe('pickVerseDay (the widgets’ midnight rule)', () => {
	const verses = [verse('2026-11-12'), verse('2026-11-13'), verse('2026-11-14')];

	it('shows the verse dated today', () => {
		expect(pickVerseDay(verses, '2026-11-13')).toEqual({ verse: verses[1], stale: false });
	});

	it('past the last stored day, keeps the last verse but claims no date', () => {
		expect(pickVerseDay(verses, '2026-11-20')).toEqual({ verse: verses[2], stale: true });
	});

	it('fills a gap with the latest earlier verse, undated', () => {
		const gappy = [verse('2026-11-12'), verse('2026-11-14')];
		expect(pickVerseDay(gappy, '2026-11-13')).toEqual({ verse: gappy[0], stale: true });
	});

	it('shows nothing before the first verse or with none', () => {
		expect(pickVerseDay(verses, '2026-11-01')).toBeNull();
		expect(pickVerseDay([], '2026-11-12')).toBeNull();
	});
});

describe('mergeVerses', () => {
	it('drops past days, adds new ones, one per date, oldest first', () => {
		const stored = [verse('2026-11-11'), verse('2026-11-12', 'old'), verse('2026-11-13')];
		const fresh = [verse('2026-11-14'), verse('2026-11-12', 'new')];
		expect(mergeVerses(stored, fresh, '2026-11-12').map((v) => [v.date, v.text])).toEqual([
			['2026-11-12', 'new'],
			['2026-11-13', 'v 2026-11-13'],
			['2026-11-14', 'v 2026-11-14']
		]);
	});

	it('with nothing current, keeps the latest verse to show undated', () => {
		const stored = [verse('2026-11-01'), verse('2026-11-03')];
		expect(mergeVerses(stored, [], '2026-11-12')).toEqual([stored[1]]);
		expect(mergeVerses([], [], '2026-11-12')).toEqual([]);
	});
});

describe('widgetCoverUrl', () => {
	it('points a raster cover at its small webp on the website', () => {
		expect(widgetCoverUrl('/covers/art/humility.jpg', 'https://ochorus.com/')).toBe(
			'https://ochorus.com/covers/art/humility-320.webp'
		);
	});

	it('has none for a plate, an outside URL or no cover', () => {
		expect(widgetCoverUrl('/covers/humility.en.svg', 'https://ochorus.com')).toBeNull();
		expect(widgetCoverUrl('https://example.org/x.jpg', 'https://ochorus.com')).toBeNull();
		expect(widgetCoverUrl(null, 'https://ochorus.com')).toBeNull();
	});
});

describe('buildWidgetSnapshot', () => {
	const book = {
		kind: 'book',
		slug: 'all-of-grace',
		key: 'all-of-grace',
		href: '/books/all-of-grace/13',
		title: 'Toda gracia',
		author: 'C. H. Spurgeon',
		finished: false,
		pct: 64.6,
		order: 13,
		chapterCount: 20,
		book: { language: 'es', cover_url: '/covers/art/all-of-grace.jpg', cover_color: '#3f3d9a' }
	} as unknown as ResumeBook;

	const input = (over: Partial<SnapshotInput> = {}): SnapshotInput => ({
		locale: 'es',
		rtl: false,
		siteUrl: 'https://ochorus.com',
		localize: (p) => `/es${p === '/' ? '' : p}/`,
		strings: {
			today: 'Versículo de hoy',
			continue: 'Seguir leyendo',
			start: 'Empieza a leer',
			chapterOf: 'Capítulo {order} de {total}'
		},
		verses: [verse('2026-11-12')],
		book,
		...over
	});

	it('carries localised words, absolute links and the book', () => {
		const snap = buildWidgetSnapshot(input());
		expect(snap.v).toBe(WIDGET_SNAPSHOT_VERSION);
		expect(snap.labels).toEqual({ today: 'Versículo de hoy', continue: 'Seguir leyendo', start: 'Empieza a leer' });
		expect(snap.urls).toEqual({
			today: 'https://ochorus.com/es/today/',
			home: 'https://ochorus.com/es/',
			books: 'https://ochorus.com/es/books/'
		});
		expect(snap.book).toEqual({
			title: 'Toda gracia',
			author: 'C. H. Spurgeon',
			chapter: 'Capítulo 13 de 20',
			pct: 65,
			url: 'https://ochorus.com/es/books/all-of-grace/13/',
			coverUrl: 'https://ochorus.com/covers/art/all-of-grace-320.webp',
			coverColor: '#3f3d9a',
			lang: 'es',
			description: 'Seguir leyendo: Toda gracia, C. H. Spurgeon. Capítulo 13 de 20, 65%'
		});
	});

	it('has no book, and no colour it cannot parse', () => {
		expect(buildWidgetSnapshot(input({ book: null })).book).toBeNull();
		const odd = { ...book, book: { ...book.book, cover_color: 'var(--x)' } } as ResumeBook;
		expect(buildWidgetSnapshot(input({ book: odd })).book?.coverColor).toBeNull();
	});

	it('says which way the language runs', () => {
		expect(buildWidgetSnapshot(input({ locale: 'ar', rtl: true })).rtl).toBe(true);
	});

	it('holds nothing private beyond the book shown', () => {
		const json = JSON.stringify(buildWidgetSnapshot(input()));
		expect(json).not.toMatch(/token|email|session/i);
	});
});
