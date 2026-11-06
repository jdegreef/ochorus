import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { ACTIVITY_KEY, PLANS_KEY, PROGRESS_KEY, RESUME_BOOKS_KEY } from './reading-schema';
import { SCHEMA as RESUME_SCHEMA } from './resumeBooks';
import { localToday, shiftDay } from './streak';
import { storedSessionUser } from './auth.svelte';

/**
 * app.html's boot script flags, before first paint, a home page that will not
 * stay the prerendered newcomer page — a signed-in reader (dashboard) or a
 * returning one ("Continue reading") — so the page holds back until it has
 * settled instead of jumping (`data-home-for`; see src/routes/+page.svelte).
 * Run that block of the real script against this test's localStorage.
 */
const html = readFileSync(join(process.cwd(), 'src/app.html'), 'utf-8');
const block = /try \{\s*\/\/ Whose home page this is[\s\S]*?\} catch \(e\) \{\}/.exec(html)?.[0];

const SESSION = { access_token: 'x', refresh_token: 'y', user: { email: 'a@b.c' } };
const ATTRS = ['data-home-for', 'data-home-cards', 'data-home-nudge', 'data-home-resume', 'data-home-plan'];
const root = () => document.documentElement;

function flag(): string | null {
	for (const a of ATTRS) root().removeAttribute(a);
	new Function(block!)();
	return root().getAttribute('data-home-for');
}

const at = (back: number) => shiftDay(localToday(), -back);

