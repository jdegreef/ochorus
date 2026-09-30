import { describe, expect, it } from 'vitest';
import { PLAN_MOVES, applyPlanMoves, movedDone } from './planMoves';

const move = PLAN_MOVES['the-key-teachings-four-teachers'];

describe('the Four Teachers plan move', () => {
	it('maps all 88 old days into 86 new ones, each old day once', () => {
		expect(move.sources).toHaveLength(86);
		expect(move.books).toHaveLength(86);
		expect(move.sources.flat().sort((a, b) => a - b)).toEqual(
			Array.from({ length: 88 }, (_, i) => i + 1)
		);
	});

	it('keeps a finished plan finished, new chapters included', () => {
		const all = Array.from({ length: 88 }, (_, i) => i + 1);
		expect(movedDone(move, all)).toHaveLength(86);
	});

	it('marks a merged day only when every day it replaces was done', () => {
		expect(movedDone(move, [1, 2, 3, 4])).toEqual([1, 2, 3]); // old 4+5 -> new 4
		expect(movedDone(move, [1, 2, 3, 4, 5])).toEqual([1, 2, 3, 4]);
	});

	it('marks a brand-new day read-past only inside the same book', () => {
		// new day 32 (Edwards) sits between old 34 (new 31) and old 35 (new 33)
		expect(movedDone(move, [34, 35])).toEqual([31, 32, 33]);
		expect(movedDone(move, [34])).toEqual([31]);
	});

	it('moves a device store to the new slug once and drops the old one', () => {
		const store: Record<string, { startedAt: number; done: number[] }> = {
			'the-key-teachings-four-teachers': { startedAt: 5, done: [1, 2] },
			other: { startedAt: 1, done: [3] }
		};
		expect(applyPlanMoves(store)).toEqual(['key-teachings-four-teachers']);
		expect(store['the-key-teachings-four-teachers']).toBeUndefined();
		expect(store['key-teachings-four-teachers']).toEqual({ startedAt: 5, done: [1, 2] });
		expect(store.other).toEqual({ startedAt: 1, done: [3] });
		expect(applyPlanMoves(store)).toEqual([]);
	});
});
