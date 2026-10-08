import { beforeEach, describe, expect, it } from 'vitest';
import { MAX_DISMISSALS, SNOOZE_MS, noteChapterEnd, shouldAsk, snoozeAsk } from './chapterAsk';

beforeEach(() => localStorage.clear());

describe('noteChapterEnd', () => {
	it('counts distinct chapter ends', () => {
		expect(noteChapterEnd('book:humility:7')).toBe(1);
		expect(noteChapterEnd('book:humility:7')).toBe(1);
		expect(noteChapterEnd('book:humility:8')).toBe(2);
	});
});

describe('shouldAsk — the end-of-chapter card', () => {
	it('asks from the first chapter end, wherever the reader started', () => {
		expect(shouldAsk(0)).toBe(false);
		expect(shouldAsk(1)).toBe(true);
	});

	it('hides for a week after "Not now"', () => {
		snoozeAsk(1000);
		expect(shouldAsk(3, 1000 + SNOOZE_MS - 1)).toBe(false);
		expect(shouldAsk(3, 1000 + SNOOZE_MS)).toBe(true);
	});

	it(`stops for good after ${MAX_DISMISSALS} "Not now"s`, () => {
		for (let i = 0; i < MAX_DISMISSALS; i++) snoozeAsk(0);
		expect(shouldAsk(3, SNOOZE_MS * 10)).toBe(false);
	});
});
