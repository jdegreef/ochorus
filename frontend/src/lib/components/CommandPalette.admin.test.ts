/**
 * The palette's admin shortcuts: admin sections for a viewer who can open them,
 * and an "Admin" action beside a book/sermon hit. None of it reaches a reader.
 */
import { flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { gotoSpy, searchSpy } = vi.hoisted(() => ({ gotoSpy: vi.fn(), searchSpy: vi.fn() }));
vi.mock('$app/navigation', () => ({ goto: gotoSpy, preloadCode: vi.fn() }));
vi.mock('$lib/library-public', async (orig) => ({
	...(await orig<typeof import('$lib/library-public')>()),
	search: searchSpy
}));

import CommandPalette from './CommandPalette.svelte';
import { auth } from '$lib/auth.svelte';
import { paletteUi } from '$lib/paletteUi.svelte';

let app: ReturnType<typeof mount> | null = null;

function open() {
	app = mount(CommandPalette, { target: document.body });
	paletteUi.openPalette();
	flushSync();
}
function type(text: string) {
	const input = document.querySelector<HTMLInputElement>('[role="dialog"] input')!;
	input.value = text;
	input.dispatchEvent(new Event('input', { bubbles: true }));
	flushSync();
	return input;
}
const rows = () =>
	[...document.querySelectorAll('[role="dialog"] li')].map((li) => li.textContent!.replace(/\s+/g, ' ').trim());

beforeEach(() => {
	vi.useFakeTimers();
	// jsdom has no layout: the palette keeps its active row in view with this.
	Element.prototype.scrollIntoView = vi.fn();
	searchSpy.mockResolvedValue({
		results: [
			{ type: 'book', book_slug: 'humility', book_title: 'Humility', author_name: 'Andrew Murray' },
			{ type: 'sermon', sermon_slug: 'do-you-pray', sermon_title: 'Do You Pray?', author_name: 'J. C. Ryle' }
		]
	});
});
afterEach(() => {
	paletteUi.close();
	if (app) unmount(app);
	app = null;
	auth.scopes = [];
	auth.isAdmin = false;
	vi.useRealTimers();
	gotoSpy.mockReset();
});

describe('CommandPalette admin shortcuts', () => {
	it('shows a reader no admin rows', async () => {
		open();
		type('review');
		expect(rows().some((r) => r.startsWith('Admin'))).toBe(false);
		type('humility');
		await vi.advanceTimersByTimeAsync(250);
		flushSync();
		expect(document.querySelector('[aria-label^="Open Humility in admin"]')).toBeNull();
	});

	it('lists the sections a super admin can open once something is typed', () => {
		auth.isAdmin = true;
		auth.scopes = 'all';
		open();
		// Empty: the reader's page list only.
		expect(rows().some((r) => r.startsWith('Admin'))).toBe(false);
		type('review');
		expect(rows()).toContain('Admin Review queue');
		type('admin');
		expect(rows().filter((r) => r.startsWith('Admin')).length).toBeGreaterThan(10);
	});

	it('offers a scoped grantee only the sections their grant opens', () => {
		auth.scopes = [{ capability: 'review', verb: 'approve', languages: ['es'] }] as typeof auth.scopes;
		open();
		type('admin');
		const admin = rows().filter((r) => r.startsWith('Admin'));
		expect(admin).toContain('Admin Review queue');
		expect(admin).toContain('Admin Help & roles');
		expect(admin).not.toContain('Admin Team & access');
		expect(admin).not.toContain('Admin Coverage matrix');
	});

	it('puts an Admin action on book and sermon hits, and ⌘↵ follows it', async () => {
		auth.isAdmin = true;
		auth.scopes = 'all';
		open();
		const input = type('humility');
		await vi.advanceTimersByTimeAsync(250);
		flushSync();
		const link = document.querySelector<HTMLAnchorElement>('[aria-label="Open Humility in admin"]');
		expect(link?.getAttribute('href')).toMatch(/\/admin\/books\/humility\/?$/);
		expect(document.querySelector('[aria-label="Open Do You Pray? in admin"]')).not.toBeNull();
		// Down past "Show all results" to the book hit, then ⌘↵.
		const key = (k: string, extra: KeyboardEventInit = {}) =>
			input.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, ...extra }));
		const at = rows().findIndex((r) => r.includes('Humility'));
		for (let i = 0; i < at; i++) key('ArrowDown');
		flushSync();
		key('Enter', { metaKey: true });
		expect(gotoSpy).toHaveBeenLastCalledWith(expect.stringMatching(/\/admin\/books\/humility\/?$/));
		// Plain ↵ still opens the reader page.
		key('Enter');
		expect(gotoSpy).toHaveBeenLastCalledWith(expect.stringMatching(/\/books\/humility\/?$/));
		expect(gotoSpy.mock.lastCall![0]).not.toContain('/admin/');
	});
});
