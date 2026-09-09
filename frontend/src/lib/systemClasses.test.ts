/**
 * System classes are owned by app.css — a component must not redefine one in a
 * scoped <style> block.
 *
 * The shared component classes (`.btn`, `.field`, `.seg`, `.chip`, `.eyebrow`,
 * `.section-label`, `.count`, `.page-col`) are UNLAYERED in app.css, and a
 * component's scoped rule wins over them by specificity (Svelte scopes it with
 * a hash). So a scoped `.seg {…}` silently forks the design: Settings' segmented
 * toggle drifted into a weak-edged pill that no longer matched Sermons/Books,
 * and `.count` was hand-redefined in two files instead of using the app.css one.
 *
 * Style these in app.css, or add a MODIFIER beside the base class
 * (`.eyebrow-micro`, `.btn-sm`) — never a same-named scoped override. This is a
 * source-text authoring check, like typeScaleGuard/rtl beside it.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const SRC = join(process.cwd(), 'src');

function svelteFiles(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (statSync(path).isDirectory()) {
			if (name === 'paraglide' || name === 'node_modules') continue;
			svelteFiles(path, out);
		} else if (name.endsWith('.svelte')) {
			out.push(path);
		}
	}
	return out;
}

/** The shared classes app.css owns. `(?![\w-])` so `.count` doesn't match
 *  `.counter` and `.eyebrow` doesn't match `.eyebrow-micro`. */
const SYSTEM = ['btn', 'field', 'seg', 'chip', 'tag', 'eyebrow', 'section-label', 'count', 'page-col'];
const RULE = new RegExp(`^\\s*\\.(?:${SYSTEM.join('|')})(?![\\w-])`);

describe('system classes are not redefined in scoped CSS', () => {
	it('no <style> block redefines an app.css component class', () => {
		const offenders: string[] = [];
		for (const file of svelteFiles(SRC)) {
			const rel = file.replace(SRC, 'src');
			// Admin is English-only with its own surface. (Settings' `.seg` override
			// was retired in E1 — it now uses the shared control and stacks its rows
			// on mobile — so Settings is no longer exempt.)
			if (rel.includes('/admin/')) continue;
			const style = /<style>([\s\S]*?)<\/style>/.exec(readFileSync(file, 'utf8'))?.[1];
			if (!style) continue;
			for (const line of style.split('\n')) {
				if (RULE.test(line)) offenders.push(`${rel}: ${line.trim()}`);
			}
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});

	// A disabled .btn must read as disabled. There was no rule at all, so a
	// dimmed-nothing button sat at full opacity with a live cursor (audit I1). If
	// this rule is ever dropped the affordance silently vanishes site-wide.
	it('app.css gives .btn a :disabled affordance', () => {
		const css = readFileSync(join(SRC, 'app.css'), 'utf8');
		expect(css, '.btn:disabled must be defined in app.css').toMatch(/\.btn:disabled\s*\{/);
	});
});
