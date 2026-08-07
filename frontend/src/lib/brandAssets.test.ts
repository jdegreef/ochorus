import { readFileSync } from 'node:fs';
import { join } from 'node:path';
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

describe('brand assets stay in sync', () => {
	it('the frontend lockup is byte-identical to the backend canonical copy', () => {
		const backend = readFileSync(join(CANONICAL, 'ochorus-lockup.svg'), 'utf-8');
		const frontend = readFileSync(join(MIRROR, 'ochorus-lockup.svg'), 'utf-8');

		expect(
			frontend,
			'frontend/src/lib/brand/ochorus-lockup.svg has drifted from ' +
				'backend/library/data/brand/ochorus-lockup.svg (the canonical copy). ' +
				'Copy the backend file over the frontend one.'
		).toBe(backend);
	});

	it('the lockup is themeable — it must not hard-code a fill colour', () => {
		const svg = readFileSync(join(MIRROR, 'ochorus-lockup.svg'), 'utf-8');

		// The header renders it on paper AND on the dark theme from one file, so
		// the artwork has to inherit the surrounding text colour.
		expect(svg).toContain('currentColor');
		expect(svg, 'a literal black fill would be invisible on the dark theme').not.toMatch(
			/fill="#(000|000000)"/
		);
	});
});
