import { flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { BookSummary } from '$lib/library-public';

/**
 * The Bookshelf's "Bookplates": one plate per finished book, made out to the
 * account's name — or, with no name yet, a place to write one.
 */
vi.mock('$lib/lang.svelte', () => ({ getLang: () => 'en' }));
const auth = vi.hoisted(() => ({ displayName: '', user: { email: 'm@example.com' }, setDisplayName: vi.fn() }));
vi.mock('$lib/auth.svelte', () => ({ auth }));

const { default: BookplatesShelf } = await import('./BookplatesShelf.svelte');

const book = (slug: string, title: string): BookSummary =>
	({ slug, title, language: 'en', author: { slug: 'spurgeon', name: 'C. H. Spurgeon', birth_year: 1834 } }) as unknown as BookSummary;
const row = (slug: string, finished_at: number | null) => ({
	slug,
	kind: 'book' as const,
	order: 1,
	paragraph_index: 0,
	language: 'en',
	at: 1,
	finished_at,
	furthest: 1
});

let target: HTMLElement;
let component: ReturnType<typeof mount> | null = null;
beforeEach(() => {
	target = document.createElement('div');
	document.body.appendChild(target);
});
afterEach(() => {
	if (component) unmount(component);
	component = null;
	target.remove();
	auth.displayName = '';
});

function render(progress: ReturnType<typeof row>[], books: BookSummary[]) {
	component = mount(BookplatesShelf, { target, props: { progress, books } });
	flushSync();
}

describe('BookplatesShelf', () => {
	it('shows nothing until a book is finished', () => {
		render([row('all-of-grace', null)], [book('all-of-grace', 'All of Grace')]);
		expect(target.querySelector('#bookplates')).toBeNull();
	});

	it('lists a plate per finished book, newest first, made out to the reader', () => {
		auth.displayName = 'Mary Okonkwo';
		render(
			[row('all-of-grace', Date.UTC(2026, 10, 11, 12)), row('humility', Date.UTC(2026, 11, 1, 12))],
			[book('all-of-grace', 'All of Grace'), book('humility', 'Humility')]
		);
		const plates = [...target.querySelectorAll('.plate')];
		expect(plates).toHaveLength(2);
		expect(plates[0].textContent).toContain('Humility');
		expect(plates[1].textContent).toContain('All of Grace');
		expect(plates[1].textContent).toContain('EX LIBRIS');
		expect(plates[1].textContent).toContain('Mary Okonkwo');
		expect(plates[1].textContent).toContain('November 11, 2026');
		expect(target.querySelector('#bookplate-name')).toBeNull();
		expect(target.querySelectorAll('.plate-grid button')).toHaveLength(2);
	});

	it('asks for a name, and offers no image, when the account has none', () => {
		render([row('all-of-grace', 5)], [book('all-of-grace', 'All of Grace')]);
		expect(target.querySelector('#bookplate-name')).not.toBeNull();
		expect(target.querySelectorAll('.plate-grid button')).toHaveLength(0);
	});

	it('shows six at first, and the rest on request', () => {
		auth.displayName = 'Mary';
		const slugs = Array.from({ length: 8 }, (_, i) => `b${i}`);
		render(
			slugs.map((s, i) => row(s, i + 1)),
			slugs.map((s) => book(s, s))
		);
		expect(target.querySelectorAll('.plate')).toHaveLength(6);
		const more = [...target.querySelectorAll('button')].find((b) => !b.closest('.plate-grid'))!;
		more.click();
		flushSync();
		expect(target.querySelectorAll('.plate')).toHaveLength(8);
	});
});
