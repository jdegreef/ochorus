import { flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { BookDetail } from '$lib/library-public';

/**
 * The finish panel's bookplate: made out to the account's name; for a reader
 * signed out, left blank with an offer to sign in to keep it — the plate
 * itself is never withheld.
 */
vi.mock('$lib/lang.svelte', () => ({ getLang: () => 'en' }));
vi.mock('$lib/progress', () => ({
	getProgressRecord: () => ({ finished_at: Date.UTC(2026, 10, 11, 12) })
}));
const auth = vi.hoisted(() => ({
	enabled: true,
	initialized: true,
	displayName: '',
	user: null as { email: string } | null,
	setDisplayName: () => {}
}));
vi.mock('$lib/auth.svelte', () => ({ auth }));
vi.mock('$lib/signupSource', async (orig) => ({
	...(await orig<typeof import('$lib/signupSource')>()),
	seenOnView: () => ({})
}));

const { default: BookplatePanel } = await import('./BookplatePanel.svelte');

const book = {
	slug: 'all-of-grace',
	title: 'All of Grace',
	language: 'en',
	author: { slug: 'charles-spurgeon', name: 'C. H. Spurgeon', birth_year: 1834 }
} as unknown as BookDetail;

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
	auth.user = null;
	auth.displayName = '';
});
const render = () => {
	component = mount(BookplatePanel, { target, props: { book } });
	flushSync();
};

describe('BookplatePanel', () => {
	it('signed out: a blank plate, and sign-up credited to the bookplate', () => {
		render();
		expect(target.querySelector('.plate')?.textContent).toContain('All of Grace');
		expect(target.querySelector('.owner')).toBeNull();
		const cta = target.querySelector<HTMLAnchorElement>('a.btn-primary')!;
		expect(cta.getAttribute('href')).toContain('src=bookplate');
		expect(cta.getAttribute('href')).toContain('mode=signup');
	});

	it('signed in with a name: the plate is theirs, dated, and can be saved', () => {
		auth.user = { email: 'm@example.com' };
		auth.displayName = 'Mary Okonkwo';
		render();
		expect(target.querySelector('.owner')?.textContent).toBe('Mary Okonkwo');
		expect(target.querySelector('.date')?.textContent).toBe('November 11, 2026');
		expect(target.querySelector('a.btn-primary')).toBeNull();
		expect(target.querySelector('button')?.textContent?.trim()).toBe('Save as image');
	});

	it('signed in without a name: they write one on the blank line', () => {
		auth.user = { email: 'm@example.com' };
		render();
		expect(target.querySelector('#bookplate-name')).not.toBeNull();
	});
});
