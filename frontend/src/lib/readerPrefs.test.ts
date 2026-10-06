import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
	LEADING,
	MEASURE,
	MARGIN,
	FONT_STACK,
	defaultMeasureFor,
	load
} from './readerPrefs.svelte';

const KEY = 'ochorus:reader-prefs';
const stored = () => JSON.parse(localStorage.getItem(KEY) || '{}');

// The store is a module singleton: each test gets a fresh instance, as a fresh
// page load would, so no preference set by one test leaks into the next.
let readerPrefs: typeof import('./readerPrefs.svelte').readerPrefs;
const innerWidth = window.innerWidth;
beforeEach(async () => {
	localStorage.clear();
	vi.resetModules();
	({ readerPrefs } = await import('./readerPrefs.svelte'));
});
// The device-default tests narrow the window; reset() reads it too.
afterEach(() => {
	Object.defineProperty(window, 'innerWidth', { value: innerWidth, configurable: true, writable: true });
});

describe('readerPrefs store', () => {
	it('keeps a stored face this build offers and drops one it does not', () => {
		localStorage.setItem(KEY, JSON.stringify({ font: 'lora' }));
		expect(load().font).toBe('lora');
		// A face removed in a later build, or a hand-edited value, lands on the
		// default rather than on an --reading-font nothing defines.
		localStorage.setItem(KEY, JSON.stringify({ font: 'comic-neue' }));
		expect(load().font).toBe('serif');
		// `in` would walk the prototype and accept this.
		localStorage.setItem(KEY, JSON.stringify({ font: 'constructor' }));
		expect(load().font).toBe('serif');
	});

	it('clamps font scale to the supported range', () => {
		readerPrefs.setScale(5);
		expect(readerPrefs.scale).toBe(1.6);
		readerPrefs.setScale(0.1);
		expect(readerPrefs.scale).toBe(0.8);
	});

	it('snaps the scale to 0.05 steps', () => {
		readerPrefs.setScale(1.13);
		expect(readerPrefs.scale).toBe(1.15);
	});

	it('bumpScale is relative to the current scale', () => {
		readerPrefs.setScale(1);
		readerPrefs.bumpScale(0.1);
		expect(readerPrefs.scale).toBeCloseTo(1.1, 5);
	});

	it('persists preferences to localStorage', () => {
		readerPrefs.setPaged(true);
		readerPrefs.setFont('dyslexic');
		expect(stored().paged).toBe(true);
		expect(stored().font).toBe('dyslexic');
	});

	it('reset() restores every preference to its default', () => {
		readerPrefs.setScale(1.4);
		readerPrefs.setFont('dyslexic');
		readerPrefs.setMeasure('wide');
		readerPrefs.setTapToScroll(true);
		readerPrefs.setPreferModern(true);
		readerPrefs.reset();
		expect(readerPrefs.scale).toBe(1);
		expect(readerPrefs.font).toBe('serif');
		expect(readerPrefs.measure).toBe('normal');
		expect(readerPrefs.tapToScroll).toBe(false);
		expect(readerPrefs.preferModern).toBe(false);
		expect(stored().scale).toBe(1);
		expect(stored().font).toBe('serif');
	});

	it('persists the tap-to-page-down default (off by default)', () => {
		expect(readerPrefs.tapToScroll).toBe(false);
		readerPrefs.setTapToScroll(true);
		expect(stored().tapToScroll).toBe(true);
	});

	it('persists the prefer-Modern-English default (off by default)', () => {
		expect(readerPrefs.preferModern).toBe(false);
		readerPrefs.setPreferModern(true);
		expect(readerPrefs.preferModern).toBe(true);
		expect(stored().preferModern).toBe(true);
		readerPrefs.setPreferModern(false);
		expect(stored().preferModern).toBe(false);
	});

	it('persists text alignment and enables hyphenation when justified', () => {
		readerPrefs.setAlign('justify');
		expect(stored().align).toBe('justify');
		expect(readerPrefs.style).toContain('--reading-align:justify');
		expect(readerPrefs.style).toContain('--reading-hyphens:auto');
		readerPrefs.setAlign('left');
		expect(readerPrefs.style).toContain('--reading-align:start');
	});

	it('builds a CSS custom-property string the reader can consume', () => {
		readerPrefs.setLeading('relaxed');
		readerPrefs.setMeasure('wide');
		readerPrefs.setFont('serif');
		const style = readerPrefs.style;
		expect(style).toContain(`--reading-leading:${LEADING.relaxed}`);
		expect(style).toContain(`--reading-measure:${MEASURE.wide}`);
		expect(style).toContain(`--reading-font:${FONT_STACK.serif}`);
	});

	it('offers an extra-wide measure and emits it', () => {
		readerPrefs.setMeasure('xwide');
		expect(stored().measure).toBe('xwide');
		expect(readerPrefs.style).toContain(`--reading-measure:${MEASURE.xwide}`);
	});

	it('persists the margin pref, emits it, and resets it', () => {
		expect(readerPrefs.margin).toBe('normal');
		readerPrefs.setMargin('generous');
		expect(stored().margin).toBe('generous');
		expect(readerPrefs.style).toContain(`--reading-margin:${MARGIN.generous}`);
		readerPrefs.reset();
		expect(readerPrefs.margin).toBe('normal');
	});
});

