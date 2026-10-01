/**
 * The language-health page's reading of a score: what each signal earned and
 * lost, which band a score sits in, and the one piece of work worth the most
 * points next. Pure, so it is tested beside this file; the page only renders.
 */
import type { AdminLanguageHealth, HealthScoreKey } from './library-admin';

export type HealthWeights = Record<HealthScoreKey, number>;

/** The composite's ingredients, in the order the backend weights them. */
export const HEALTH_KEYS: HealthScoreKey[] = ['readiness', 'coverage', 'review', 'engagement'];

export interface SignalPoints {
	key: HealthScoreKey;
	/** Points this signal can contribute out of 100 (its weight × 100). */
	max: number;
	earned: number;
	lost: number;
}

/** Each signal's share of the 100 points, split into earned and still available. */
export function pointsBreakdown(
	scores: Record<HealthScoreKey, number>,
	weights: HealthWeights
): SignalPoints[] {
	return HEALTH_KEYS.map((key) => {
		const max = (weights[key] ?? 0) * 100;
		const earned = max * Math.min(1, Math.max(0, scores[key] ?? 0));
		return { key, max, earned, lost: max - earned };
	});
}

export type HealthBand = { label: 'Strong' | 'Fair' | 'Weak'; tone: 'accent' | 'text' | 'warning' };

export const BAND_STRONG = 75;
export const BAND_FAIR = 45;

/** A named band, so the score never relies on colour alone. */
export function healthBand(health: number): HealthBand {
	if (health >= BAND_STRONG) return { label: 'Strong', tone: 'accent' };
	if (health >= BAND_FAIR) return { label: 'Fair', tone: 'text' };
	return { label: 'Weak', tone: 'warning' };
}

export interface NextAction {
	key: HealthScoreKey;
	/** Points the composite would gain if this signal were maxed out. */
	gain: number;
	label: string;
	/** Points one unit of the work is worth (one book reviewed / translated). */
	perUnit: number | null;
	href: string;
	cta: string;
}

/** Below this many points a lever isn't worth recommending. */
const MIN_GAIN = 0.5;

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/**
 * The levers an admin can pull, best first. Engagement is left out on purpose:
 * readers aren't something an hour of admin work produces, so it never heads
 * the list — the bar still shows what it has lost.
 */
export function nextActions(
	l: AdminLanguageHealth,
	sourceBooks: number,
	weights: HealthWeights,
	checkLabel: (key: string) => string = (k) => k
): NextAction[] {
	if (l.is_source) return [];
	const pts = Object.fromEntries(pointsBreakdown(l.scores, weights).map((p) => [p.key, p]));
	const code = encodeURIComponent(l.code);
	const out: NextAction[] = [];

	const blocking = l.readiness.blocking;
	out.push({
		key: 'readiness',
		gain: pts.readiness.lost,
		label: blocking.length
			? `Clear the go-live ${blocking.length === 1 ? 'blocker' : 'blockers'}: ${blocking.map(checkLabel).join(', ')}`
			: 'Close the remaining go-live gaps',
		perUnit: null,
		href: `/admin/languages/${code}#sec-readiness`,
		cta: 'Open readiness'
	});

	const missing = Math.max(0, sourceBooks - l.content.published_books);
	out.push({
		key: 'coverage',
		gain: pts.coverage.lost,
		label: `Translate more books (${missing} of ${sourceBooks} not here yet)`,
		perUnit: sourceBooks ? pts.coverage.max / sourceBooks : null,
		href: `/admin/languages/${code}#sec-books`,
		cta: 'Open books'
	});

	const unreviewed = l.content.unreviewed_books;
	if (unreviewed > 0) {
		out.push({
			key: 'review',
			gain: pts.review.lost,
			label: `Review ${plural(unreviewed, 'AI-translated book')}`,
			perUnit: l.content.published_books ? pts.review.max / l.content.published_books : null,
			href: `/admin/review?language=${code}`,
			cta: 'Open review queue'
		});
	}

	return out.filter((a) => a.gain >= MIN_GAIN).sort((a, b) => b.gain - a.gain);
}
