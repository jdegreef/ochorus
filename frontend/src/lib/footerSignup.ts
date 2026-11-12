import { adventWindow, SEASON_DOORS } from './seasonCalendar';
import { localDayNumber } from './dailyArticles';
import type { SignupSource } from './signupSource';

/**
 * Which message the footer's sign-up card shows a signed-out reader (design:
 * "Ochorus Footer Sign-up", 2026-11). One slot, the strongest reason for THIS
 * reader on THIS page, in order:
 *
 *  1. `progress` — a book in progress on this device: name it ("don't lose
 *     what you've read"), the warmest reason there is.
 *  2. `page` — on a book, sermon, biography or plan page: the thing they just
 *     spent minutes on.
 *  3. `season` — Advent, and the three weeks before it: a start date is a
 *     reason to act now. Only a season whose calendar has doors (Lent's is
 *     still empty, so it never shows).
 *  4. `band` — everyone else: what an account keeps, drawn.
 *
 * Each carries its own sign-up source, so the admin Users page can count what
 * each one earned (`footer` stays the general band's, as before).
 */
export type FooterPitch = 'progress' | 'page' | 'season' | 'band';

export type FooterPage =
	| { kind: 'book'; title: string }
	| { kind: 'sermon'; title: string }
	| { kind: 'author'; name: string }
	| { kind: 'plan'; title: string };

export const FOOTER_SOURCE: Record<FooterPitch, SignupSource> = {
	progress: 'footer_progress',
	page: 'footer_page',
	season: 'footer_season',
	band: 'footer'
};

/** How long before Advent Sunday the footer starts inviting readers to it. */
export const SEASON_LEAD_DAYS = 21;

/**
 * Advent's window if `date` falls in it or in the lead-up, with the days until
 * it starts (0 once it has). Null otherwise, or when the season has no doors.
 */
export function adventOffer(date: Date): { start: number; daysToGo: number } | null {
	if (!SEASON_DOORS.advent.length) return null;
	const w = adventWindow(date.getFullYear());
	const today = localDayNumber(date);
	const start = w.days[0];
	const end = w.days[w.days.length - 1];
	if (today < start - SEASON_LEAD_DAYS || today > end) return null;
	return { start, daysToGo: Math.max(0, start - today) };
}

export function chooseFooterPitch(input: {
	hasProgressBook: boolean;
	page: FooterPage | null;
	inSeason: boolean;
}): FooterPitch {
	if (input.hasProgressBook) return 'progress';
	if (input.page) return 'page';
	if (input.inSeason) return 'season';
	return 'band';
}

/**
 * The page the footer sits under, from the route and its loaded data — only
 * the four kinds with something to name. Anything else (or a page whose data
 * is missing, as on an error) is null.
 */
export function footerPage(routeId: string | null, data: Record<string, unknown>): FooterPage | null {
	const title = (o: unknown, key: 'title' | 'name') =>
		o && typeof o === 'object' && typeof (o as Record<string, unknown>)[key] === 'string'
			? ((o as Record<string, unknown>)[key] as string)
			: '';
	switch (routeId) {
		case '/books/[slug]': {
			const t = title(data.book, 'title');
			return t ? { kind: 'book', title: t } : null;
		}
		case '/sermons/[slug]': {
			const t = title(data.sermon, 'title');
			return t ? { kind: 'sermon', title: t } : null;
		}
		case '/authors/[slug]': {
			const n = title(data.author, 'name');
			return n ? { kind: 'author', name: n } : null;
		}
		case '/plans/[slug]': {
			const t = title(data.plan, 'title');
			return t ? { kind: 'plan', title: t } : null;
		}
		default:
			return null;
	}
}
