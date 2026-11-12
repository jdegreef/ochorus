import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PROGRESS_KEY, RESUME_BOOKS_KEY } from './reading-schema';
import { SCHEMA } from './resumeBooks';

// The native side stood in for: what the app hands the phone, and when.
const m = vi.hoisted(() => ({
	setWidgetSnapshot: vi.fn(async (_json: string) => true),
	loadDayVerse: vi.fn(async (day: Date, _lang: string) => ({
		text: `verse ${day.getDate()}`,
		ref: `Ps 1:${day.getDate()} · OWB`,
		lang: 'en'
	}))
}));
vi.mock('$lib/platform', () => ({ setWidgetSnapshot: m.setWidgetSnapshot }));
vi.mock('$lib/todayPicks', () => ({ loadDayVerse: m.loadDayVerse }));

import { WIDGET_VERSES_KEY, syncWidgets, widgetBook, widgetVerses } from './widgetSync';
import type { WidgetSnapshot } from './widgetSnapshot';

const NOV_12 = new Date(2026, 10, 12, 9);
const lastSnapshot = (): WidgetSnapshot =>
	JSON.parse(m.setWidgetSnapshot.mock.calls.at(-1)![0]) as WidgetSnapshot;

function readBook(slug: string, order: number) {
	localStorage.setItem(
		PROGRESS_KEY,
		JSON.stringify({ [slug]: { order, paragraph_index: 4, language: 'en', at: 1, finished_at: null, furthest: order } })
	);
	localStorage.setItem(
		RESUME_BOOKS_KEY,
		JSON.stringify({
			schema: SCHEMA,
			books: {
				en: [
					{
						slug,
						language: 'en',
						title: 'All of Grace',
						cover_url: '/covers/art/all-of-grace.jpg',
						cover_color: '#3f3d9a',
						chapter_count: 20,
						has_modern_edition: false,
						author: { slug: 'spurgeon', name: 'C. H. Spurgeon', birth_year: 1834 }
					}
				]
			},
			absent: {}
		})
	);
}

beforeEach(() => {
	localStorage.clear();
	m.setWidgetSnapshot.mockClear();
	m.loadDayVerse.mockClear();
});

describe('widgetVerses', () => {
	it('fetches the next three days once, then only the new day', async () => {
		const first = await widgetVerses(NOV_12, 'en');
		expect(first.map((v) => v.date)).toEqual(['2026-11-12', '2026-11-13', '2026-11-14']);
		expect(m.loadDayVerse).toHaveBeenCalledTimes(3);

		m.loadDayVerse.mockClear();
		const next = await widgetVerses(new Date(2026, 10, 13, 0, 5), 'en');
		expect(next.map((v) => v.date)).toEqual(['2026-11-13', '2026-11-14', '2026-11-15']);
		expect(m.loadDayVerse).toHaveBeenCalledTimes(1);
		expect(JSON.parse(localStorage.getItem(WIDGET_VERSES_KEY)!).verses).toHaveLength(3);
	});

	it('asks a day with no verse once per launch, not on every sync', async () => {
		m.loadDayVerse.mockResolvedValue(null as never);
		await widgetVerses(NOV_12, 'lg');
		await widgetVerses(NOV_12, 'lg');
		expect(m.loadDayVerse).toHaveBeenCalledTimes(3);
		m.loadDayVerse.mockReset();
	});

	it('starts again in another language', async () => {
		localStorage.setItem(
			WIDGET_VERSES_KEY,
			JSON.stringify({ lang: 'en', verses: [{ date: '2026-11-12', text: 'x', ref: 'y', lang: 'en' }] })
		);
		m.loadDayVerse.mockImplementation(async (day: Date) => ({ text: `v${day.getDate()}`, ref: 'r', lang: 'es' }));
		const verses = await widgetVerses(NOV_12, 'es');
		expect(verses.every((v) => v.lang === 'es')).toBe(true);
	});
});

describe('widgetBook', () => {
	it('is the book the reader is in, from the device cache', () => {
		readBook('all-of-grace', 13);
		expect(widgetBook('en')).toMatchObject({ slug: 'all-of-grace', order: 13, chapterCount: 20 });
	});

	it('is null with nothing in progress, or a book the cache lacks', () => {
		expect(widgetBook('en')).toBeNull();
		readBook('all-of-grace', 2);
		localStorage.removeItem(RESUME_BOOKS_KEY);
		expect(widgetBook('en')).toBeNull();
	});
});

describe('syncWidgets', () => {
	it('sends the snapshot, and again only when it changed', async () => {
		readBook('all-of-grace', 13);
		await syncWidgets(NOV_12);
		expect(m.setWidgetSnapshot).toHaveBeenCalledTimes(1);
		const snap = lastSnapshot();
		expect(snap.book).toMatchObject({ title: 'All of Grace', author: 'C. H. Spurgeon' });
		expect(snap.book!.url).toMatch(/\/books\/all-of-grace\/13\/$/);
		expect(snap.urls.today).toMatch(/^https:\/\/.*\/today\/?$/);

		await syncWidgets(NOV_12);
		expect(m.setWidgetSnapshot).toHaveBeenCalledTimes(1);

		readBook('all-of-grace', 14);
		await syncWidgets(NOV_12);
		expect(m.setWidgetSnapshot).toHaveBeenCalledTimes(2);
		expect(lastSnapshot().book!.chapter).toContain('14');
	});

	it('tries again next time when the phone did not take it', async () => {
		m.setWidgetSnapshot.mockResolvedValueOnce(false);
		await syncWidgets(new Date(2026, 10, 20));
		await syncWidgets(new Date(2026, 10, 20));
		expect(m.setWidgetSnapshot).toHaveBeenCalledTimes(2);
	});
});
