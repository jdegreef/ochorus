import { beforeEach, describe, expect, it } from 'vitest';
import { hasStarted, readerActivity } from './readerActivity';

beforeEach(() => localStorage.clear());

describe('readerActivity', () => {
	it('reports nothing done on a fresh device', () => {
		expect(readerActivity('en')).toEqual({ read: false, saved: false, marked: false });
		expect(hasStarted(readerActivity('en'))).toBe(false);
	});

	it('counts reading or saving as having started, not marking alone', () => {
		expect(hasStarted({ read: true, saved: false, marked: false })).toBe(true);
		expect(hasStarted({ read: false, saved: true, marked: false })).toBe(true);
		expect(hasStarted({ read: false, saved: false, marked: true })).toBe(false);
	});
});
