import { beforeEach, describe, it, expect, vi } from 'vitest';
import { DEFAULT_GOAL, GOAL_MIN, GOAL_MAX } from './readingGoal.svelte';

const KEY = 'ochorus:reading-goal';

// The store is a module singleton: each test gets a fresh instance, as a fresh
// page load would, so a goal set by one test never leaks into the next.
let readingGoal: typeof import('./readingGoal.svelte').readingGoal;
beforeEach(async () => {
	localStorage.clear();
	vi.resetModules();
	({ readingGoal } = await import('./readingGoal.svelte'));
});

describe('readingGoal', () => {
	it('defaults to DEFAULT_GOAL', () => {
		expect(readingGoal.perWeek).toBe(DEFAULT_GOAL);
	});

	it('clamps and persists a set value', () => {
		readingGoal.set(6);
		expect(readingGoal.perWeek).toBe(6);
		expect(JSON.parse(localStorage.getItem(KEY)!)).toBe(6);
	});

	it('clamps out-of-range and non-finite input to [MIN, MAX]', () => {
		readingGoal.set(99);
		expect(readingGoal.perWeek).toBe(GOAL_MAX);
		readingGoal.set(0);
		expect(readingGoal.perWeek).toBe(GOAL_MIN);
		readingGoal.set(Number.NaN);
		expect(readingGoal.perWeek).toBe(DEFAULT_GOAL);
	});
});

describe('yearly books goal', () => {
	it('is unset by default, then set per year, clamped, and cleared', () => {
		expect(readingGoal.booksFor(2026)).toBeNull();
		readingGoal.setBooks(2026, 12);
		readingGoal.setBooks(2025, 999);
		expect(readingGoal.booksFor(2026)).toBe(12);
		expect(readingGoal.booksFor(2025)).toBe(365);
		expect(JSON.parse(localStorage.getItem('ochorus:reading-goal-books')!)).toEqual({ '2026': 12, '2025': 365 });
		readingGoal.setBooks(2026, null);
		expect(readingGoal.booksFor(2026)).toBeNull();
	});
});
