import { beforeEach, describe, expect, it } from 'vitest';
import { readJSON, writeJSON } from './persisted';

beforeEach(() => localStorage.clear());

describe('readJSON', () => {
	it('returns the fallback when the key is absent', () => {
		expect(readJSON('missing', { a: 1 })).toEqual({ a: 1 });
	});

	it('returns the fallback when the stored value is corrupt', () => {
		localStorage.setItem('bad', '{not json');
		expect(readJSON('bad', [])).toEqual([]);
	});

	it('parses a stored JSON value', () => {
		localStorage.setItem('good', JSON.stringify({ x: [1, 2] }));
		expect(readJSON('good', null)).toEqual({ x: [1, 2] });
	});
});

describe('writeJSON', () => {
	it('round-trips a value through localStorage', () => {
		writeJSON('k', { hello: 'world', n: 3 });
		expect(readJSON('k', null)).toEqual({ hello: 'world', n: 3 });
	});
});
