import { describe, expect, it } from 'vitest';
import {
	bookProgressPercent,
	chapterLabel,
	contentLang,
	minutesLeft,
	readingMinutes,
	readingTime,
	listenMinutes,
	listenTime,
	planTimeLeft
} from './reading';

describe('readingMinutes', () => {
	it('never returns less than one minute', () => {
		expect(readingMinutes(0)).toBe(1);
		expect(readingMinutes(50)).toBe(1);
	});

	it('rounds to the nearest minute at ~200 wpm', () => {
		expect(readingMinutes(200)).toBe(1);
		expect(readingMinutes(300)).toBe(2); // 1.5 rounds up
		expect(readingMinutes(500)).toBe(3); // 2.5 rounds up
	});
});

describe('bookProgressPercent', () => {
	it('does not count the open chapter as fully read (was 10% for ch1/10)', () => {
		expect(bookProgressPercent(1, 10)).toBe(5); // midpoint of chapter 1
	});

	it('stays below 100% on the last chapter so the book never vanishes', () => {
		expect(bookProgressPercent(10, 10)).toBe(95);
		expect(bookProgressPercent(16, 16)).toBeLessThan(100);
	});

	it('is always a visibly-started value in [1, 99]', () => {
		expect(bookProgressPercent(1, 1)).toBe(50);
		expect(bookProgressPercent(1, 500)).toBe(1); // clamped up from ~0
		expect(bookProgressPercent(3, 6)).toBe(42);
	});

	it('handles a zero/unknown chapter count without dividing by zero', () => {
		expect(bookProgressPercent(1, 0)).toBe(0);
	});
});

describe('readingTime', () => {
	it('labels sub-hour reads in minutes', () => {
		expect(readingTime(400)).toBe('2 min read');
	});

	it('labels a whole hour without trailing minutes', () => {
		expect(readingTime(200 * 60)).toBe('1 hr read');
	});

	it('labels hours and minutes together', () => {
		expect(readingTime(200 * 65)).toBe('1 hr 5 min read');
		expect(readingTime(200 * 130)).toBe('2 hr 10 min read');
	});
});

describe('planTimeLeft', () => {
	it('reads in minutes under the hour, hours and minutes past it', () => {
		expect(planTimeLeft(45)).toBe('45 min left');
		expect(planTimeLeft(60)).toBe('1 hr left');
		expect(planTimeLeft(251)).toBe('4 hr 11 min left');
	});
});

describe('listenMinutes', () => {
	it('runs slower than reading — a longer estimate for the same words', () => {
		expect(listenMinutes(1550)).toBe(10); // 1550 / 155 wpm
		expect(readingMinutes(1550)).toBe(8); // 1550 / 200 wpm — reading is quicker
	});

	it('shrinks with a faster speed multiplier', () => {
		expect(listenMinutes(1550, 2)).toBe(5); // twice as fast
	});

	it('floors at 1 minute', () => {
		expect(listenMinutes(0)).toBe(1);
		expect(listenMinutes(20)).toBe(1);
	});
});

describe('listenTime', () => {
	it('labels sub-hour listens in minutes', () => {
		expect(listenTime(1550)).toBe('10 min listen');
	});

	it('labels hours and minutes at speed', () => {
		expect(listenTime(155 * 60)).toBe('1 hr listen');
		expect(listenTime(155 * 65)).toBe('1 hr 5 min listen');
	});
});


describe('minutesLeft', () => {
	it('counts down as the reader moves through the text', () => {
		expect(minutesLeft(2000, 0)).toBe(10);
		expect(minutesLeft(2000, 0.5)).toBe(5);
	});

	it('never reads "0 min left" at the foot of the text', () => {
		// The chapter reader used a bare Math.ceil here, so the end of a chapter
		// announced "0 min left" — not a reading time, and it disagreed with the
		// sermon page, which floored at 1 in its own copy.
		expect(minutesLeft(2000, 1)).toBe(1);
		expect(minutesLeft(2000, 0.999)).toBe(1);
	});

	it('clamps a fraction outside 0-1', () => {
		// The scroll fraction is measured from rects and can overshoot slightly.
		expect(minutesLeft(2000, 1.2)).toBe(1);
		expect(minutesLeft(2000, -0.3)).toBe(10);
	});
});

describe('contentLang', () => {
	it('passes a real language code through', () => {
		expect(contentLang('ar')).toBe('ar');
		expect(contentLang('sw')).toBe('sw');
	});

	it('reduces the Modern English edition marker to its base language', () => {
		// en-modern is our own edition marker, not a subtag a browser can
		// hyphenate against; a Modern English edition hyphenates as English.
		expect(contentLang('en-modern')).toBe('en');
	});
});

describe('chapterLabel', () => {
	it('numbers a titled chapter', () => {
		expect(chapterLabel(3, 'The Letter Killeth')).toBe('3. The Letter Killeth');
	});

	it('names an untitled chapter instead of leaving a dangling number', () => {
		// Bounds's Purpose in Prayer is thirteen untitled chapters. The number
		// moves INSIDE the label, so it can never read "1. Chapter 1".
		const label = chapterLabel(1, '');
		expect(label).toMatch(/1$/);
		expect(label).not.toMatch(/^1\./);
	});

	it('treats null and undefined as untitled', () => {
		expect(chapterLabel(2, null)).toBe(chapterLabel(2, ''));
		expect(chapterLabel(2, undefined)).toBe(chapterLabel(2, ''));
	});
});
