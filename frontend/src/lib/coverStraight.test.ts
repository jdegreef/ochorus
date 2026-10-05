/**
 * Upright-cover guard: a book is never drawn on a slant.
 *
 * Covers used to lean — the home Year-in-Books collage at -1.5°, the shelf
 * fans at -3°…7°, the plan-page fan at ±10°, the home hero plate at 2° — and
 * readers saw it as crooked rather than charming (founder steer, 2026-10-04:
 * "I want them all to be straight horizontally and vertically"). Each tilt was
 * added deliberately, in a different file, so without a check the next one
 * comes back the same way.
 *
 * The rule is broader than "covers", on purpose: a tilt on a WRAPPER (the
 * collage was a rotated <ul>) leans every cover inside it, and no selector
 * test can see that. So every 2D rotation that isn't a right angle fails,
 * unless the line or the line above says `tilt-ok:` and why — paper scraps in
 * the notebook, a stamp, the login illustration's sticky note. Right angles
 * (chevrons, disclosure arrows) and 3D turns (`rotateY`, the card's hover tip
 * toward the reader) are not slants and pass.
 *
 * Same shape as colorTokens.test.ts: a source-text check, costing nothing.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const SRC = join(process.cwd(), 'src');

function styleFiles(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (statSync(path).isDirectory()) {
			if (name === 'paraglide' || name === 'node_modules' || name === 'admin') continue;
			styleFiles(path, out);
		} else if (name.endsWith('.svelte') || name.endsWith('.css')) {
			out.push(path);
		}
	}
	return out;
}

/** A CSS `rotate(<n>deg)` / `rotate: <n>deg` / `rotate(calc(…))`, or a
 *  Tailwind `rotate-<n>` class, whose angle is not a whole number of quarter
 *  turns. SVG's unit-less `rotate(a x y)` attribute is a drawing, not layout,
 *  and is left alone. */
function slants(line: string): string[] {
	const found: string[] = [];
	for (const m of line.matchAll(/(?<![\w-])rotate(?:\(\s*|:\s*)(calc\(|-?[\d.]+deg)/g)) {
		if (m[1] === 'calc(' || Number.parseFloat(m[1]) % 90 !== 0) found.push(m[0]);
	}
	for (const m of line.matchAll(/(?<![\w-])-?rotate-(\d+)(?![\w-])/g)) {
		if (Number(m[1]) % 90 !== 0) found.push(m[0]);
	}
	return found;
}

describe('book covers stand upright', () => {
	it('has no slanted rotation outside a stated tilt-ok: exemption', () => {
		const offenders: string[] = [];
		for (const file of styleFiles(SRC)) {
			const lines = readFileSync(file, 'utf8').split('\n');
			lines.forEach((line, i) => {
				const hits = slants(line);
				if (!hits.length) return;
				if (/tilt-ok:/.test(line) || /tilt-ok:/.test(lines[i - 1] ?? '')) return;
				offenders.push(`${relative(SRC, file)}:${i + 1}  ${hits.join(', ')}`);
			});
		}
		expect(offenders, 'Covers stand straight — drop the rotation, or mark a non-book with `tilt-ok: <why>`').toEqual([]);
	});

	it('recognises a slant and lets a right angle or a 3D turn through', () => {
		expect(slants('transform: rotate(-1.5deg);')).toHaveLength(1);
		expect(slants('transform: rotate(calc(var(--lean) * 4deg));')).toHaveLength(1);
		expect(slants('rotate: 3deg;')).toHaveLength(1);
		expect(slants('<li class="-rotate-2 shadow">')).toHaveLength(1);
		expect(slants('transform: rotate(-90deg);')).toEqual([]);
		expect(slants('group-open:rotate-90')).toEqual([]);
		expect(slants('transform: perspective(700px) rotateY(-9deg);')).toEqual([]);
		expect(slants('transform="rotate(-10 215 178)"')).toEqual([]);
	});
});
