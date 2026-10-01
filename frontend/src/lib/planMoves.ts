/**
 * Reading plans that moved to a new slug because their days were renumbered.
 *
 * A plan's completed days are day NUMBERS, cached on the device and unioned
 * into the account on every sync, so renumbering a plan in place would let a
 * device's old numbers tick the wrong days. Instead the plan takes a new slug
 * (the server moves the account's progress in a migration — backend
 * `library/migrations/0172_reshape_first_key_teachings.py`,
 * `reading/migrations/0032_move_series_plan_progress.py`) and this moves the
 * device's own cache across, once, by this rule (0172 applies all of it; 0032's
 * series moves have no merged days, and their only brand-new days — each
 * book's Introduction and Conclusion — sit on book boundaries, so the
 * read-past rule never fires there and the server simply leaves them unread):
 *
 * - a new day made of several old days is done only if all of them were;
 * - a brand-new day (no old days) is done when the reader had already done the
 *   days either side of it in the same book — they read past it.
 *
 * A retired plan may be SPLIT across several successors (a list of moves): the
 * reader starts each successor they had ticked a day of, or the first one if
 * they had ticked none.
 */

export interface PlanMove {
	to: string;
	/** For each new day (index 0 = day 1), the old day numbers it replaces. */
	sources: number[][];
	/** For each new day, which book it belongs to (only equality matters). */
	books: number[];
}

// The young-reader series plans (reading 0032). Every book in these series has
// 32 chapters — Introduction, Day 1 … Day 30, Conclusion — and a successor
// reads all of them, three books per plan, so its day for (book b, chapter c)
// is b * 32 + c.
const SERIES_CHAPTERS = 32;

/** A three-book series plan, mapping each (book, chapter) to an old day. */
function seriesMove(to: string, oldDay: (book: number, order: number) => number | null): PlanMove {
	const sources: number[][] = [];
	const books: number[] = [];
	for (let book = 0; book < 3; book++) {
		for (let order = 1; order <= SERIES_CHAPTERS; order++) {
			const day = oldDay(book, order);
			sources.push(day === null ? [] : [day]);
			books.push(book);
		}
	}
	return { to, sources, books };
}

/** `<series>-book-<n>-30-days` read one book's Day 1 … Day 30 (chapters 2–31). */
const perBookPlans = (series: string, to: string, first: number): Record<string, PlanMove[]> =>
	Object.fromEntries(
		[0, 1, 2].map((i) => [
			`${series}-book-${first + i}-30-days`,
			[seriesMove(to, (book, order) => (book === i && order >= 2 && order <= 31 ? order - 1 : null))]
		])
	);

export const PLAN_MOVES: Record<string, PlanMove[]> = {
	...perBookPlans('rooted', 'rooted-three-months-books-1-3', 1),
	...perBookPlans('rooted', 'rooted-three-months-books-4-6', 4),
	...perBookPlans('daughters-of-the-king', 'daughters-of-the-king-three-months', 1),
	...perBookPlans('sons-of-the-king', 'sons-of-the-king-three-months', 1),
	// Six books, 192 days, split into its two halves.
	'rooted-six-months-with-god': [0, 1].map((half) =>
		seriesMove(
			`rooted-three-months-books-${half ? '4-6' : '1-3'}`,
			(book, order) => (half * 3 + book) * SERIES_CHAPTERS + order
		)
	),
	// 0172: the four Key Teachings volumes the plan reads were reshaped (88 → 86 days).
	'the-key-teachings-four-teachers': [
		{
			to: 'key-teachings-four-teachers',
			sources: [
				[1], [2], [3], [4, 5], [6, 7], [8], [9, 10], [11], [12], [13], [14], [15], [16], [17],
				[18], [19], [20], [21], [22], [23], [24], [25], [26], [27], [28], [29], [30], [31], [32],
				[33], [34], [], [35], [36], [37], [38], [39], [], [40], [41], [42], [43], [44], [45], [46],
				[47], [48], [49], [50], [51], [52], [53, 54], [55, 56], [57], [58], [59], [60], [61], [62],
				[63], [64], [65], [66], [67], [68], [69], [70], [71], [72], [73], [74], [75], [76], [77],
				[78], [79], [80], [81], [82], [83], [84], [], [85], [86], [87], [88]
			],
			books: [
				0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
				1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
				2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3
			]
		}
	]
};

/** The new plan's done days, from the old plan's. */
export function movedDone(move: PlanMove, oldDone: readonly number[]): number[] {
	const had = new Set(oldDone);
	const done = new Set<number>();
	move.sources.forEach((olds, i) => {
		if (olds.length && olds.every((d) => had.has(d))) done.add(i + 1);
	});
	move.sources.forEach((olds, i) => {
		if (olds.length) return;
		const day = i + 1;
		const sameBook = (n: number) => move.books[n - 1] === move.books[day - 1];
		const before = day > 1 && sameBook(day - 1) && done.has(day - 1);
		const after = day < move.sources.length && sameBook(day + 1) && done.has(day + 1);
		if (before && after) done.add(day);
	});
	return [...done].sort((a, b) => a - b);
}

/**
 * Move every retired slug in a plan store to its new one(s). Returns the slugs
 * it wrote, so the caller can push them to the account. A store that already
 * has a new slug keeps it (union of both), and the retired entry is dropped.
 */
export function applyPlanMoves<S extends { startedAt: number; done: number[] }>(
	store: Record<string, S>
): string[] {
	const moved = new Set<string>();
	for (const [from, moves] of Object.entries(PLAN_MOVES)) {
		const old = store[from];
		if (!old) continue;
		const carried = moves.map((move) => ({ to: move.to, done: movedDone(move, old.done) }));
		// A split plan starts only the successors the reader reached.
		const reached = carried.filter((c) => c.done.length);
		for (const { to, done } of reached.length ? reached : carried.slice(0, 1)) {
			const existing = store[to];
			store[to] = {
				...old,
				startedAt: existing ? Math.min(existing.startedAt, old.startedAt) : old.startedAt,
				done: [...new Set([...(existing?.done ?? []), ...done])].sort((a, b) => a - b)
			};
			moved.add(to);
		}
		delete store[from];
	}
	return [...moved];
}
