import { beforeEach, describe, expect, it } from 'vitest';
import { readerPrefs, LEADING, MEASURE, FONT_STACK } from './readerPrefs.svelte';

const KEY = 'ochorus:reader-prefs';
const stored = () => JSON.parse(localStorage.getItem(KEY) || '{}');

beforeEach(() => localStorage.clear());

describe('readerPrefs store', () => {
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

	it('builds a CSS custom-property string the reader can consume', () => {
		readerPrefs.setLeading('relaxed');
		readerPrefs.setMeasure('wide');
		readerPrefs.setFont('serif');
		const style = readerPrefs.style;
		expect(style).toContain(`--reading-leading:${LEADING.relaxed}`);
		expect(style).toContain(`--reading-measure:${MEASURE.wide}`);
		expect(style).toContain(`--reading-font:${FONT_STACK.serif}`);
	});
});
