/**
 * The dashboard's trend tiles, shaped from `GET /api/admin/trends/`. Pure (no
 * Svelte, no fetch) so the labels, formats and which direction reads as bad
 * are unit-tested (`adminDashboard.test.ts`). Admin copy is English-only.
 */
import { formatDuration, periodTrend, type AdminTrends, type Trend } from './library-admin';

export interface PulseTile {
	label: string;
	value: string;
	sub: string;
	trend: Trend;
	values: number[];
	labels: string[];
	format: (n: number) => string;
	href: string;
}

const nf = new Intl.NumberFormat('en');
export const num = (n: number) => nf.format(n);

/** "Nov 23" for a date (`2026-11-23`) or a moment. */
export const shortDate = (iso: string): string =>
	new Date(iso.length === 10 ? iso + 'T00:00:00' : iso).toLocaleDateString('en', {
		month: 'short',
		day: 'numeric'
	});

/** "week of Nov 23" — what each sparkline point is, for screen readers. */
export const weekLabel = (iso: string): string => `week of ${shortDate(iso)}`;

/** Whole days since `iso`; null for a missing or unparseable time. Shared by
 *  the dashboard's backlog and the review queue's "oldest waiting". */
export function daysSince(iso: string | null | undefined, now: number = Date.now()): number | null {
	if (!iso) return null;
	const t = Date.parse(iso);
	return Number.isNaN(t) ? null : Math.max(0, Math.floor((now - t) / 86_400_000));
}

/** A rise where a rise is bad (searches that found nothing) reads red. */
const inverted = (t: Trend): Trend => (t && t.dir !== 'flat' ? { ...t, bad: t.dir === 'up' } : t);

export function pulseTiles(p: AdminTrends['pulse']): PulseTile[] {
	const labels = p.weeks.map(weekLabel);
	const tile = (
		label: string,
		s: AdminTrends['pulse']['readers'],
		format: (n: number) => string,
		href: string,
		lowerIsBetter = false
	): PulseTile => {
		const t = periodTrend(s.d7, s.d7_prev);
		return {
			label,
			value: format(s.d7),
			sub: `${format(s.d30)} in 30 days`,
			trend: lowerIsBetter ? inverted(t) : t,
			values: s.weekly,
			labels,
			format,
			href
		};
	};
	return [
		tile('Readers · 7d', p.readers, num, '/admin/engagement'),
		tile('New accounts · 7d', p.signups, num, '/admin/users'),
		tile('Reading time · 7d', p.reading_seconds, (n) => formatDuration(n), '/admin/engagement'),
		tile('Searches with no result · 7d', p.zero_searches, num, '/admin/search', true)
	];
}

/** "89 / 255" and the share as a whole percent, for a Level 1 bar. */
export function levelProgress(l: { done: number; total: number }): { pct: number; text: string } {
	const pct = l.total ? Math.round((l.done / l.total) * 100) : 0;
	return { pct, text: `${num(l.done)} / ${num(l.total)}` };
}

/** How long the oldest item has waited, in days ("12 days"). */
export function waitedFor(iso: string, now: Date = new Date()): string {
	const days = daysSince(iso, now.getTime()) ?? 0;
	return `${num(days)} day${days === 1 ? '' : 's'}`;
}
