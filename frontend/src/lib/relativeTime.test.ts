import { describe, it, expect } from 'vitest';
import { relativeTime } from './relativeTime';

const NOW = 1_750_000_000_000;

describe('relativeTime', () => {
	it('uses the just-now label under 45 seconds', () => {
		expect(relativeTime(NOW - 10_000, 'en', 'just now', NOW)).toBe('just now');
	});

	it('formats minutes, hours and days in the past', () => {
		expect(relativeTime(NOW - 5 * 60_000, 'en', 'x', NOW)).toBe('5 minutes ago');
		expect(relativeTime(NOW - 3 * 3_600_000, 'en', 'x', NOW)).toBe('3 hours ago');
		expect(relativeTime(NOW - 2 * 86_400_000, 'en', 'x', NOW)).toBe('2 days ago');
	});

	it('rolls up to months for older timestamps', () => {
		expect(relativeTime(NOW - 40 * 86_400_000, 'en', 'x', NOW)).toBe('last month');
	});
});
