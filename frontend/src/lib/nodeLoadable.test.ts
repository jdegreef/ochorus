import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * Some `src/lib` modules are loaded straight from Node by the build scripts in
 * `scripts/`, under its TypeScript type stripping. Node does no extension resolution and knows
 * nothing of the `$lib` alias, so a runtime import of `'./x'` or `'$lib/x'`
 * anywhere in them stops both generators dead — while `svelte-check`, vitest
 * and `vite build` all keep passing, because every one of them resolves those
 * specifiers happily.
 *
 * That is exactly how it broke once: a convenience `export … from
 * './emblemNames'` was added to `emblems.ts`, and the failure surfaced only
 * when someone ran the script — with CI meanwhile telling authors of new
 * sermons to run it.
 *
 * TYPE-only imports are fine: they are erased before Node sees them.
 */
describe('modules the build scripts load under bare Node', () => {
	/**
	 * DERIVED, not listed. The list was hand-kept and had already fallen behind:
	 * `coverArt.ts` (loaded by `og-card.mjs` and `generate-sermon-og.mjs`) and
	 * `eras.ts` (by `generate-cover-og.mjs`) were both unguarded while the
	 * docstring above claimed the set was complete. Scanning the scripts means a
	 * new one arrives already covered — and this is the guard whose whole point
	 * is that nobody notices when it is missing, since `og:covers` is hand-run
	 * and not in CI.
	 *
	 * One level deep is enough: a module these import would have to name a `.ts`
	 * extension to load at all, which is what the check below is about.
	 */
	const FILES = [
		...new Set(
			readdirSync(join(process.cwd(), 'scripts'))
				.filter((f) => f.endsWith('.mjs'))
				.flatMap((f) => [
					...readFileSync(join(process.cwd(), 'scripts', f), 'utf8').matchAll(
						/from '\.\.?\/(?:\.\.\/)?(src\/lib\/[\w./-]+\.ts)'/g
					)
				])
				.map((m) => m[1])
		)
	].sort();

	it('finds the modules the scripts actually load', () => {
		// A regex that matched nothing would make every case below vacuous.
		expect(FILES.length, 'no script-loaded src/lib module was found').toBeGreaterThan(0);
	});

	for (const file of FILES) {
		it(`${file} has no runtime import Node cannot resolve`, () => {
			const src = readFileSync(file, 'utf8');
			const offenders = [...src.matchAll(/^(?:import|export)\s+(?!type\b)[\s\S]*?from\s+'([^']+)'/gm)]
				.map((m) => m[1])
				.filter((spec) => !spec.endsWith('.ts') && !spec.endsWith('.js'));
			expect(
				offenders,
				`add the .ts extension, or drop the import — Node resolves neither ` +
					`'$lib' nor an extensionless path, and these files are loaded by ` +
					`scripts/generate-*.mjs`
			).toEqual([]);
		});
	}
});
