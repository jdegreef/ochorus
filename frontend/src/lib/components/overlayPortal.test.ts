import { createRawSnippet, flushSync, mount, unmount, type Component } from 'svelte';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import OverlayPortalHost from '../../test/OverlayPortalHost.svelte';
import CommandPalette from './CommandPalette.svelte';
import DefinePopover from './DefinePopover.svelte';
import FeedbackDialog from './FeedbackDialog.svelte';
import ListenBar from './ListenBar.svelte';
import ModalShell from './ModalShell.svelte';
import NoteDialog from './NoteDialog.svelte';
import PlanStartBar from './PlanStartBar.svelte';
import ScripturePopover from './ScripturePopover.svelte';
import UnsyncedSignOutDialog from './UnsyncedSignOutDialog.svelte';
import JournalDialog from './notebook/JournalDialog.svelte';
import { define } from '$lib/define.svelte';
import { listen } from '$lib/listen.svelte';
import { paletteUi } from '$lib/paletteUi.svelte';
import { scripture } from '$lib/scripture.svelte';

/**
 * The fixed overlays portal themselves to <body>, as DrawerShell does, so an
 * ancestor with a transform (the page-turn pager, `.page-col`) or a
 * backdrop-filter (the reader's bars) can't become their containing block.
 * DrawerShell.test.ts holds the pattern for the drawers; these hold it for
 * every other overlay, each dropped into the same transformed, fenced column:
 * it lands on <body>, goes away when it closes, and goes away when an ancestor
 * block or the whole host is torn down while it is open — without taking a
 * sibling with it.
 *
 * Two kinds: a DIALOG is open while its parent renders it (its root is
 * ModalShell's only root), and a POPOVER is always mounted and opens from a
 * store (its root is the only root of its own {#if}).
 */
type Host = { setMounted(v: boolean): void; setShown(v: boolean): void };

interface Case {
	name: string;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any -- each overlay has its own props
	overlay: Component<any>;
	props?: Record<string, unknown>;
	/** The portalled root, as a direct child of <body>. */
	root: string;
	/** For a popover: open or close it through its store. */
	store?: (open: boolean) => void;
}

const noop = () => {};

const CASES: Case[] = [
	{
		name: 'ModalShell',
		overlay: ModalShell,
		props: {
			onClose: noop,
			ariaLabel: 'Dialog',
			children: createRawSnippet(() => ({ render: () => '<p>body</p>' }))
		},
		root: '.modal-overlay'
	},
	{
		name: 'NoteDialog',
		overlay: NoteDialog,
		props: { text: '', color: 'yellow', onSave: noop, onRemove: noop, onClose: noop },
		root: '.modal-overlay'
	},
	{
		name: 'JournalDialog',
		overlay: JournalDialog,
		props: {
			kind: 'note',
			source: { kind: 'book', slug: 'b', order: 1, p: 0, edition: 'en', title: 'B · 1', quote: 'q' },
			onsave: noop,
			onclose: noop
		},
		root: '.modal-overlay'
	},
	{
		name: 'FeedbackDialog',
		overlay: FeedbackDialog,
		props: { source: 'fab', onClose: noop },
		root: '.modal-overlay'
	},
	{ name: 'UnsyncedSignOutDialog', overlay: UnsyncedSignOutDialog, root: '.modal-overlay' },
	{
		name: 'PlanStartBar',
		overlay: PlanStartBar,
		props: { href: '/plans/p/1', label: 'Start the plan', title: 'Day one', meta: 'Day 1 of 3' },
		root: '.plan-startbar'
	},
	{
		name: 'ScripturePopover',
		overlay: ScripturePopover,
		root: '.scripture-pop',
		store: (open) => (scripture.open = open)
	},
	{
		name: 'DefinePopover',
		overlay: DefinePopover,
		root: '.define-pop',
		store: (open) => (define.open = open)
	},
	{
		name: 'ListenBar',
		overlay: ListenBar,
		root: '.listen-bar',
		store: (open) => (listen.status = open ? 'paused' : 'idle')
	},
	{
		name: 'CommandPalette',
		overlay: CommandPalette,
		root: '.palette-overlay',
		store: (open) => (paletteUi.open = open)
	}
];

const read = (file: string) => readFileSync(join(import.meta.dirname, file), 'utf8');

let target: HTMLElement;
let host: Host | null = null;

const ids = () => [...target.querySelectorAll('[id]')].map((el) => el.id);
/** Everything on <body> that isn't the host — the portal, or a leak. */
const outside = () => [...document.body.children].filter((el) => el !== target);
const set = (fn: () => void) => {
	fn();
	flushSync();
};

// jsdom has no layout: ListenBar measures itself with a ResizeObserver, and the
// palette scrolls its active row into view.
beforeAll(() => {
	vi.stubGlobal(
		'ResizeObserver',
		class {
			observe() {}
			disconnect() {}
		}
	);
	Element.prototype.scrollIntoView = () => {};
});
afterAll(() => {
	vi.unstubAllGlobals();
	delete (Element.prototype as Partial<Element>).scrollIntoView;
});

