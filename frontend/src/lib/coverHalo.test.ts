import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { HALO_SCOPE, haloDigest, haloRules } from './coverHalo';

/**
 * The halo is a promise the contrast gate relies on, and this holds it.
 *
 * `covers.ink_contrast` lays `cover_halo.HALO` over every line it measures:
 * the least darkness the halo leaves just outside a glyph, measured in the
 * browser by `npm run covers:halo` from the rules in `cover-type.css`. Soften a
 * shadow and the gate would go on counting darkness the page no longer draws —
 * and every painting's band strength was tuned against that count. So the
 * measurement records a digest of the rules it measured, and this fails the
 * moment the stylesheet's rules differ from it.
 */
const COVER_CSS = readFileSync(join(process.cwd(), 'src/lib/components/cover-type.css'), 'utf-8');
const HALO_PY = readFileSync(
	resolve(process.cwd(), '..', 'backend', 'library', 'cover_halo.py'),
	'utf-8'
);

describe('the halo under white type', () => {
	it('is the halo the contrast gate measured', () => {
		const recorded = /^HALO_RULES = "([0-9a-f]+)"/m.exec(HALO_PY)?.[1];
		expect(recorded, 'cover_halo.py records no HALO_RULES digest').toBeTruthy();
		expect(
			haloDigest(COVER_CSS),
			'the halo rules in cover-type.css are not the ones its floor was measured from — ' +
				'run `npm run covers:halo`, then `uv run python scripts/tune_art_scrim.py` and `npm run og:covers`'
		).toBe(recorded);
	});

	it('shadows every line of white type and the mark, and only over a scrim', () => {
		const rules = haloRules(COVER_CSS);
		for (const part of ['.byline', '.volume', '.title', '.subtitle', '.brandmark svg']) {
			expect(rules, `the halo no longer reaches ${part}`).toContain(part);
		}
		// A layout and a dark-ink ground set DARK ink: a black halo there would
		// muddy the very type it is meant to lift.
		expect(HALO_SCOPE).toContain(':not(.has-layout, .ink-dark)');
	});
});
