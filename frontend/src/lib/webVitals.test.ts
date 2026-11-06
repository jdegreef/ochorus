import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
	PAGE_LOAD_EVENT,
	SLOW_TAP_EVENT,
	lcpBucket,
	pageLoadProps,
	ttfbBucket,
	watchPageLoad,
	inpBucket,
	longestPhase,
	notePageView,
	reportInp,
	resetWebVitals,
	scrubSelector,
	slowTapProps,
	viewAt
} from './webVitals';

type Attribution = Parameters<typeof slowTapProps>[0]['attribution'];

function metric(value: number, over: Partial<Attribution> = {}) {
	return {
		value,
		attribution: {
			interactionTarget: 'main>a.card',
			interactionType: 'pointer',
			interactionTime: 1000,
			inputDelay: 10,
			processingDuration: 150,
			presentationDelay: 40,
			loadState: 'complete',
			processedEventEntries: [],
			longAnimationFrameEntries: [],
			longAnimationFrameSummary: undefined,
			...over
		} as Attribution
	};
}

describe('inpBucket', () => {
	it('reports only above 200 ms, in coarse buckets', () => {
		expect(inpBucket(80)).toBeNull();
		expect(inpBucket(200)).toBeNull();
		expect(inpBucket(201)).toBe('200-300');
		expect(inpBucket(300)).toBe('200-300');
		expect(inpBucket(301)).toBe('300-500');
		expect(inpBucket(500)).toBe('300-500');
		expect(inpBucket(1800)).toBe('500+');
		expect(inpBucket(NaN)).toBeNull();
	});
});

describe('longestPhase', () => {
	it('names the phase that took longest', () => {
		expect(longestPhase({ inputDelay: 300, processingDuration: 20, presentationDelay: 10 })).toBe(
			'input delay'
		);
		expect(longestPhase({ inputDelay: 3, processingDuration: 20, presentationDelay: 10 })).toBe(
			'processing'
		);
		expect(longestPhase({ inputDelay: 3, processingDuration: 20, presentationDelay: 99 })).toBe(
			'presentation delay'
		);
	});
});

describe('scrubSelector', () => {
	it('drops Svelte scope classes, masks numbers and hashes, caps length', () => {
		expect(scrubSelector('div.svelte-1x9abc2>button.tab')).toBe('div>button.tab');
		expect(scrubSelector('#note-8812>span')).toBe('#note-N>span');
		expect(scrubSelector('#h-3f2a9c1e-77aa-4b2c>p')).toBe('#h-*>p');
		expect(scrubSelector(undefined)).toBe('(removed)');
		const long = scrubSelector('div.' + 'x'.repeat(200));
		expect(long.length).toBe(80);
		expect(long.startsWith('…')).toBe(true);
	});
});

describe('slowTapProps', () => {
	it('builds short, non-personal labels', () => {
		expect(slowTapProps(metric(420), '/authors/[slug]', 'es')).toEqual({
			route: '/authors/[slug]',
			locale: 'es',
			inp: '300-500',
			type: 'pointer',
			target: 'main>a.card',
			phase: 'processing'
		});
	});

	it('is null for a fast page view', () => {
		expect(slowTapProps(metric(120), '/', 'en')).toBeNull();
	});
});

describe('reportInp', () => {
	beforeEach(() => resetWebVitals());

	it('credits the page the tap happened on, once per page view', () => {
		notePageView('/books/[slug]', 0);
		notePageView('/books/[slug]/[order]', 2000);
		expect(viewAt(1500)?.route).toBe('/books/[slug]');
		const send = vi.fn();

		reportInp(metric(350, { interactionTime: 1500 }), 'en', send);
		reportInp(metric(900, { interactionTime: 1600 }), 'en', send); // same view: dropped
		reportInp(metric(260, { interactionTime: 2500 }), 'en', send);

		expect(send).toHaveBeenCalledTimes(2);
		expect(send.mock.calls[0]).toEqual([
			SLOW_TAP_EVENT,
			expect.objectContaining({ route: '/books/[slug]', inp: '300-500' })
		]);
		expect(send.mock.calls[1][1]).toMatchObject({ route: '/books/[slug]/[order]', inp: '200-300' });
	});

	it('sends nothing for a fast interaction and keeps the view open', () => {
		notePageView('/', 0);
		const send = vi.fn();
		reportInp(metric(90), 'en', send);
		expect(send).not.toHaveBeenCalled();
		reportInp(metric(240), 'en', send);
		expect(send).toHaveBeenCalledOnce();
	});

	it('names a route-less page (the SPA fallback shell)', () => {
		notePageView(null, 0);
		const send = vi.fn();
		reportInp(metric(600), 'en', send);
		expect(send.mock.calls[0][1].route).toBe('(no route)');
	});
});

describe('page load (LCP + TTFB)', () => {
	beforeEach(() => resetWebVitals());

	it('buckets LCP and TTFB on web.dev bands', () => {
		expect([999, 1000, 2500, 2501, 4000, 4001].map(lcpBucket)).toEqual(['<1s', '1-2.5s', '1-2.5s', '2.5-4s', '2.5-4s', '4s+']);
		expect([299, 300, 800, 801, 1800, 1801].map(ttfbBucket)).toEqual(['<0.3s', '0.3-0.8s', '0.3-0.8s', '0.8-1.8s', '0.8-1.8s', '1.8s+']);
	});

	it('reports once, for the first page view, with TTFB when it arrived', () => {
		notePageView('/books/[slug]', 0);
		notePageView('/authors', 5000);
		let lcp!: (m: { value: number }) => void;
		let ttfb!: (m: { value: number }) => void;
		const send = vi.fn();
		watchPageLoad({ onLCP: (cb) => (lcp = cb as never), onTTFB: (cb) => (ttfb = cb as never) }, 'sw', send);
		ttfb({ value: 1200 });
		lcp({ value: 3100 });
		lcp({ value: 3300 });
		expect(send).toHaveBeenCalledTimes(1);
		expect(send).toHaveBeenCalledWith(PAGE_LOAD_EVENT, {
			route: '/books/[slug]',
			locale: 'sw',
			lcp: '2.5-4s',
			ttfb: '0.8-1.8s'
		});
	});

	it('says unknown when TTFB never arrived', () => {
		expect(pageLoadProps({ value: 500 }, undefined, '/', 'en')).toEqual({ route: '/', locale: 'en', lcp: '<1s', ttfb: 'unknown' });
	});
});
