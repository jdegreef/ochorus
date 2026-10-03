/**
 * Stacking-order guard.
 *
 * Everything that floats over a page takes its z-index from the one scale in
 * app.css (`--z-pinned`, `--z-popover`, `--z-chrome`, …). Before the scale,
 * equivalent bars sat at different numbers — the reader bars at 10, every other
 * pinned bar at 20 — so a popover inside one lost to the other, and nothing
 * said which number a new bar should take.
 *
 * Local stacking inside one component (a badge over its own card, 1–10) may
 * stay numeric; anything above 10 must use a token. Admin is exempt.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const SRC = join(process.cwd(), 'src');

function sourceFiles(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (statSync(path).isDirectory()) {
			if (name === 'paraglide' || name === 'node_modules' || name === 'admin') continue;
			sourceFiles(path, out);
		} else if (name.endsWith('.svelte') || name.endsWith('.css')) {
			out.push(path);
		}
	}
	return out;
}

/** `z-index: 40` in CSS, or a Tailwind `z-40` / `z-[40]` class. */
const CSS_Z = /z-index:\s*(\d+)/g;
const TW_Z = /(?<![\w-])z-\[?(\d+)\]?(?![\w-])/g;

describe('stacking order', () => {
	it('anything above local stacking uses a --z-* token', () => {
		const offenders: string[] = [];
		for (const file of sourceFiles(SRC)) {
			const lines = readFileSync(file, 'utf-8').split('\n');
			lines.forEach((line, i) => {
				for (const re of [CSS_Z, TW_Z]) {
					for (const m of line.matchAll(re)) {
						if (Number(m[1]) > 10) {
							offenders.push(`${file.replace(SRC, 'src')}:${i + 1}: ${line.trim()}`);
						}
					}
				}
			});
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});

	it('the scale keeps chrome above pinned bars and sheets above chrome', () => {
		const css = readFileSync(join(SRC, 'app.css'), 'utf-8');
		const z = (name: string) => Number(css.match(new RegExp(`--z-${name}:\\s*(\\d+)`))?.[1]);
		expect(z('pinned')).toBeLessThan(z('popover'));
		expect(z('popover')).toBeLessThan(z('chrome'));
		expect(z('chrome')).toBeLessThan(z('floating'));
		expect(z('floating')).toBeLessThan(z('sheet'));
		expect(z('sheet')).toBeLessThan(z('modal'));
		expect(z('modal')).toBeLessThan(z('toast'));
		expect(z('toast')).toBeLessThan(z('skip'));
	});
});
