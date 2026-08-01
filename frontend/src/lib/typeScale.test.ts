import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * The type scale has to be reachable as Tailwind utilities.
 *
 * It wasn't, for a long time and invisibly. `--fs-small`, `--fs-body`,
 * `--fs-h1..h3` were declared in `:root` and never mapped into `@theme`, so
 * Tailwind generated no `text-small` / `text-body` / `text-h*` rules at all —
 * roughly 690 uses across the app that quietly did nothing. It stayed hidden
 * because the *colour* tokens WERE mapped, so `text-small text-muted` still
 * turned grey and looked alive; only the size was missing. Elements fell back
 * to the base rules, which is how a section label written as a 14px sans
 * eyebrow (`<h2 class="text-small uppercase">`) came to render as a 25px
 * Fraunces heading.
 *
 * Asserted against the stylesheet rather than a rendered page because that is
 * where the mistake is made: adding a step to the scale and forgetting to
 * expose it is a one-line omission with no error anywhere.
 */

// Resolved from the project root: the jsdom environment doesn't give this file
// a `file:` import.meta.url, and vitest runs with cwd at frontend/.
const css = readFileSync(resolve(process.cwd(), 'src/app.css'), 'utf8');

/** The `@theme` block — the only place Tailwind reads utility tokens from. */
const theme = css.slice(css.indexOf('@theme'), css.indexOf('@layer base'));

const scaleSteps = [...css.matchAll(/--fs-([a-z0-9]+)\s*:/g)].map((m) => m[1]);

describe('the type scale is wired into Tailwind', () => {
	it('finds the scale in the stylesheet at all', () => {
		// Guards the test itself: a rename of --fs-* would otherwise make every
		// assertion below vacuously pass.
		expect(scaleSteps.length).toBeGreaterThan(3);
		expect(scaleSteps).toContain('small');
	});

	it('exposes every step as a text-* utility', () => {
		for (const step of scaleSteps) {
			// `display` is a hand-written component class (.text-display), not a
			// theme token — it works, and mapping it too would emit a duplicate.
			if (step === 'display') continue;
			expect(theme, `--fs-${step} has no --text-${step} in @theme`).toContain(
				`--text-${step}:`
			);
		}
	});

	it('pairs each with a line height', () => {
		// Tailwind's font-size utility emits `line-height: var(--tw-leading,
		// var(--text-<name>--line-height))`. With no such token that resolves to
		// nothing and the declaration is dropped, so the size would apply and the
		// leading would silently come from whatever it inherited.
		for (const step of scaleSteps) {
			if (step === 'display') continue;
			expect(theme, `--text-${step} has no --text-${step}--line-height`).toContain(
				`--text-${step}--line-height:`
			);
		}
	});
});
