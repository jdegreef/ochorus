// Keeps the phone's home-screen widgets (Today, Continue) fed — app only. The
// root layout imports this behind `IS_APP` (a dynamic import of a
// build-time-dead branch), so the website ships none of it.
//
// It builds the snapshot ($lib/widgetSnapshot) from what the reader already
// has on the device — the day's verse as the Today card picks it, and the book
// the home hero resumes — and hands it to the native side through
// $lib/platform, but only when it changed. The native widgets redraw from it,
// and roll the verse over at midnight on their own (see MOBILE.md).

import { setWidgetSnapshot } from '$lib/platform';
import { SITE_URL } from '$lib/config';
import { getLang } from '$lib/lang.svelte';
import { i18n } from '$lib/i18n.svelte';
import { localizeHref } from '$lib/href';
import { getLocale, getTextDirection } from '$lib/paraglide/runtime';
import { allProgress } from '$lib/progress';
import { resumeBookOf, type ResumeBook } from '$lib/resumeItems';
import { cachedResumeBooks, currentBookSlug, knownAbsent, libraryBooks } from '$lib/resumeBooks';
import { localToday } from '$lib/streak';
import { loadDayVerse } from '$lib/todayPicks';
import { watchToday } from '$lib/today';
import {
	buildWidgetSnapshot,
	dateOfKey,
	dayKeys,
	mergeVerses,
	type WidgetVerse
} from '$lib/widgetSnapshot';

/** The verses already fetched, per language: no personal data, so not in the sign-out wipe. */
export const WIDGET_VERSES_KEY = 'ochorus:widget-verses';

type StoredVerses = { lang: string; verses: WidgetVerse[] };

function readVerses(lang: string): WidgetVerse[] {
	try {
		const stored = JSON.parse(localStorage.getItem(WIDGET_VERSES_KEY) || 'null') as StoredVerses | null;
		return stored?.lang === lang && Array.isArray(stored.verses) ? stored.verses : [];
	} catch {
		return [];
	}
}

function writeVerses(lang: string, verses: WidgetVerse[]): void {
	try {
		localStorage.setItem(WIDGET_VERSES_KEY, JSON.stringify({ lang, verses } satisfies StoredVerses));
	} catch {
		/* blocked storage: the next sync fetches again */
	}
}

/** When each day was last asked for and got nothing, so a language with no
 *  devotional (or an API that is down) costs a try every RETRY_MS, not one
 *  per sync. A day that got its verse is stored, and never asked again. */
const asked = new Map<string, number>();
const RETRY_MS = 30 * 60_000;

/**
 * The next few days' verses: the stored ones, plus any day not yet stored
 * (normally just the newest, once a day — the shelf for a date and, in
 * English, its OWB lookup).
 */
export async function widgetVerses(now: Date, lang: string): Promise<WidgetVerse[]> {
	const keys = dayKeys(now);
	const stored = readVerses(lang);
	const have = new Set(stored.map((v) => v.date));
	const askedAt = Date.now();
	const recentlyAsked = (k: string) => askedAt - (asked.get(`${lang}:${k}`) ?? -Infinity) < RETRY_MS;
	const missing = keys.filter((k) => !have.has(k) && !recentlyAsked(k));
	missing.forEach((k) => asked.set(`${lang}:${k}`, askedAt));
	const fresh = (
		await Promise.all(
			missing.map(async (date) => {
				const verse = await loadDayVerse(dateOfKey(date), lang).catch(() => null);
				return verse ? { date, text: verse.text, ref: verse.ref, lang: verse.lang } : null;
			})
		)
	).filter((v): v is WidgetVerse => v !== null);
	const verses = mergeVerses(stored, fresh, keys[0]);
	if (fresh.length || verses.length !== stored.length) writeVerses(lang, verses);
	return verses;
}

/**
 * The book the home hero resumes (`currentBook`'s answer). From the device's
 * own cache, with no request, as a rule: a book is cached the moment its
 * chapter opens (`rememberResumeBook`). A place synced from another device in
 * a book never opened here is not, so then the shared library list
 * (`libraryBooks`, which fills the cache for next time).
 */
export async function widgetBook(lang: string): Promise<ResumeBook | null> {
	const progress = allProgress();
	const slug = currentBookSlug(knownAbsent(lang), progress);
	if (!slug) return null;
	return (
		resumeBookOf(cachedResumeBooks(lang), slug, progress) ??
		libraryBooks(lang).then(
			(books) => resumeBookOf(books, slug, progress),
			() => null
		)
	);
}

/** What the phone was last handed, and when. An unchanged snapshot is sent
 *  again after RESEND_MS all the same: the phone fetches the cover itself, and
 *  a cover that failed to download (offline) is retried that way. */
let sent = '';
let sentAt = 0;
const RESEND_MS = 60 * 60_000;
let queue: Promise<void> = Promise.resolve();

/** Build the snapshot now and send it if it changed. Calls run one at a time. */
export function syncWidgets(now = new Date()): Promise<void> {
	queue = queue.then(async () => {
		const lang = getLang();
		const locale = getLocale();
		const t = i18n.t;
		// Independent: the verses and the book load side by side.
		const [verses, book] = await Promise.all([widgetVerses(now, lang), widgetBook(lang)]);
		const snapshot = buildWidgetSnapshot({
			locale,
			rtl: getTextDirection(locale) === 'rtl',
			siteUrl: SITE_URL,
			localize: (path) => localizeHref(path),
			strings: {
				today: t('home.todayVerse'),
				continue: t('continue.title'),
				start: t('home.startReading'),
				chapterOf: t('home.resumeChapter')
			},
			verses,
			book
		});
		const json = JSON.stringify(snapshot);
		if (json === sent && Date.now() - sentAt < RESEND_MS) return;
		if (await setWidgetSnapshot(json)) {
			sent = json;
			sentAt = Date.now();
		}
	});
	return queue.catch(() => {});
}

let soonTimer: ReturnType<typeof setTimeout> | undefined;

/** Sync a moment from now — after a page (a chapter) opens and saves the
 *  reader's place, or a sync from the account lands; calls fold into one. */
export function syncWidgetsSoon(): void {
	clearTimeout(soonTimer);
	soonTimer = setTimeout(() => void syncWidgets(), 1500);
}

/**
 * Keep the widgets current while the app runs: now; on each new day; after a
 * sync from the account; and as the app goes to the background — the moment the home
 * screen, and so the widget, comes into view. The layout adds a
 * `syncWidgetsSoon` after each navigation. Returns the cleanup.
 */
export function startWidgetSync(): () => void {
	const onHide = () => {
		if (document.visibilityState === 'hidden') void syncWidgets();
	};
	// watchToday looks every few minutes; only a new day changes anything.
	let day = '';
	const stopToday = watchToday((now) => {
		if (localToday(now) === day) return;
		day = localToday(now);
		void syncWidgets(now);
	});
	window.addEventListener('ochorus:sync', syncWidgetsSoon);
	document.addEventListener('visibilitychange', onHide);
	return () => {
		clearTimeout(soonTimer);
		stopToday();
		window.removeEventListener('ochorus:sync', syncWidgetsSoon);
		document.removeEventListener('visibilitychange', onHide);
	};
}
