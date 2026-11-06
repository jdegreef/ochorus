/**
 * The palette rules live in static/palettes.css, out of the render-blocking
 * app.css, and are linked only when a palette is applied (see that file's
 * header). These guard the split.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { PALETTE_SHEET } from './palette.svelte';

const read = (f: string) => readFileSync(join(process.cwd(), f), 'utf-8').replace(/\/\*[\s\S]*?\*\//g, '');
const APP = read('src/app.css');
const SHEET = read('static/palettes.css');
const HTML = readFileSync(join(process.cwd(), 'src/app.html'), 'utf-8');
const RENDER = readFileSync(join(process.cwd(), '../render.yaml'), 'utf-8');

/** Every `selector { body }` rule with custom properties, innermost blocks. */
function rules(css: string): { selector: string; props: Set<string> }[] {
	return [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({
		selector: m[1].trim(),
		props: new Set([...m[2].matchAll(/(--[\w-]+)\s*:/g)].map((p) => p[1]))
	}));
}
/** Attribute + class + pseudo-class count: enough for these flat selectors. */
const specificity = (sel: string) => (sel.match(/\[|\.|:(?!:)/g) ?? []).length;

describe('the palette sheet', () => {
	it('app.css carries no palette rules', () => {
		expect(APP).not.toMatch(/data-palette=/);
	});

	it('holds only palette-scoped :root rules', () => {
		for (const { selector } of rules(SHEET)) {
			expect(selector).toMatch(/^:root(\[data-theme='\w+'\])?\[data-palette='\w+'\]$/);
		}
	});

	it('does not depend on load order: no app.css rule of equal specificity sets the same property', () => {
		const app = rules(APP);
		for (const p of rules(SHEET)) {
			for (const a of app) {
				if (specificity(a.selector) !== specificity(p.selector)) continue;
				const shared = [...p.props].filter((x) => a.props.has(x));
				expect(shared, `${p.selector} vs ${a.selector}`).toEqual([]);
			}
		}
	});

	it("app.html's boot script links the sheet when it sets a palette", () => {
		expect(HTML).toContain(`document.write('<link rel="stylesheet" href="${PALETTE_SHEET}">')`);
	});

	it('has a cache rule (it is unhashed)', () => {
		expect(RENDER).toContain(`path: ${PALETTE_SHEET}`);
	});
});
