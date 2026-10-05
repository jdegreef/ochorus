import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { beforeEach, describe, expect, it } from 'vitest';
import {
	SIGNUP_SOURCES,
	SOURCE_TTL_MS,
	isSignupSource,
	noteSignupSource,
	signupSource,
	withSource
} from './signupSource';

beforeEach(() => localStorage.clear());

describe('signupSource — which prompt a sign-up is credited to', () => {
	it('is null when the reader followed no prompt and saw no band', () => {
		expect(signupSource()).toBeNull();
	});

	it('credits the prompt the reader followed', () => {
		noteSignupSource('bookshelf', 1000);
		expect(signupSource(2000)).toBe('bookshelf');
	});

	it('gives the credit to the last prompt followed', () => {
		noteSignupSource('article', 1000);
		noteSignupSource('chapter_end', 2000);
		expect(signupSource(3000)).toBe('chapter_end');
	});

	it('lets the credit lapse after a day', () => {
		noteSignupSource('quote', 0);
		expect(signupSource(SOURCE_TTL_MS - 1)).toBe('quote');
		expect(signupSource(SOURCE_TTL_MS)).toBeNull();
	});


	it('ignores a junk or future-dated stored value', () => {
		localStorage.setItem('ochorus:signup_source', JSON.stringify({ source: 'nope', at: 0 }));
		expect(signupSource(1)).toBeNull();
		localStorage.setItem('ochorus:signup_source', JSON.stringify({ source: 'footer', at: 50 }));
		expect(signupSource(10)).toBeNull();
	});

	it('only accepts known sources', () => {
		expect(isSignupSource('notebook')).toBe(true);
		expect(isSignupSource('habit')).toBe(true);
		expect(isSignupSource('anything')).toBe(false);
		expect(isSignupSource(null)).toBe(false);
	});
});

describe('withSource', () => {
	it('adds src to a bare or queried href', () => {
		expect(withSource('/login', 'footer')).toBe('/login?src=footer');
		expect(withSource('/login?mode=signup', 'article')).toBe('/login?mode=signup&src=article');
	});
});

describe('the backend accepts exactly these sources', () => {
	it('matches accounts.models.SIGNUP_VARIANTS', () => {
		const models = readFileSync(resolve(__dirname, '../../../backend/accounts/models.py'), 'utf8');
		const tuple = models.match(/SIGNUP_VARIANTS = \(([\s\S]*?)\n\)/);
		expect(tuple).not.toBeNull();
		const backend = [...tuple![1].matchAll(/"([a-z_]+)"/g)].map((m) => m[1]);
		expect(backend).toEqual([...SIGNUP_SOURCES]);
	});
});