describe('the home boot flag', () => {
	afterEach(() => localStorage.clear());

	it('is in app.html, reading the keys (and cache schema) the stores write', () => {
		expect(block).toBeTruthy();
		for (const key of [PROGRESS_KEY, ACTIVITY_KEY, RESUME_BOOKS_KEY, PLANS_KEY]) expect(block).toContain(`'${key}'`);
		expect(block).toContain(`rb.schema === ${RESUME_SCHEMA}`);
	});

	it('leaves a newcomer (and a crawler) on the prerendered page', () => {
		expect(flag()).toBeNull();
		localStorage.setItem(PROGRESS_KEY, '{}');
		expect(flag()).toBeNull();
		expect(root().getAttribute('data-home-cards')).toBeNull();
	});

	it('marks a returning reader', () => {
		localStorage.setItem(PROGRESS_KEY, JSON.stringify({ 'sermon:some-sermon': { order: 1, at: 1 } }));
		expect(flag()).toBe('reader');
		expect(root().getAttribute('data-home-cards')).toBe('1');
		expect(root().getAttribute('data-home-nudge')).toBeNull();
		expect(root().getAttribute('data-home-resume')).toBeNull();
	});

	// Design #10: the book the reader is in takes the hero's place (HomeResume),
	// so it is not one of the strip's slots.
	it("marks a reader with a book open for Continue reading in the hero's place", () => {
		localStorage.setItem(PROGRESS_KEY, JSON.stringify({ 'some-book': { order: 2, at: 1 } }));
		expect(flag()).toBe('reader');
		expect(root().getAttribute('data-home-resume')).toBe('');
		expect(root().getAttribute('data-home-cards')).toBe('0');
		expect(root().getAttribute('data-home-plan')).toBeNull();
		localStorage.setItem(PLANS_KEY, JSON.stringify({ 'some-plan': { startedAt: 1, done: [1] } }));
		flag();
		expect(root().getAttribute('data-home-plan')).toBe('');
		// A plan alone, with no book, leaves the hero where it is.
		localStorage.removeItem(PROGRESS_KEY);
		expect(flag()).toBeNull();
		expect(root().getAttribute('data-home-resume')).toBeNull();
		expect(root().getAttribute('data-home-plan')).toBeNull();
	});

	it('takes the newest unfinished book this language has as the current one', () => {
		localStorage.setItem(
			PROGRESS_KEY,
			JSON.stringify({ old: { order: 1, at: 1 }, gone: { order: 1, at: 3 }, newer: { order: 1, at: 2 } })
		);
		localStorage.setItem(
			RESUME_BOOKS_KEY,
			JSON.stringify({ schema: RESUME_SCHEMA, books: {}, absent: { en: ['gone'] } })
		);
		flag();
		expect(root().getAttribute('data-home-resume')).toBe('');
		// `newer` is the block's; `old` is the strip's one card.
		expect(root().getAttribute('data-home-cards')).toBe('1');
	});

	it("counts the strip's slots as ContinueReading draws them at mount", () => {
		const progress = {
			a: { order: 2, at: 1 },
			'sermon:b': { order: 1, at: 2 },
			done: { order: 9, at: 3, finished_at: '2026-01-01' },
			'bio:c': { order: 1, at: 4 },
			'article:d': { order: 1, at: 5 },
			gone: { order: 1, at: 6 }
		};
		localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
		localStorage.setItem(
			RESUME_BOOKS_KEY,
			JSON.stringify({ schema: RESUME_SCHEMA, books: {}, absent: { en: ['gone'] } })
		);
		flag();
		// `a`, the one book, is the block's (design #10); `sermon:b` is left.
		expect(root().getAttribute('data-home-cards')).toBe('1');
		// Another shape of the cache is ignored, as resumeBooks ignores it.
		localStorage.setItem(RESUME_BOOKS_KEY, JSON.stringify({ schema: -1, absent: { en: ['gone'] } }));
		flag();
		// `gone` (the newest book) is now the block's; `a` and `sermon:b` are left.
		expect(root().getAttribute('data-home-cards')).toBe('2');
		// At most the strip's four.
		const many = Object.fromEntries([...'abcdefg'].map((s, i) => [s, { order: 1, at: i }]));
		localStorage.setItem(PROGRESS_KEY, JSON.stringify(many));
		flag();
		expect(root().getAttribute('data-home-cards')).toBe('4');
	});

	it('says whether, and how, the reading nudge will show', () => {
		localStorage.setItem(ACTIVITY_KEY, JSON.stringify([at(5)]));
		expect(flag()).toBe('reader');
		expect(root().getAttribute('data-home-cards')).toBe('0');
		expect(root().getAttribute('data-home-nudge')).toBe('on');
		localStorage.setItem(ACTIVITY_KEY, JSON.stringify([at(1)]));
		flag();
		expect(root().getAttribute('data-home-nudge')).toBe('on streak');
		localStorage.setItem(ACTIVITY_KEY, JSON.stringify([at(1), at(0)]));
		flag();
		expect(root().getAttribute('data-home-nudge')).toBe('on streak today');
	});

	it('marks a signed-in reader by the supabase-js session key, ahead of reading history', () => {
		localStorage.setItem(PROGRESS_KEY, JSON.stringify({ 'some-book': { order: 2, at: 1 } }));
		localStorage.setItem('sb-abcdefgh-auth-token', JSON.stringify(SESSION));
		expect(flag()).toBe('member');
		expect(root().getAttribute('data-home-cards')).toBeNull();
	});

	it('agrees with storedSessionUser on what counts as a session', () => {
		localStorage.setItem(PROGRESS_KEY, JSON.stringify({ 'some-book': { order: 2, at: 1 } }));
		for (const value of ['{}', '{not json', JSON.stringify(SESSION)]) {
			localStorage.setItem('sb-abcdefgh-auth-token', value);
			expect(flag()).toBe(storedSessionUser() ? 'member' : 'reader');
		}
	});
});

// The dashboard draws at mount from the session the boot flag saw, not the
// one auth.init() restores later (src/routes/+page.svelte).
describe('storedSessionUser', () => {
	afterEach(() => localStorage.clear());

	it("reads the stored supabase-js session's account, synchronously", () => {
		expect(storedSessionUser()).toBeNull();
		localStorage.setItem(
			'sb-abcdefgh-auth-token',
			JSON.stringify({ access_token: 'x', refresh_token: 'y', user: { email: 'a@b.c' } })
		);
		expect(storedSessionUser()).toEqual({ email: 'a@b.c' });
	});

	it('finds none in an unreadable session, or in the PKCE verifier key', () => {
		localStorage.setItem('sb-abcdefgh-auth-token', '{not json');
		expect(storedSessionUser()).toBeNull();
		localStorage.setItem('sb-abcdefgh-auth-token', '{}');
		expect(storedSessionUser()).toBeNull();
		localStorage.clear();
		localStorage.setItem('sb-abcdefgh-auth-token-code-verifier', '"v"');
		expect(storedSessionUser()).toBeNull();
	});
});
