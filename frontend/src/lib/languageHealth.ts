/**
 * The language-health page's reading of a score: what each signal earned and
 * lost, which band a score sits in, and the one piece of work worth the most
 * points next. Pure, so it is tested beside this file; the page only renders.
 */
import type {
	AdminLanguageHealth,
	AdminLanguageReadiness,
	HealthScoreKey,
	HealthWeights,
	ShelfKind
} from './library-admin';

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
		// `?? 0`: a key the API renamed or dropped degrades to an empty track
		// rather than a NaN that breaks the bar, its label and the grid.
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

const nf = new Intl.NumberFormat('en');

/** "1 reader" / "12,345 readers", formatted like every other count on the page. */
export const plural = (n: number, one: string, many = `${one}s`) =>
	`${nf.format(n)} ${n === 1 ? one : many}`;

/** How coverage weighs each kind of content, and the source shelf's count of
 *  each. Absent (an API that scored books alone), coverage reads as books only. */
export interface CoverageShelf {
	mix: Record<ShelfKind, number>;
	source: Record<ShelfKind, number>;
}

const SHELF_KINDS: ShelfKind[] = ['books', 'sermons', 'bios', 'plans'];

const SHELF_NOUN: Record<ShelfKind, string> = {
	books: 'book',
	sermons: 'sermon',
	bios: 'bio',
	plans: 'plan'
};

const have = (l: AdminLanguageHealth, k: ShelfKind) =>
	k === 'books' ? l.content.published_books : l.content[k];

/** The kinds the source shelf actually has; the backend leaves the rest out of
 *  the mix and renormalises, so the page does the same. */
export const shelfKinds = (shelf: CoverageShelf) => SHELF_KINDS.filter((k) => shelf.source[k] > 0);

/**
 * The raw count behind a signal's bar, so a percentage never hides the size of
 * the job. `engagementTarget` is absent from an API that predates the fixed
 * target; engagement then shows the bare reader count.
 */
export function countLine(
	key: HealthScoreKey,
	l: AdminLanguageHealth,
	sourceBooks: number,
	engagementTarget?: number,
	shelf?: CoverageShelf
): string {
	switch (key) {
		case 'readiness':
			return l.readiness.ready ? 'all checks met' : `${nf.format(l.readiness.blocking.length)} blocking`;
		case 'coverage':
			if (!shelf) return `${nf.format(l.content.published_books)} of ${nf.format(sourceBooks)} books`;
			if (!shelfKinds(shelf).length) return 'no English shelf to compare';
			return shelfKinds(shelf)
				.map((k) => `${k} ${Math.round(100 * Math.min(1, have(l, k) / shelf.source[k]))}%`)
				.join(' · ');
		case 'review': {
			const total = l.content.published_books;
			return total
				? `${nf.format(total - l.content.unreviewed_books)} of ${nf.format(total)} reviewed`
				: 'nothing to review';
		}
		case 'engagement':
			if (!engagementTarget) return plural(l.readers, 'reader');
			// Past the target the bar is full; "30 of 25" would read as a bug.
			return l.readers >= engagementTarget
				? `target met (${plural(l.readers, 'reader')})`
				: `${nf.format(l.readers)} of ${plural(engagementTarget, 'reader')}`;
	}
}

export type Blocker = { key: string; label: string };

/**
 * Readiness check keys by their human names ("Interface strings", not "ui").
 * The report lists `blocking` and `unforceable` as keys, but every check in
 * `checks` already carries its label, so no second copy of the names is kept.
 * A key the report doesn't list shows as itself.
 */
export const checkLabels = (r: Pick<AdminLanguageReadiness, 'checks'>, keys: string[]): string[] =>
	keys.map((key) => r.checks.find((c) => c.key === key)?.label ?? key);

/**
 * The language's blocking checks, labelled. The API sends `{key, label}`; an
 * API deployed before this page sent bare keys, and the web build and the API
 * ship separately, so a bare key is read as its own label rather than breaking.
 */
export const blockers = (l: AdminLanguageHealth): Blocker[] =>
	(l.readiness.blocking as (Blocker | string)[]).map((c) =>
		typeof c === 'string' ? { key: c, label: c } : c
	);

/**
 * The levers an admin can pull, best first. Engagement is left out on purpose:
 * readers aren't something an hour of admin work produces, so it never heads
 * the list — the bar still shows what it has lost.
 */
export function nextActions(
	l: AdminLanguageHealth,
	sourceBooks: number,
	weights: HealthWeights,
	shelf?: CoverageShelf
): NextAction[] {
	if (l.is_source) return [];
	const pts = Object.fromEntries(pointsBreakdown(l.scores, weights).map((p) => [p.key, p]));
	const code = encodeURIComponent(l.code);
	const out: NextAction[] = [];

	const blocking = blockers(l);
	out.push({
		key: 'readiness',
		gain: pts.readiness.lost,
		label: blocking.length
			? `Clear the go-live ${blocking.length === 1 ? 'blocker' : 'blockers'}: ${blocking.map((c) => c.label).join(', ')}`
			: 'Close the remaining go-live gaps',
		perUnit: null,
		href: `/admin/languages/${code}#sec-readiness`,
		cta: 'Open readiness'
	});

	if (shelf) {
		const kinds = shelfKinds(shelf);
		const mixTotal = kinds.reduce((s, k) => s + shelf.mix[k], 0);
		const gaps = kinds
			.map((k) => ({ k, n: Math.max(0, shelf.source[k] - have(l, k)) }))
			.filter((g) => g.n > 0);
		// Send the admin to the kind whose gap costs the most points.
		const lostOn = (g: { k: ShelfKind; n: number }) => (shelf.mix[g.k] * g.n) / shelf.source[g.k];
		const worst = gaps.reduce<(typeof gaps)[number] | undefined>(
			(a, g) => (!a || lostOn(g) > lostOn(a) ? g : a),
			undefined
		);
		const missingBooks = gaps.find((g) => g.k === 'books')?.n ?? 0;
		out.push({
			key: 'coverage',
			gain: pts.coverage.lost,
			label: `Translate the missing content (${gaps.map((g) => plural(g.n, SHELF_NOUN[g.k], g.k)).join(', ')})`,
			// One book's share of the coverage points, after renormalising; none
			// once every book is here, since another one would earn nothing.
			perUnit:
				missingBooks && mixTotal
					? (pts.coverage.max * shelf.mix.books) / mixTotal / shelf.source.books
					: null,
			href: `/admin/languages/${code}#sec-${worst?.k ?? 'books'}`,
			cta: `Open ${worst?.k ?? 'books'}`
		});
	} else {
		const missing = Math.max(0, sourceBooks - l.content.published_books);
		out.push({
			key: 'coverage',
			gain: pts.coverage.lost,
			label: `Translate more books (${missing} of ${sourceBooks} not here yet)`,
			perUnit: sourceBooks ? pts.coverage.max / sourceBooks : null,
			href: `/admin/languages/${code}#sec-books`,
			cta: 'Open books'
		});
	}

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
