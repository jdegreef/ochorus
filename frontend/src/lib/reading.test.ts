import { describe, expect, it } from 'vitest';
import {
	bookProgressPercent,
	workPercent,
	chapterLabel,
	chapterName,
	chapterNameIn,
	contentLang,
	minutesLeft,
	seenFraction,
	readingMinutes,
	readingTime,
	listenMinutes,
	listenTime,
	planTimeLeft,
	planMinutesPerDay
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

describe('planMinutesPerDay', () => {
	it("averages the plan's words over its days, at the reading pace", () => {
		// 96 days, 44,214 words → ~460 words a day → 2 min at 200 wpm.
		expect(planMinutesPerDay({ day_count: 96, total_words: 44214 })).toBe(2);
		expect(planMinutesPerDay({ day_count: 12, total_words: 12 * 1600 })).toBe(8);
	});

	it('is 0 (nothing to show), not a floored 1, with no days or no text', () => {
		expect(planMinutesPerDay({ day_count: 0, total_words: 5000 })).toBe(0);
		expect(planMinutesPerDay({ day_count: 30, total_words: 0 })).toBe(0);
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

describe('chapterNameIn', () => {
	it('says which chapter when its title just repeats the book title', () => {
		// A single-work volume: "Absolute Surrender" under "Absolute Surrender".
		expect(chapterNameIn(1, 'Absolute Surrender', 'Absolute Surrender')).toBe(chapterName(1, ''));
	});

	it('keeps a chapter title that differs from the book', () => {
		expect(chapterNameIn(2, 'The Fruit of the Spirit is Love', 'Absolute Surrender')).toBe(
			'The Fruit of the Spirit is Love'
		);
	});

	it('names an untitled chapter as chapterName does', () => {
		expect(chapterNameIn(3, null, 'Purpose in Prayer')).toBe(chapterName(3, null));
	});
});

describe('seenFraction', () => {
	it('is the share of the block above the viewport bottom, clamped to 0–1', () => {
		expect(seenFraction({ top: 900, height: 1000 }, 900)).toBe(0);
		expect(seenFraction({ top: 400, height: 1000 }, 900)).toBe(0.5);
		expect(seenFraction({ top: -500, height: 1000 }, 900)).toBe(1);
		expect(seenFraction({ top: 0, height: 0 }, 900)).toBe(0);
	});
});

describe('workPercent — the one "% read" (review bug #15)', () => {
	it("uses the reader's stored by-words figure when there is one", () => {
		expect(workPercent({ order: 2, pct: 33 }, 10)).toBe(33);
	});
	it('falls back to the chapter estimate without one', () => {
		expect(workPercent({ order: 2 }, 10)).toBe(bookProgressPercent(2, 10));
	});
	it('is 100 once finished, and never claims completion before', () => {
		expect(workPercent({ order: 10, pct: 100, finished_at: 1 }, 10)).toBe(100);
		expect(workPercent({ order: 10, pct: 100 }, 10)).toBe(99);
		expect(workPercent({ order: 1, pct: 0 }, 10)).toBe(1);
	});
});

describe('workPercent during a peek (review bug #14)', () => {
	it('measures from the furthest chapter, not the peeked one', () => {
		expect(workPercent({ order: 20, furthest: 3, pct: 90 }, 20)).toBe(bookProgressPercent(3, 20));
	});
});

