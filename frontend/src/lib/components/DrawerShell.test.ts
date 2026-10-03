import { flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import DrawerShellHost from '../../test/DrawerShellHost.svelte';

/**
 * DrawerShell portals its scrim + panel to <body>, so an ancestor with a
 * transform (the page-turn pager) or backdrop-filter (the reader's bars) can't become
 * the containing block for the fixed panel. Moving DOM out from under Svelte 5
 * is only safe if block teardown still removes exactly what it should — these
 * hold that across open/close cycles and an ancestor block going away.
 */
type Host = { setOpen(v: boolean): void; setShown(v: boolean): void; isOpen(): boolean };

let target: HTMLElement;
let host: Host | null = null;

const ids = () => [...target.querySelectorAll('[id]')].map((el) => el.id);
const portals = () => document.body.querySelectorAll(':scope > .drawer-portal');
const set = (fn: () => void) => {
	fn();
	flushSync();
};

beforeEach(() => {
	target = document.createElement('div');
	document.body.appendChild(target);
	host = mount(DrawerShellHost, { target }) as unknown as Host;
	flushSync();
});

afterEach(() => {
	if (host) unmount(host);
	host = null;
	target.remove();
	// A leak is asserted where it happens; don't let it spill into the next test.
	portals().forEach((el) => el.remove());
});

describe('DrawerShell portal', () => {
	it('renders the open drawer as a direct child of <body>, outside the transformed column', () => {
		set(() => host!.setOpen(true));
		expect(portals()).toHaveLength(1);
		const panel = portals()[0].querySelector('[role="dialog"]');
		expect(panel?.querySelector('#drawer-body')).not.toBeNull();
		expect(target.querySelector('#col')!.contains(panel)).toBe(false);
		expect(portals()[0].querySelector('.drawer-scrim')).not.toBeNull();
	});

	it('opens and closes repeatedly without leaking or removing siblings', () => {
		const before = ids();
		for (let i = 0; i < 5; i++) {
			set(() => host!.setOpen(true));
			expect(portals()).toHaveLength(1);
			expect(ids()).toEqual(before);
			set(() => host!.setOpen(false));
			expect(portals()).toHaveLength(0);
			expect(ids()).toEqual(before);
		}
	});

	it('closes from the scrim and the close button, through the bound prop', () => {
		set(() => host!.setOpen(true));
		set(() => (portals()[0].querySelector('.drawer-scrim') as HTMLElement).click());
		expect(host!.isOpen()).toBe(false);
		expect(portals()).toHaveLength(0);

		set(() => host!.setOpen(true));
		set(() => (portals()[0].querySelector('header button') as HTMLElement).click());
		expect(host!.isOpen()).toBe(false);
		expect(portals()).toHaveLength(0);
	});

	it('closes on Escape from inside the moved panel and returns focus to the opener', async () => {
		const opener = document.createElement('button');
		document.body.appendChild(opener);
		opener.focus();
		set(() => host!.setOpen(true));
		await Promise.resolve(); // let focusTrap's own focus-in microtask run first
		// jsdom has no layout, so focusTrap's auto-focus can't pick a target here.
		const body = document.getElementById('drawer-body')!;
		body.focus();

		set(() => body.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })));
		expect(host!.isOpen()).toBe(false);
		expect(portals()).toHaveLength(0);
		expect(document.activeElement).toBe(opener);
		opener.remove();
	});

	it('is removed when an ancestor block is torn down while it is open', () => {
		set(() => host!.setOpen(true));
		set(() => host!.setShown(false));
		expect(portals()).toHaveLength(0);
		expect(ids()).toEqual(['before', 'after']);

		set(() => host!.setShown(true));
		expect(ids()).toEqual(['before', 'col', 'col-first', 'col-last', 'after']);
		expect(portals()).toHaveLength(1); // still bound open: it comes back
		set(() => host!.setOpen(false));
		expect(portals()).toHaveLength(0);
	});

	it('is removed when the whole component unmounts while open', () => {
		set(() => host!.setOpen(true));
		unmount(host!);
		host = null;
		expect(portals()).toHaveLength(0);
		expect(target.childElementCount).toBe(0);
	});
});
