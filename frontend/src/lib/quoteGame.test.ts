import { beforeEach, describe, expect, it } from 'vitest';
import { gameStreak, loadLog, recentDays, recordResult, resultLine, type GameLog } from './quoteGame';
import { QUOTE_GAME_KEY, READING_DATA_KEYS } from './reading-schema';

const r = (right: boolean, n = 1) => ({ n, guess: 'x', right });

describe('quoteGame log', () => {
	beforeEach(() => localStorage.clear());

	it('stores one guess a day and keeps the first', () => {
		let log = recordResult({}, '2026-11-11', r(true));
		log = recordResult(log, '2026-11-11', r(false));
		expect(log['2026-11-11'].right).toBe(true);
		expect(loadLog()).toEqual(log);
	});

	it('drops malformed rows instead of throwing', () => {
		localStorage.setItem(
			QUOTE_GAME_KEY,
			JSON.stringify({ '2026-11-10': r(true), nonsense: r(true), '2026-11-09': { n: 'x' } })
		);
		expect(Object.keys(loadLog())).toEqual(['2026-11-10']);
		localStorage.setItem(QUOTE_GAME_KEY, '{not json');
		expect(loadLog()).toEqual({});
	});

	it('forgets days long past', () => {
		const log = recordResult({ '2020-01-01': r(true) }, '2026-11-11', r(true));
		expect(Object.keys(log)).toEqual(['2026-11-11']);
	});

	it('is reader data, wiped on sign-out', () => {
		expect(READING_DATA_KEYS).toContain(QUOTE_GAME_KEY);
	});
});

describe('gameStreak', () => {
	const log: GameLog = {
		'2026-11-05': r(true),
		'2026-11-06': r(false),
		'2026-11-07': r(true),
		'2026-11-08': r(true),
		'2026-11-09': r(true)
	};
	it('counts right answers running to today or yesterday', () => {
		expect(gameStreak(log, '2026-11-09')).toBe(3);
		expect(gameStreak(log, '2026-11-10')).toBe(3);
		expect(gameStreak(log, '2026-11-11')).toBe(0);
	});
	it('a wrong answer breaks it', () => {
		expect(gameStreak({ ...log, '2026-11-10': r(false) }, '2026-11-10')).toBe(0);
	});
});

describe('recentDays', () => {
	it('walks the last week oldest first', () => {
		const days = recentDays({ '2026-11-11': r(true), '2026-11-09': r(false) }, '2026-11-11', 3);
		expect(days).toEqual([
			{ day: '2026-11-09', state: 'wrong' },
			{ day: '2026-11-10', state: 'none' },
			{ day: '2026-11-11', state: 'right' }
		]);
	});
});

describe('resultLine', () => {
	it('reads as one line', () => {
		expect(resultLine({ title: 'Whose words?', number: 'No. 42', right: true, streak: '6-day streak' })).toBe(
			'Ochorus · Whose words? No. 42 ✓ · 6-day streak'
		);
		expect(resultLine({ title: 'Whose words?', number: 'No. 3', right: false, streak: '' })).toBe(
			'Ochorus · Whose words? No. 3 ✗'
		);
	});
});
