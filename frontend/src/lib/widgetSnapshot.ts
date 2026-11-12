// The home-screen widgets' data (design #46): what the app hands the phone so
// its two native widgets — Today (the day's verse) and Continue (the book the
// reader is in) — can draw without the app running. Pure, so the contract the
// Android and iOS widgets read is pinned by tests here; $lib/widgetSync gathers
// the inputs and sends the JSON through $lib/platform.
//
// The snapshot carries words already in the reader's language (the widgets
// translate nothing) and nothing private beyond what the widget shows: no
// token, no account, no other book. See frontend/MOBILE.md, "Home-screen
// widgets", for how each platform reads it.
//
// MIDNIGHT. The Today widget must turn over at local midnight even when the app
// was not opened that day, so the snapshot holds the verses of the next
// `VERSE_DAYS` local dates, each tagged with its date. The widget shows the one
// dated today; past the last one it keeps showing the last one but drops the
// "Verse for today" eyebrow (`pickVerseDay`'s `stale`) — an old verse with no
// date claimed, never a verse under the wrong date.

import { coverVariants } from './coverArt';
import { baseEdition } from './reading-schema';
import { localToday } from './streak';
import type { ResumeBook } from './resumeItems';

/** Bump when the shape changes; a widget seeing another version shows its placeholder. */
export const WIDGET_SNAPSHOT_VERSION = 1;

/** How many local days of verses the snapshot carries (today included). */
export const VERSE_DAYS = 3;

/** One day's verse: `date` is the reader's local `YYYY-MM-DD`. */
export type WidgetVerse = { date: string; text: string; ref: string; lang: string };

export type WidgetBook = {
	title: string;
	author: string;
	/** "Chapter 3 of 12", in the reader's language. */
	chapter: string;
	/** 0–100. */
	pct: number;
	/** Absolute https link to the chapter — the app opens it in place. */
	url: string;
	/** A small raster of the cover on the website, or null (a plate, no file). */
	coverUrl: string | null;
	/** The cover's colour, for a widget with no cover image. */
	coverColor: string | null;
	/** The book's language (its title may be in another script than the UI). */
	lang: string;
	/** What a screen reader says for the whole widget. */
	description: string;
};

export type WidgetSnapshot = {
	v: typeof WIDGET_SNAPSHOT_VERSION;
	/** The UI locale the labels are in, and whether it is written right to left. */
	locale: string;
	rtl: boolean;
	labels: {
		/** Eyebrow over the day's verse ("Verse for today"). */
		today: string;
		/** Eyebrow over the book ("Continue reading"). */
		continue: string;
		/** The call to action with nothing to show ("Start reading"). */
		start: string;
	};
	/** Where each widget opens (absolute https, localised). */
	urls: { today: string; home: string; books: string };
	/** The next VERSE_DAYS days' verses, oldest first; [] when the language has no devotionals. */
	verses: WidgetVerse[];
	/** The book the reader is in; null when none. */
	book: WidgetBook | null;
};

/** The reader's local `YYYY-MM-DD` for `now` and the `count - 1` days after it. */
export function dayKeys(now: Date, count = VERSE_DAYS): string[] {
	// Noon, so a zone whose clocks jump at midnight cannot skip or repeat a date.
	return Array.from({ length: count }, (_, i) =>
		localToday(new Date(now.getFullYear(), now.getMonth(), now.getDate() + i, 12))
	);
}

/** A `YYYY-MM-DD` key as a local Date (noon), for the day's shelf. */
export function dateOfKey(key: string): Date {
	const [y, m, d] = key.split('-').map(Number);
	return new Date(y, m - 1, d, 12);
}

/**
 * Which stored verse the Today widget shows on `today` (`YYYY-MM-DD`): the one
 * dated today; else the latest before today, `stale` (shown without the
 * "today" eyebrow); else none — a clock set back before the first one, or no
 * verses at all. THE CONTRACT the native widgets implement (Android's
 * `VersePicker`, iOS's `pickVerse`) — keep the three in step.
 */
export function pickVerseDay<T extends { date: string }>(
	verses: readonly T[],
	today: string
): { verse: T; stale: boolean } | null {
	let best: T | null = null;
	for (const v of verses) {
		if (v.date === today) return { verse: v, stale: false };
		if (v.date < today && (!best || v.date > best.date)) best = v;
	}
	return best ? { verse: best, stale: true } : null;
}

/**
 * Keep the stored verses the snapshot still needs — today's and later, or,
 * when there is none of those, the latest one (still worth showing, undated) —
 * merged with freshly loaded ones, one per date, oldest first.
 */
export function mergeVerses(stored: WidgetVerse[], fresh: WidgetVerse[], today: string): WidgetVerse[] {
	const byDate = new Map<string, WidgetVerse>();
	for (const v of [...stored, ...fresh]) byDate.set(v.date, v);
	const all = [...byDate.values()].sort((a, b) => (a.date < b.date ? -1 : 1));
	const current = all.filter((v) => v.date >= today);
	return current.length ? current : all.slice(-1);
}

/**
 * The cover the widget draws: the small webp beside a raster cover on the
 * website (the reader's covers are not bundled in the app), or null for a
 * plate (an SVG ground the widget cannot draw — it shows `coverColor`).
 */
export function widgetCoverUrl(coverUrl: string | null | undefined, siteUrl: string): string | null {
	const [small] = coverVariants(coverUrl);
	return small ? `${siteUrl.replace(/\/+$/, '')}${small}` : null;
}

export type SnapshotInput = {
	locale: string;
	rtl: boolean;
	siteUrl: string;
	/** Locale-prefix a site path (`$lib/href`'s localizeHref). */
	localize: (path: string) => string;
	/** UI strings, already in `locale`. `chapterOf` keeps `{order}` / `{total}`. */
	strings: { today: string; continue: string; start: string; chapterOf: string };
	verses: WidgetVerse[];
	book: ResumeBook | null;
};

export function buildWidgetSnapshot(input: SnapshotInput): WidgetSnapshot {
	const { strings, book } = input;
	const site = input.siteUrl.replace(/\/+$/, '');
	const url = (path: string) => `${site}${input.localize(path)}`;
	let widgetBook: WidgetBook | null = null;
	if (book) {
		const chapter = strings.chapterOf
			.replace('{order}', String(book.order))
			.replace('{total}', String(book.chapterCount));
		widgetBook = {
			title: book.title,
			author: book.author,
			chapter,
			pct: Math.max(0, Math.min(100, Math.round(book.pct))),
			url: url(book.href),
			coverUrl: widgetCoverUrl(book.book.cover_url, site),
			coverColor: /^#[0-9a-f]{6}$/i.test(book.book.cover_color ?? '') ? book.book.cover_color : null,
			lang: baseEdition(book.book.language),
			description: `${strings.continue}: ${book.title}, ${book.author}. ${chapter}, ${Math.round(book.pct)}%`
		};
	}
	return {
		v: WIDGET_SNAPSHOT_VERSION,
		locale: input.locale,
		rtl: input.rtl,
		labels: { today: strings.today, continue: strings.continue, start: strings.start },
		urls: { today: url('/today'), home: url('/'), books: url('/books') },
		verses: input.verses,
		book: widgetBook
	};
}
