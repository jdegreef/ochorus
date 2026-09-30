/**
 * Reading plans that moved to a new slug because their days were renumbered.
 *
 * A plan's completed days are day NUMBERS, cached on the device and unioned
 * into the account on every sync, so renumbering a plan in place would let a
 * device's old numbers tick the wrong days. Instead the plan takes a new slug
 * (the server moves the account's progress in the same migration — backend
 * `library/migrations/0171_reshape_first_key_teachings.py`) and this moves the
 * device's own cache across, once, by the same rule:
 *
 * - a new day made of several old days is done only if all of them were;
 * - a brand-new day (no old days) is done when the reader had already done the
 *   days either side of it in the same book — they read past it.
 */

export interface PlanMove {
	to: string;
	/** For each new day (index 0 = day 1), the old day numbers it replaces. */
	sources: number[][];
	/** For each new day, which book it belongs to (only equality matters). */
	books: number[];
}

// 0171: the four Key Teachings volumes the plan reads were reshaped (88 → 86 days).
export const PLAN_MOVES: Record<string, PlanMove> = {
	'the-key-teachings-four-teachers': {
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
 * Move every retired slug in a plan store to its new one. Returns the slugs it
 * wrote, so the caller can push them to the account. A store that already has
 * the new slug keeps it (union of both), and the retired entry is dropped.
 */
export function applyPlanMoves<S extends { startedAt: number; done: number[] }>(
	store: Record<string, S>
): string[] {
	const moved: string[] = [];
	for (const [from, move] of Object.entries(PLAN_MOVES)) {
		const old = store[from];
		if (!old) continue;
		const carried = movedDone(move, old.done);
		const existing = store[move.to];
		store[move.to] = {
			...old,
			startedAt: existing ? Math.min(existing.startedAt, old.startedAt) : old.startedAt,
			done: [...new Set([...(existing?.done ?? []), ...carried])].sort((a, b) => a - b)
		};
		delete store[from];
		moved.push(move.to);
	}
	return moved;
}
