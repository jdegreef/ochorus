import { describe, expect, it } from 'vitest';
import { createLimiter } from './limiter';

/** Instrumented work that records how many copies of itself overlap. */
function counter() {
	const state = { inFlight: 0, peak: 0, done: 0 };
	const task = async <T>(value?: T) => {
		state.peak = Math.max(state.peak, ++state.inFlight);
		await new Promise((r) => setTimeout(r, 1));
		state.inFlight--;
		state.done++;
		return value;
	};
	return { state, task };
}

describe('createLimiter', () => {
	it('runs everything, never more than the ceiling at once', async () => {
		const gate = createLimiter(4);
		const { state, task } = counter();
		await Promise.all(Array.from({ length: 20 }, () => gate(task)));
		expect(state.peak).toBe(4);
		expect(state.done).toBe(20);
	});

	it('resolves with the work’s value', async () => {
		const gate = createLimiter(2);
		expect(await Promise.all([1, 2, 3].map((n) => gate(async () => n * 2)))).toEqual([2, 4, 6]);
	});

	it('holds ONE ceiling across independent call sites', async () => {
		// The reason this is a shared object and not a number per call. Three
		// lanes of two would otherwise peak at six while each looks bounded.
		const gate = createLimiter(3);
		const { state, task } = counter();
		await Promise.all([
			Promise.all(Array.from({ length: 5 }, () => gate(task))),
			Promise.all(Array.from({ length: 5 }, () => gate(task))),
			Promise.all(Array.from({ length: 5 }, () => gate(task)))
		]);
		expect(state.peak).toBe(3);
	});

	it('holds the ceiling when a finished call wakes a waiter', async () => {
		// Handing the slot straight to the waiter is what keeps this exact: the
		// waiter resumes a microtask later, and a caller arriving in that gap
		// must not also find a free slot.
		const gate = createLimiter(2);
		const { state, task } = counter();
		const first = Array.from({ length: 6 }, () => gate(task));
		await Promise.resolve();
		const late = Array.from({ length: 4 }, () => gate(task));
		await Promise.all([...first, ...late]);
		expect(state.peak).toBe(2);
	});

	it('releases the slot when the work throws', async () => {
		const gate = createLimiter(1);
		await expect(
			gate(async () => {
				throw new Error('boom');
			})
		).rejects.toThrow('boom');
		// Hangs forever if the failed call kept its slot.
		await expect(gate(async () => 'ok')).resolves.toBe('ok');
	});

	it('treats a limit below one as one', async () => {
		const gate = createLimiter(0);
		const { state, task } = counter();
		await Promise.all([gate(task), gate(task), gate(task)]);
		expect(state.peak).toBe(1);
	});

	it('deadlocks if gated work awaits the same gate — the documented rule', async () => {
		// Pinned deliberately: this is the trap the module comment warns about,
		// and the reason the notebook gates its fetches rather than its lanes.
		// Every slot held by a task waiting for a slot never resolves.
		const gate = createLimiter(2);
		const reentrant = Promise.all(
			[1, 2, 3].map(() => gate(async () => gate(async () => 'leaf')))
		);
		const outcome = await Promise.race([
			reentrant.then(() => 'completed'),
			new Promise((r) => setTimeout(() => r('deadlocked'), 100))
		]);
		expect(outcome).toBe('deadlocked');
	});
});