describe('load(): a stored measure beats the device default', () => {
	const setWidth = (w: number) =>
		Object.defineProperty(window, 'innerWidth', { value: w, configurable: true, writable: true });

	it('picks the tablet default only when nothing is stored', () => {
		setWidth(800);
		localStorage.removeItem('ochorus:reader-prefs');
		expect(load().measure).toBe('wide');
	});

	it("honours a stored choice on a tablet (a saved 'narrow' is never overridden)", () => {
		setWidth(800);
		localStorage.setItem('ochorus:reader-prefs', JSON.stringify({ measure: 'narrow' }));
		expect(load().measure).toBe('narrow');
	});

	it('drops a junk margin (prototype key) to the default rather than injecting it', () => {
		localStorage.setItem('ochorus:reader-prefs', JSON.stringify({ margin: 'constructor' }));
		expect(load().margin).toBe('normal');
	});
});

describe('defaultMeasureFor (first-run column width by device class)', () => {
	it('gives tablets a wide column, phones and desktops the normal one', () => {
		expect(defaultMeasureFor(375)).toBe('normal'); // phone
		expect(defaultMeasureFor(768)).toBe('wide'); // tablet portrait (lower bound)
		expect(defaultMeasureFor(1023)).toBe('wide'); // just under the two-column threshold
		expect(defaultMeasureFor(1024)).toBe('normal'); // desktop: gets the paged spread instead
		expect(defaultMeasureFor(1440)).toBe('normal');
	});
});

describe('the young-reader layout', () => {
	it('lays a children’s edition out big, clear and scrolling until the reader chooses', () => {
		readerPrefs.init();
		readerPrefs.youngEdition = true;
		expect(readerPrefs.youngActive).toBe(true);
		expect([readerPrefs.scale, readerPrefs.leading, readerPrefs.measure]).toEqual([1.3, 'relaxed', 'narrow']);
		expect([readerPrefs.font, readerPrefs.paged]).toEqual(['hyperlegible', false]);
		// Never written down: leaving the edition restores the reader's own layout.
		readerPrefs.youngEdition = false;
		expect([readerPrefs.scale, readerPrefs.font]).toEqual([1, 'serif']);
		expect(stored().font).toBeUndefined();
	});

	it('steps aside for each setting the reader picks, and only that one', () => {
		readerPrefs.init();
		readerPrefs.youngEdition = true;
		readerPrefs.setFont('garamond');
		readerPrefs.bumpScale(0.1); // from the layout's 1.3, not the stored 1
		expect([readerPrefs.font, readerPrefs.scale, readerPrefs.leading]).toEqual(['garamond', 1.4, 'relaxed']);
		expect(stored().chosen).toEqual(['font', 'scale']);
	});

	it('lets a young reader go up to 200%, capped back to 160% elsewhere', () => {
		readerPrefs.init();
		readerPrefs.youngEdition = true;
		readerPrefs.setScale(5);
		expect(readerPrefs.scale).toBe(2);
		readerPrefs.youngEdition = false;
		expect(readerPrefs.scale).toBe(1.6);
		expect(readerPrefs.canGrow).toBe(false);
	});

	it('goes off with the toggle, and the toggle is remembered', () => {
		readerPrefs.init();
		readerPrefs.youngEdition = true;
		readerPrefs.setYoungLayout(false);
		expect([readerPrefs.youngActive, readerPrefs.font]).toEqual([false, 'serif']);
		expect(stored().youngLayout).toBe(false);
	});

	it('counts an older saved preference as chosen only where it differs from a first run', () => {
		// Saved before `chosen` existed: every field present, only the font changed.
		localStorage.setItem(
			KEY,
			JSON.stringify({ scale: 1, leading: 'normal', measure: defaultMeasureFor(window.innerWidth), font: 'lora', paged: window.innerWidth >= 1024 })
		);
		expect(load().chosen).toEqual(['font']);
	});

	it('keeps the account in step with the reader’s own values, never the layer', () => {
		readerPrefs.init();
		readerPrefs.youngEdition = true;
		expect(readerPrefs.scale).toBe(1.3);
		expect(readerPrefs.own.scale).toBe(1); // what the account sync sends
	});

	it('takes the account’s default size on sign-in without counting it as chosen', () => {
		readerPrefs.init();
		readerPrefs.applySyncedScale(1);
		readerPrefs.youngEdition = true;
		expect(readerPrefs.scale).toBe(1.3);
		// …but a size the reader did set somewhere is theirs.
		readerPrefs.applySyncedScale(1.5);
		expect(readerPrefs.scale).toBe(1.5);
	});

	it('keeps a children’s 200% out of the reader’s own values everywhere else', () => {
		readerPrefs.init();
		readerPrefs.youngEdition = true;
		readerPrefs.setScale(2);
		expect(readerPrefs.own.scale).toBe(1.6);
	});
});
