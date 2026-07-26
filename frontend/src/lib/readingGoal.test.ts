import { beforeEach, describe, it, expect } from 'vitest';
import { readingGoal, DEFAULT_GOAL, GOAL_MIN, GOAL_MAX } from './readingGoal.svelte';

const KEY = 'ochorus:reading-goal';

beforeEach(() => localStorage.clear());

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
