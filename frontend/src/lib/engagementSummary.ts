// The Engagement page's opening sentence: how the last 7 days went, in words,
// from numbers the page already loads. Pure, so its wording rules are tested
// rather than eyeballed. "This week" is the last 7 days, the same window as the
// "Active · 7d" tile, so the sentence and the tile never disagree.
import { SMALL_BASE, type AdminEngagement, type EngagementEvent } from './library-admin';

/** A run of the sentence: plain, bold, or a link. */
export type SummaryPart = { text: string; strong?: boolean; href?: string };

export interface WeeklySummary {
	parts: SummaryPart[];
	/** The sentence as plain text, for the Copy button. */
	text: string;
	/** This week's events, named on their own line under the sentence. */
	events: EngagementEvent[];
}

/** Hearts must move at least this much to earn a clause. */
export const HEARTS_MIN_CHANGE = 3;

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** "up 2 on last week": a count below the small base, a percentage above it,
 *  the same rule as the trend chips. */
export function weekChange(cur: number, prev: number): string {
	if (cur === prev) return 'the same as last week';
	const dir = cur > prev ? 'up' : 'down';
	if (prev < SMALL_BASE) return `${dir} ${Math.abs(cur - prev)} on last week`;
	return `${dir} ${Math.abs(Math.round(((cur - prev) / prev) * 100))}% on last week`;
}

/** Reading time in words: "48 minutes", "1 hour 12 minutes", "under a minute". */
export function durationWords(seconds: number): string {
	const mins = Math.floor(seconds / 60);
	if (mins < 1) return 'under a minute';
	const h = Math.floor(mins / 60);
	const m = mins % 60;
	if (!h) return plural(m, 'minute');
	return m ? `${plural(h, 'hour')} ${plural(m, 'minute')}` : plural(h, 'hour');
}

type SummaryInput = Pick<AdminEngagement, 'overview' | 'time' | 'rising'> & {
	events?: EngagementEvent[];
};

/** `today` is an ISO date (the viewer's), for picking this week's events. */
export function weeklySummary(
	d: SummaryInput,
	today: string,
	workHref: (w: SummaryInput['rising'][number]) => string
): WeeklySummary {
	const { active_7d: n, active_7d_prev: prev, hearts_7d, hearts_7d_prev } = d.overview;
	const since = new Date(today + 'T00:00:00Z'); // UTC, so toISOString can't shift the day
	since.setUTCDate(since.getUTCDate() - 6);
	const sinceIso = since.toISOString().slice(0, 10);
	const events = (d.events ?? []).filter((e) => e.date >= sinceIso && e.date <= today);

	if (!n) {
		const text = 'No one has opened a book yet this week.';
		return { parts: [{ text }], text, events };
	}
	const parts: SummaryPart[] = [
		{ text: plural(n, 'reader'), strong: true },
		{ text: ' opened a book this week, ' },
		{ text: weekChange(n, prev), strong: true }
	];
	if (d.time.seconds_7d >= 60) {
		parts.push({ text: ', and spent ' }, { text: durationWords(d.time.seconds_7d), strong: true }, { text: ' reading' });
	}
	parts.push({ text: '.' });
	const top = d.rising[0];
	if (top) {
		parts.push(
			{ text: ' ' },
			{ text: top.title, href: workHref(top) },
			{ text: ` is rising fastest, with ${plural(top.delta, 'more reader')} than last week.` }
		);
	}
	if (Math.abs(hearts_7d - hearts_7d_prev) >= HEARTS_MIN_CHANGE) {
		parts.push({ text: ` Hearts ${hearts_7d > hearts_7d_prev ? 'rose' : 'fell'} to ${hearts_7d} this week.` });
	}
	return { parts, text: parts.map((p) => p.text).join(''), events };
}
