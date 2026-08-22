import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

/**
 * Two modules are loaded straight from Node by build scripts
 * (`scripts/generate-sermon-og.mjs`, `scripts/generate-emblem-hues.mjs`) under
 * its TypeScript type stripping. Node does no extension resolution and knows
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
	const FILES = ['src/lib/emblems.ts', 'src/lib/emblemNames.ts'];

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
