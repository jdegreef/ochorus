import { afterEach, describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { holdFlag, markTabBar, TABBAR_FLAG } from './presenceFlag';

const SRC = join(process.cwd(), 'src');
const read = (rel: string) => readFileSync(join(SRC, rel), 'utf-8');
/** Source minus comments, so prose naming the old selector doesn't trip the guard. */
const code = (rel: string) =>
	read(rel)
		.replace(/\/\*[\s\S]*?\*\//g, '')
		.replace(/^\s*\/\/.*$/gm, '');

describe('holdFlag', () => {
	afterEach(() => {
		document.documentElement.removeAttribute('data-x');
	});

	it('sets the attribute while held and clears it on release', () => {
		const release = holdFlag(document.documentElement, 'data-x');
		expect(document.documentElement.hasAttribute('data-x')).toBe(true);
		release();
		expect(document.documentElement.hasAttribute('data-x')).toBe(false);
	});

	it('is reference-counted: the flag stays until the last holder lets go', () => {
		const a = holdFlag(document.documentElement, 'data-x');
		const b = holdFlag(document.documentElement, 'data-x');
		a();
		a(); // a second release of the same hold is a no-op
		expect(document.documentElement.hasAttribute('data-x')).toBe(true);
		b();
		expect(document.documentElement.hasAttribute('data-x')).toBe(false);
	});
});

describe('markTabBar', () => {
	it('flags <html> when the prerendered page carries the tab bar', () => {
		const html = '<html lang="en" dir="ltr"><body><nav class="tabbar svelte-abc" aria-label="Tabs"></nav>';
		expect(markTabBar(html)).toMatch(new RegExp(`^<html ${TABBAR_FLAG} lang="en"`));
	});

	it('leaves a page without the bar alone', () => {
		const html = '<html lang="en"><body><nav class="tabbar-ish"></nav><div class="x tabbar"></div>';
		expect(markTabBar(html)).toBe(html);
	});
});

describe('no document-wide :has() for chrome presence', () => {
	// `:root:has(…)` / `body:has(…)` restyle the whole page whenever a matching
	// element comes or goes — the flags above replace them.
	it.each([
		'app.css',
		'lib/components/TabBar.svelte',
		'lib/components/FeedbackFab.svelte',
		'lib/components/ReadBar.svelte',
		'lib/components/FootFeedback.svelte'
	])('%s', (file) => {
		expect(code(file)).not.toMatch(/(:root|html|body):has\(/);
	});
});
