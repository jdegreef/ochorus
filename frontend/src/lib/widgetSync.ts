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
import { buildResumeItems, type ResumeBook } from '$lib/resumeItems';
import { cachedResumeBooks, currentBookSlug, knownAbsent } from '$lib/resumeBooks';
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

/** Days already asked for this launch, so a language with no devotional (or
 *  a failing API) costs one try per day, not one per sync. */
const asked = new Set<string>();

/**
 * The next few days' verses: the stored ones, plus any day not yet stored
 * (normally just the newest, once a day — the shelf for a date and, in
 * English, its OWB lookup).
 */
export async function widgetVerses(now: Date, lang: string): Promise<WidgetVerse[]> {
	const keys = dayKeys(now);
	const stored = readVerses(lang);
	const have = new Set(stored.map((v) => v.date));
	const missing = keys.filter((k) => !have.has(k) && !asked.has(`${lang}:${k}`));
	missing.forEach((k) => asked.add(`${lang}:${k}`));
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
 * The book the home hero resumes (`currentBook`'s answer), from the device's
 * own cache — no request: a book is cached the moment its chapter opens
 * (`rememberResumeBook`), so the book the reader is in is there.
 */
export function widgetBook(lang: string): ResumeBook | null {
	const progress = allProgress();
	const slug = currentBookSlug(knownAbsent(lang), progress);
	if (!slug) return null;
	const [item] = buildResumeItems(
		cachedResumeBooks(lang),
		[],
		progress.filter((p) => p.kind === 'book' && p.slug === slug)
	);
	return item?.kind === 'book' ? item : null;
}

let sent = '';
let queue: Promise<void> = Promise.resolve();

/** Build the snapshot now and send it if it changed. Calls run one at a time. */
export function syncWidgets(now = new Date()): Promise<void> {
	queue = queue.then(async () => {
		const lang = getLang();
		const locale = getLocale();
		const t = i18n.t;
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
			verses: await widgetVerses(now, lang),
			book: widgetBook(lang)
		});
		const json = JSON.stringify(snapshot);
		if (json !== sent && (await setWidgetSnapshot(json))) sent = json;
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
 * Keep the widgets current while the app runs: now; on each new day (and on
 * every return to the app, which `watchToday` looks at); after a sync from the
 * account; and as the app goes to the background — the moment the home
 * screen, and so the widget, comes into view. The layout adds a
 * `syncWidgetsSoon` after each navigation. Returns the cleanup.
 */
export function startWidgetSync(): () => void {
	const onHide = () => {
		if (document.visibilityState === 'hidden') void syncWidgets();
	};
	const stopToday = watchToday((now) => void syncWidgets(now));
	window.addEventListener('ochorus:sync', syncWidgetsSoon);
	document.addEventListener('visibilitychange', onHide);
	return () => {
		clearTimeout(soonTimer);
		stopToday();
		window.removeEventListener('ochorus:sync', syncWidgetsSoon);
		document.removeEventListener('visibilitychange', onHide);
	};
}