afterEach(() => {
	if (host) unmount(host);
	host = null;
	target?.remove();
	// A leak is asserted where it happens; don't let it spill into the next test.
	outside().forEach((el) => el.remove());
});

describe.each(CASES)('$name portal', (c) => {
	const open = () => set(() => (c.store ? c.store(true) : host!.setMounted(true)));
	const close = () => set(() => (c.store ? c.store(false) : host!.setMounted(false)));

	afterEach(() => c.store?.(false));

	beforeEach(() => {
		target = document.createElement('div');
		document.body.appendChild(target);
		host = mount(OverlayPortalHost, {
			target,
			props: { overlay: c.overlay, props: c.props }
		}) as unknown as Host;
		flushSync();
		// A popover's component is always there; only its store opens it.
		if (c.store) set(() => host!.setMounted(true));
	});

	it('renders open as a direct child of <body>, outside the transformed column', () => {
		const before = ids();
		open();
		expect(outside()).toHaveLength(1);
		expect(outside()[0].matches(c.root)).toBe(true);
		expect(target.querySelector('#col')!.contains(outside()[0])).toBe(false);
		expect(ids()).toEqual(before);
	});

	it('opens and closes repeatedly without leaking or removing siblings', () => {
		const before = ids();
		for (let i = 0; i < 3; i++) {
			open();
			expect(outside()).toHaveLength(1);
			expect(ids()).toEqual(before);
			close();
			expect(outside()).toHaveLength(0);
			expect(ids()).toEqual(before);
		}
	});

	it('is removed when an ancestor block is torn down while it is open', () => {
		open();
		set(() => host!.setShown(false));
		expect(outside()).toHaveLength(0);
		expect(ids()).toEqual(['before', 'after']);

		set(() => host!.setShown(true));
		expect(ids()).toEqual(['before', 'col', 'col-first', 'col-last', 'after']);
		expect(outside()).toHaveLength(1); // still open: it comes back
		close();
		expect(outside()).toHaveLength(0);
	});

	it('is removed when the whole host unmounts while open', () => {
		open();
		unmount(host!);
		host = null;
		expect(outside()).toHaveLength(0);
		expect(target.childElementCount).toBe(0);
	});
});

/**
 * The overlays jsdom can't open — the selection bar needs a laid-out Range,
 * the testimony dialog a canvas, ReaderOverlays' notices a TTS voice lookup —
 * are held to the same shape in source: `use:portal` on the root, or the
 * testimony dialog rendered through ModalShell.
 */
describe('overlays that jsdom cannot open', () => {
	it.each([
		['SelectionBar.svelte', 'class="selbar"'],
		['ReaderOverlays.svelte', 'class="reader-dock listen-notice"'],
		['ReaderOverlays.svelte', 'class="saved-notice"'],
		['notebook/TestimonyDialog.svelte', '<ModalShell']
	])('%s: the %s root portals', (file, root) => {
		expect(read(file)).toMatch(
			root === '<ModalShell' ? /<\/script>\s*<ModalShell[\s\S]*<\/ModalShell>\s*(<style|$)/ : new RegExp(`${root}[^<]*?use:portal`)
		);
	});
});

/**
 * The centred dialogs get their overlay — portal, scrim, focus trap — from
 * ModalShell; the dialog cases above mount four of them through it. This holds
 * what the shell itself wires up.
 */
describe('ModalShell', () => {
	it('names the dialog and closes on Escape from inside', () => {
		const onClose = vi.fn();
		const target = document.createElement('div');
		document.body.appendChild(target);
		const shell = mount(ModalShell, {
			target,
			props: {
				onClose,
				role: 'alertdialog',
				ariaLabelledby: 'shell-title',
				ariaDescribedby: 'shell-body',
				width: '26rem',
				children: createRawSnippet(() => ({ render: () => '<button id="inside">ok</button>' }))
			}
		});
		flushSync();
		const overlay = document.body.querySelector(':scope > .modal-overlay')!;
		expect(overlay.getAttribute('role')).toBe('alertdialog');
		expect(overlay.getAttribute('aria-modal')).toBe('true');
		expect(overlay.getAttribute('aria-labelledby')).toBe('shell-title');
		expect(overlay.getAttribute('aria-describedby')).toBe('shell-body');
		expect(overlay.hasAttribute('aria-label')).toBe(false);
		expect((overlay.querySelector('.modal-card') as HTMLElement).style.maxWidth).toBe('26rem');

		document.getElementById('inside')!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
		expect(onClose).toHaveBeenCalledOnce();

		unmount(shell);
		target.remove();
		expect(document.body.querySelector(':scope > .modal-overlay')).toBeNull();
	});
});
