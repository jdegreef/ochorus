import { readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * The logo exists twice on purpose, and must never diverge.
 *
 * The api's Docker image has rootDir `backend/`, so `library/covers.py` cannot
 * read anything under `frontend/` — the backend needs its own copy. The
 * frontend needs one it can `?raw`-import through Vite. Two copies is the
 * price; two DIFFERENT copies is the bug this guards.
 *
 * It is not hypothetical. Before this, the mark was hand-drawn twice — once in
 * BrandMark.svelte and once inlined in covers.py — and both were wrong in the
 * same way (quill pointing up-left instead of up-right), because nothing tied
 * them to the real artwork or to each other.
 *
 * If this fails, copy the BACKEND file over the frontend one; the backend
 * directory is the canonical source.
 */
const CANONICAL = join(process.cwd(), '..', 'backend', 'library', 'data', 'brand');
const MIRROR = join(process.cwd(), 'src', 'lib', 'brand');

/** Every .svelte/.ts source file, so a stray copy anywhere is caught. */
const sourceFiles = (dir = join(process.cwd(), 'src'), out: string[] = []): string[] => {
	for (const e of readdirSync(dir, { withFileTypes: true })) {
		const full = join(dir, e.name);
		if (e.isDirectory()) {
			if (e.name !== 'paraglide') sourceFiles(full, out);
		} else if (/\.(svelte|ts)$/.test(e.name)) out.push(full);
	}
	return out;
};

/** Every file the frontend mirrors from the backend's canonical brand dir. */
const MIRRORED = ['ochorus-lockup.svg', 'ochorus-mark.svg'];

describe('brand assets stay in sync', () => {
	it.each(MIRRORED)('%s is byte-identical to the backend canonical copy', (file) => {
		const backend = readFileSync(join(CANONICAL, file), 'utf-8');
		const frontend = readFileSync(join(MIRROR, file), 'utf-8');

		expect(
			frontend,
			`frontend/src/lib/brand/${file} has drifted from ` +
				`backend/library/data/brand/${file} (the canonical copy). ` +
				'Copy the backend file over the frontend one.'
		).toBe(backend);
	});

	it.each(MIRRORED)('%s is themeable — it must not hard-code a fill colour', (file) => {
		const svg = readFileSync(join(MIRROR, file), 'utf-8');

		// The header renders it on paper AND on the dark theme from one file, so
		// the artwork has to inherit the surrounding text colour.
		expect(svg).toContain('currentColor');
		expect(svg, 'a literal black fill would be invisible on the dark theme').not.toMatch(
			/fill="#(000|000000)"/
		);
	});

	it('the retired hand-drawn mark is gone from every source file', () => {
		// The old approximation's first path, which appeared verbatim in
		// BrandMark.svelte, covers.py AND quoteCard.ts. Three copies, all wrong
		// the same way. If this string comes back, so has the bug.
		const RETIRED = 'M12.4 13.6C11 8.9';
		const offenders = sourceFiles()
			.filter((f) => !f.endsWith('brandAssets.test.ts')) // this file names the needle
			.filter((f) => readFileSync(f, 'utf-8').includes(RETIRED))
			.map((f) => relative(join(process.cwd(), 'src'), f));

		expect(offenders, 'the retired hand-drawn logo is back in these files').toEqual([]);
	});
});
