import { beforeEach, describe, expect, it } from 'vitest';
import { claimStamps, freshSeals, SEAL_STAMPED_KEY } from './sealStamp';

describe('seal stamps', () => {
	beforeEach(() => localStorage.clear());

	it('keeps only the keys not yet stamped, in order', () => {
		expect(freshSeals(['first', 'five', 'pupil:bunyan'], ['five'])).toEqual(['first', 'pupil:bunyan']);
	});

	it('stamps a seal the first time it is claimed and never again', () => {
		expect([...claimStamps(['first', 'five'])]).toEqual(['first', 'five']);
		expect([...claimStamps(['first', 'five'])]).toEqual([]);
		expect([...claimStamps(['five', 'week'])]).toEqual(['week']);
		expect(JSON.parse(localStorage.getItem(SEAL_STAMPED_KEY)!)).toEqual(['first', 'five', 'week']);
	});

	it('treats a corrupt record as nothing stamped', () => {
		localStorage.setItem(SEAL_STAMPED_KEY, '{"not":"a list"}');
		expect([...claimStamps(['first'])]).toEqual(['first']);
	});
});
