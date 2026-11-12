import { flushSync, mount, tick, unmount } from 'svelte';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

/**
 * The Modern English column of "Side by side": fetched through the API client,
 * with loading and error states; paired row by row only when the block counts
 * match, otherwise a note and an unpaired column — never a silent misalignment.
 * And whatever it did to the Original's blocks, it takes back on unmount.
 */
const getChapterExact = vi.hoisted(() => vi.fn());
vi.mock('$lib/library-public', () => ({ getChapterExact, MODERN_EDITION: 'en-modern' }));

const { default: ParallelModern } = await import('./ParallelModern.svelte');

beforeAll(() => {
	vi.stubGlobal(
		'ResizeObserver',
		class {
			observe() {}
			disconnect() {}
		}
	);
});
afterAll(() => vi.unstubAllGlobals());

const ORIGINAL = '<p>Thou art.</p><p>Ye shall.</p>';
let host: HTMLElement;
let cmp: ReturnType<typeof mount> | null = null;
afterEach(() => {
	if (cmp) unmount(cmp);
	cmp = null;
	document.body.innerHTML = '';
	getChapterExact.mockReset();
});

function render(modernHtml: string | Error) {
	if (modernHtml instanceof Error) getChapterExact.mockRejectedValue(modernHtml);
	else getChapterExact.mockResolvedValue({ body_html: modernHtml });
	document.body.innerHTML = `<div class="reading">${ORIGINAL}</div><div id="host"></div>`;
	const original = document.querySelector('.reading') as HTMLElement;
	host = document.getElementById('host')!;
	cmp = mount(ParallelModern, {
		target: host,
		props: { slug: 'humility-2', order: 3, originalHtml: ORIGINAL, original }
	});
	return original;
}
const settle = async () => {
	await Promise.resolve();
	await tick();
	flushSync();
};

describe('ParallelModern', () => {
	it('asks the API client for the same chapter in the Modern English edition', async () => {
		render('<p>You are.</p><p>You will.</p>');
		flushSync();
		expect(host.querySelector('[role="status"]')).not.toBeNull();
		expect(getChapterExact).toHaveBeenCalledWith('humility-2', 3, 'en-modern');
		await settle();
		expect(host.querySelector('.reading')?.textContent).toContain('You are.');
	});

	it('pairs equal block counts with no note', async () => {
		render('<p>You are.</p><p>You will.</p>');
		await settle();
		expect(host.querySelector('.par-note')).toBeNull();
		expect(host.querySelector('.par-modern.free')).toBeNull();
	});

	it('falls back to an unpaired column, with a note, when the counts differ', async () => {
		render('<p>You are.</p><p>You will.</p><p>And more.</p>');
		await settle();
		expect(host.querySelector('.par-note')).not.toBeNull();
		expect(host.querySelector('.par-modern.free')).not.toBeNull();
	});

	it('says so, with a retry, when the Modern English cannot be loaded', async () => {
		render(new Error('offline'));
		await settle();
		expect(host.querySelector('[role="alert"]')).not.toBeNull();
		getChapterExact.mockResolvedValue({ body_html: '<p>You are.</p><p>You will.</p>' });
		(host.querySelector('[role="alert"] button') as HTMLButtonElement).click();
		await settle();
		expect(getChapterExact).toHaveBeenCalledTimes(2);
		expect(host.querySelector('[role="alert"]')).toBeNull();
	});

	it('leaves the Original’s blocks as it found them on unmount', async () => {
		const original = render('<p>You are.</p><p>You will.</p>');
		await settle();
		const first = original.children[0] as HTMLElement;
		first.style.minHeight = '40px';
		first.classList.add('par-pair');
		unmount(cmp!);
		cmp = null;
		expect(first.style.minHeight).toBe('');
		expect(first.classList.contains('par-pair')).toBe(false);
		expect(original.innerHTML).toBe(ORIGINAL);
	});

	it('drops the levelling from BOTH columns when the rendered blocks stop matching', async () => {
		const original = render('<p>You are.</p><p>You will.</p>');
		await settle();
		const modern = host.querySelector('.reading') as HTMLElement;
		const kept = modern.children[0] as HTMLElement;
		kept.style.minHeight = '40px';
		// Something injected a block into the Original: the next pass unpairs.
		original.append(document.createElement('p'));
		await new Promise((r) => requestAnimationFrame(() => r(null)));
		await settle();
		expect(host.querySelector('.par-modern.free')).not.toBeNull();
		expect(kept.style.minHeight).toBe('');
	});
});
