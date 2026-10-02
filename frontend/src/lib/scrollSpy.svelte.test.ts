import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { flushSync } from 'svelte';
import {
	realignHashOnMeasure,
	realignHashTarget,
	resetFirstPage,
	scrollSpy,
	SUBNAV_H_EST,
	subnavOffset
} from './scrollSpy.svelte';

// `scrollSpy` registers an $effect, so these run inside an effect root.
const click = (over: Partial<MouseEvent> = {}) =>
	({
		button: 0,
		metaKey: false,
		ctrlKey: false,
		shiftKey: false,
		altKey: false,
		preventDefault: vi.fn(),
		...over
	}) as unknown as MouseEvent;

function withSpy(run: (spy: ReturnType<typeof scrollSpy>) => void) {
	const cleanup = $effect.root(() => run(scrollSpy(() => [])));
	cleanup();
}

describe('spy.jump — the sticky sub-nav click handler', () => {
	afterEach(() => vi.restoreAllMocks());

	it("keeps SvelteKit's history state, lights the tab and writes the hash", () => {
		// A null state here erased the router's index and broke Back (#4900).
		history.replaceState({ 'sveltekit:history': 3 }, '', '/scripture/');
		withSpy((spy) => {
			const e = click();
			spy.jump(e, 'section-paul');
			expect(e.preventDefault).toHaveBeenCalled();
			expect(history.state).toEqual({ 'sveltekit:history': 3 });
			expect(location.hash).toBe('#section-paul');
			expect(spy.active).toBe('section-paul');
		});
	});

	it('leaves a modified or non-primary click to the browser (new tab)', () => {
		for (const over of [{ metaKey: true }, { ctrlKey: true }, { shiftKey: true }, { button: 1 }]) {
			withSpy((spy) => {
				const e = click(over);
				spy.jump(e, 'books');
				expect(e.preventDefault).not.toHaveBeenCalled();
				expect(spy.active).toBe('');
			});
		}
	});

	it('does not light a target that is not a tab', () => {
		withSpy((spy) => {
			spy.jump(click(), 'languages', { track: false });
			expect(spy.active).toBe('');
		});
	});

	it('still jumps when the browser refuses replaceState', () => {
		const target = document.createElement('section');
		target.id = 'faq';
		target.scrollIntoView = vi.fn();
		document.body.append(target);
		vi.spyOn(history, 'replaceState').mockImplementation(() => {
			throw new DOMException('too many calls', 'SecurityError');
		});
		withSpy((spy) => {
			expect(() => spy.jump(click(), 'faq')).not.toThrow();
			expect(target.scrollIntoView).toHaveBeenCalled();
		});
		target.remove();
	});
});

describe('realignHashTarget — a cold #section load that landed under the bars', () => {
	afterEach(() => {
		vi.restoreAllMocks();
		history.replaceState(null, '', location.pathname);
	});

	// Measured bars of 92px: the anchors' scroll-margin is 92 + 0.5rem = 100.
	function target(top: number) {
		const el = document.createElement('section');
		el.id = 'section-paul';
		el.scrollIntoView = vi.fn();
		el.getBoundingClientRect = () => ({ top }) as DOMRect;
		document.body.append(el);
		vi.spyOn(window, 'getComputedStyle').mockReturnValue({
			scrollMarginTop: '100px',
			fontSize: '16px'
		} as CSSStyleDeclaration);
		history.replaceState(null, '', '#section-paul');
		return el;
	}

	it('re-lands a target the bars hide', () => {
		for (const top of [0, 8, 70]) {
			const el = target(top);
			realignHashTarget();
			expect(el.scrollIntoView).toHaveBeenCalledWith({ block: 'start' });
			el.remove();
			vi.restoreAllMocks();
		}
	});

	it('leaves one already clear of the bars, or scrolled off the top', () => {
		for (const top of [92, 100, 400, -600]) {
			const el = target(top);
			realignHashTarget();
			expect(el.scrollIntoView).not.toHaveBeenCalled();
			el.remove();
			vi.restoreAllMocks();
		}
	});

	it('does nothing without a hash, or for a hash naming nothing', () => {
		history.replaceState(null, '', location.pathname);
		expect(() => realignHashTarget()).not.toThrow();
		history.replaceState(null, '', '#nowhere');
		expect(() => realignHashTarget()).not.toThrow();
	});
});

describe('subnavOffset', () => {
	it('estimates a shown bar until it is measured, and is 0 with no bar', () => {
		expect(subnavOffset(true, 0)).toBe(SUBNAV_H_EST);
		expect(subnavOffset(true, 52)).toBe(52);
		expect(subnavOffset(false, 0)).toBe(0);
	});
});

describe('realignHashOnMeasure', () => {
	// It acts only for the first page a document loads; each test starts there.
	beforeEach(resetFirstPage);
	afterEach(() => vi.restoreAllMocks());

	it('waits for a measured bar, then realigns once, a frame later', () => {
		const frames: FrameRequestCallback[] = [];
		vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => frames.push(cb));
		let barH = $state(0);
		const cleanup = $effect.root(() => realignHashOnMeasure(() => barH));
		flushSync();
		expect(frames).toHaveLength(0);
		barH = 48;
		flushSync();
		barH = 52;
		flushSync();
		expect(frames).toHaveLength(1);
		cleanup();
	});

	it('keeps the frame through a re-measure, and cancels it on teardown', () => {
		vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(7);
		const cancel = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
		let barH = $state(48);
		const cleanup = $effect.root(() => realignHashOnMeasure(() => barH));
		flushSync();
		barH = 52;
		flushSync();
		expect(cancel).not.toHaveBeenCalled();
		cleanup();
		expect(cancel).toHaveBeenCalledWith(7);
	});

	it('leaves later pages, and a reload or Back, to where they landed', () => {
		const raf = vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(1);
		const page = () => {
			const cleanup = $effect.root(() => realignHashOnMeasure(() => 48));
			flushSync();
			cleanup();
		};
		page();
		page(); // a client-side navigation to a second page
		expect(raf).toHaveBeenCalledTimes(1);

		for (const type of ['reload', 'back_forward']) {
			resetFirstPage();
			vi.spyOn(performance, 'getEntriesByType').mockReturnValue([{ type } as PerformanceNavigationTiming]);
			page();
		}
		expect(raf).toHaveBeenCalledTimes(1);
	});
});
