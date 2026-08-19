import { describe, expect, it } from 'vitest';
import { mapLimit } from './mapLimit';

/** A promise plus the handle to settle it later. */
function deferred<T>() {
	let resolve!: (v: T) => void;
	let reject!: (e: unknown) => void;
	const promise = new Promise<T>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

describe('mapLimit', () => {
	it('returns results in input order, not completion order', async () => {
		const out = await mapLimit([30, 10, 20], 3, async (ms) => {
			await new Promise((r) => setTimeout(r, ms));
			return ms;
		});
		expect(out).toEqual([30, 10, 20]);
	});

	it('never exceeds the limit, and does keep it busy', async () => {
		let inFlight = 0;
		let peak = 0;
		const out = await mapLimit(Array.from({ length: 20 }, (_, i) => i), 4, async (i) => {
			peak = Math.max(peak, ++inFlight);
			await new Promise((r) => setTimeout(r, 1));
			inFlight--;
			return i * 2;
		});
		expect(peak).toBe(4);
		expect(out).toEqual(Array.from({ length: 20 }, (_, i) => i * 2));
	});

	it('starts the next item as soon as a slot frees, not in fixed batches', async () => {
		// A batching implementation waits for the slowest of each pair before
		// starting the next pair; this one must start the third item the moment
		// the fast first one finishes.
		const slow = deferred<string>();
		const fast = deferred<string>();
		const started: number[] = [];
		const gate = [slow.promise, fast.promise, Promise.resolve('c')];

		const run = mapLimit(gate, 2, async (p, i) => {
			started.push(i);
			return p;
		});
		fast.resolve('b');
		await new Promise((r) => setTimeout(r, 0));
		expect(started).toEqual([0, 1, 2]);
		slow.resolve('a');
		expect(await run).toEqual(['a', 'b', 'c']);
	});

	it('handles an empty list without hanging', async () => {
		expect(await mapLimit([], 4, async () => 1)).toEqual([]);
	});

	it('propagates a rejection, like Promise.all', async () => {
		await expect(
			mapLimit([1, 2, 3], 2, async (n) => {
				if (n === 2) throw new Error('boom');
				return n;
			})
		).rejects.toThrow('boom');
	});
});
