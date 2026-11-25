import { describe, expect, it } from 'vitest';
import { levelProgress, pulseTiles, waitedFor, weekLabel } from './adminDashboard';

const series = (d7: number, d7_prev: number, weekly = [1, 2]) => ({
	d7,
	d7_prev,
	d30: d7 * 4,
	d30_prev: d7_prev * 4,
	weekly
});
const pulse = {
	readers: series(120, 100),
	signups: series(5, 0),
	reading_seconds: series(7200, 3600),
	zero_searches: series(40, 30),
	weeks: ['2026-11-16', '2026-11-23']
};

describe('pulseTiles', () => {
	const tiles = pulseTiles(pulse);

	it('shows the last 7 days against the 7 before', () => {
		expect(tiles[0]).toMatchObject({ label: 'Readers · 7d', value: '120', sub: '480 in 30 days' });
		expect(tiles[0].trend).toEqual({ dir: 'up', text: '+20%' });
		expect(tiles[1].trend).toEqual({ dir: 'up', text: 'new' });
	});

	it('formats reading time as a duration', () => {
		expect(tiles[2].value).toBe('2h');
	});

	it('reads more failed searches as bad, fewer as good', () => {
		expect(tiles[3].trend?.bad).toBe(true);
		const fewer = pulseTiles({ ...pulse, zero_searches: series(10, 30) });
		expect(fewer[3].trend?.bad).toBe(false);
	});

	it('labels each point by its week', () => {
		expect(tiles[0].labels).toEqual([weekLabel('2026-11-16'), weekLabel('2026-11-23')]);
		expect(weekLabel('2026-11-23')).toBe('week of Nov 23');
	});
});

describe('levelProgress / waitedFor', () => {
	it('rounds the share and survives an empty target', () => {
		expect(levelProgress({ done: 89, total: 255 })).toEqual({ pct: 35, text: '89 / 255' });
		expect(levelProgress({ done: 0, total: 0 }).pct).toBe(0);
	});

	it('counts whole days waited', () => {
		const now = new Date('2026-11-25T12:00:00Z');
		expect(waitedFor('2026-11-24T13:00:00Z', now)).toBe('0 days');
		expect(waitedFor('2026-11-24T11:00:00Z', now)).toBe('1 day');
		expect(waitedFor('2026-07-06T02:25:11Z', now)).toBe('142 days');
	});
});
