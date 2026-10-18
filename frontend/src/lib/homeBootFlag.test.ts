import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { PROGRESS_KEY } from './reading-schema';

/**
 * app.html's boot script flags, before first paint, a home page that will not
 * stay the prerendered newcomer page — a signed-in reader (dashboard) or a
 * returning one ("Continue reading") — so the page holds back until it has
 * settled instead of jumping (`data-home-for`; see src/routes/+page.svelte).
 * Run that block of the real script against this test's localStorage.
 */
const html = readFileSync(join(process.cwd(), 'src/app.html'), 'utf-8');
const block = /try \{\s*\/\/ Whose home page this is[\s\S]*?\} catch \(e\) \{\}/.exec(html)?.[0];

function flag(): string | null {
	document.documentElement.removeAttribute('data-home-for');
	new Function(block!)();
	return document.documentElement.getAttribute('data-home-for');
}

describe('the home boot flag', () => {
	afterEach(() => localStorage.clear());

	it('is in app.html, reading the key the progress store writes', () => {
		expect(block).toBeTruthy();
		expect(block).toContain(`'${PROGRESS_KEY}'`);
	});

	it('leaves a newcomer (and a crawler) on the prerendered page', () => {
		expect(flag()).toBeNull();
		localStorage.setItem(PROGRESS_KEY, '{}');
		expect(flag()).toBeNull();
	});

	it('marks a returning reader', () => {
		localStorage.setItem(PROGRESS_KEY, JSON.stringify({ 'some-book': { order: 2, at: 1 } }));
		expect(flag()).toBe('reader');
	});

	it('marks a signed-in reader by the supabase-js session key, ahead of reading history', () => {
		localStorage.setItem(PROGRESS_KEY, JSON.stringify({ 'some-book': { order: 2, at: 1 } }));
		localStorage.setItem('sb-abcdefgh-auth-token', '{}');
		expect(flag()).toBe('member');
	});
});
