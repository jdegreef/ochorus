import { describe, expect, it } from 'vitest';
import { deltaWords, durationWords, followingWeek, weekChange, weeklySummary } from './engagementSummary';
import type { EngagementEvent } from './library-admin';

const base = (over: Record<string, number> = {}) => ({
	overview: { active_7d: 11, active_7d_prev: 9, hearts_7d: 8, hearts_7d_prev: 8, ...over } as never,
	time: { seconds_7d: 48 * 60 } as never,
	rising: [] as never[]
});
const href = () => '/books/x';

describe('weekChange', () => {
	it('counts below the small base and uses a percentage above it', () => {
		expect(weekChange(11, 9)).toBe('up 2 on last week');
		expect(weekChange(6, 9)).toBe('down 3 on last week');
		expect(weekChange(30, 20)).toBe('up 50% on last week');
		expect(weekChange(4, 4)).toBe('the same as last week');
	});
});

describe('durationWords', () => {
	it('reads as words', () => {
		expect(durationWords(30)).toBe('under a minute');
		expect(durationWords(60)).toBe('1 minute');
		expect(durationWords(48 * 60)).toBe('48 minutes');
		expect(durationWords(72 * 60)).toBe('1 hour 12 minutes');
		expect(durationWords(120 * 60)).toBe('2 hours');
	});
});

describe('weeklySummary', () => {
	it('says how the week went', () => {
		expect(weeklySummary(base(), href).text).toBe(
			'11 readers opened a book this week, up 2 on last week, and spent 48 minutes reading.'
		);
	});

	it('names the rising work as a link, and hearts only on a real change', () => {
		const d = {
			...base({ hearts_7d: 2, hearts_7d_prev: 7 }),
			rising: [{ title: 'The Pursuit of God', delta: 4 }] as never[]
		};
		const s = weeklySummary(d, href);
		expect(s.text).toContain('The Pursuit of God is rising fastest, with 4 more readers than last week.');
		expect(s.text).toContain('Hearts fell to 2 this week.');
		expect(s.parts.find((p) => p.text === 'The Pursuit of God')?.href).toBe('/books/x');
		expect(weeklySummary(base({ hearts_7d: 9 }), href).text).not.toContain('Hearts');
	});

	it('leaves reading time out when there is none, and says so plainly on an empty week', () => {
		expect(weeklySummary({ ...base(), time: { seconds_7d: 0 } as never }, href).text).toBe(
			'11 readers opened a book this week, up 2 on last week.'
		);
		expect(weeklySummary(base({ active_7d: 0 }), href).text).toBe(
			'No one has opened a book yet this week.'
		);
	});

	it("names only the events the server marks as this week's", () => {
		const ev = (title: string, recent: boolean): EngagementEvent => ({
			week: '2026-09-28',
			date: '2026-09-29',
			kind: 'email',
			title,
			detail: '',
			recent
		});
		const s = weeklySummary({ ...base(), events: [ev('old', false), ev('new', true)] }, href);
		expect(s.events.map((e) => e.title)).toEqual(['new']);
	});
});

describe('followingWeek', () => {
	const series = [
		{ week: 'a', readers: 4 },
		{ week: 'b', readers: 8 }
	];
	it('says what followed, and nothing for the last week', () => {
		expect(followingWeek(series, 'a')).toEqual({ readers: 8, delta: 4 });
		expect(followingWeek(series, 'b')).toBeNull();
		expect(deltaWords(4)).toBe('up 4');
		expect(deltaWords(-1)).toBe('down 1');
		expect(deltaWords(0)).toBe('no change');
	});
});
