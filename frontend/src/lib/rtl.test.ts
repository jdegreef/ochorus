/**
 * Right-to-left guards.
 *
 * Arabic is a routed locale, so every reader-facing surface renders under
 * `dir="rtl"`. Two things have to hold, and neither is visible in a code review
 * of an unrelated change — which is why they're pinned here.
 *
 * 1. The direction is baked into the PRERENDERED html. The root layout keeps
 *    `document.documentElement.dir` in sync on client navigation, but this is a
 *    static site: without the placeholder in app.html an Arabic page ships with
 *    no direction and paints left-to-right until hydration. A crawler sees only
 *    that.
 *
 * 2. Reader-facing markup uses LOGICAL spacing utilities (ms/me/ps/pe,
 *    text-start/end, border-s/e, start-/end-) rather than physical ones. In LTR
 *    they are identical, so a physical class is invisible until someone opens
 *    the site in Arabic and finds a badge on the wrong side of a heading. The
 *    admin is exempt: it is deliberately English-only and always renders LTR.
 *
 * This is a source-text check, like readerDirection.test.ts beside it — the
 * mistake it catches is one of authoring, and it costs nothing to run.
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

/** Admin is English-only and always LTR — see the note in admin/+page.svelte. */
const ADMIN_ONLY = [
	join('routes', 'admin'),
	join('components', 'AddLanguageForm.svelte'),
	join('components', 'LanguageSettingsCard.svelte')
];

const isAdmin = (path: string) => ADMIN_ONLY.some((frag) => path.includes(frag));

/**
 * Physical inline-axis utilities and their logical replacements. Only the
 * inline axis: `mt-`/`mb-`/`top-`/`bottom-` are direction-independent, and
 * pixel-positioned popovers (measured from a selection rect) are physical by
 * nature and correctly so.
 */
const PHYSICAL: [RegExp, string][] = [
	[/\bml-[\w.[\]/-]+/g, 'ms-*'],
	[/\bmr-[\w.[\]/-]+/g, 'me-*'],
	[/\bpl-[\w.[\]/-]+/g, 'ps-*'],
	[/\bpr-[\w.[\]/-]+/g, 'pe-*'],
	[/\btext-left\b/g, 'text-start'],
	[/\btext-right\b/g, 'text-end'],
	[/\bborder-l(-[\w.[\]/-]+)?\b/g, 'border-s*'],
	[/\bborder-r(-[\w.[\]/-]+)?\b/g, 'border-e*']
];

describe('right-to-left support', () => {
	it('app.html carries the direction placeholder', () => {
		const html = readFileSync(join(SRC, 'app.html'), 'utf-8');
		expect(html).toMatch(/<html[^>]*\sdir="%paraglide\.dir%"/);
	});

	it('the server hook substitutes the direction from the locale', () => {
		const hook = readFileSync(join(SRC, 'hooks.server.ts'), 'utf-8');
		expect(hook).toContain('%paraglide.dir%');
		expect(hook).toContain('getTextDirection(locale)');
	});

	it('reader-facing markup uses logical, not physical, inline spacing', () => {
		const offenders: string[] = [];
		for (const file of svelteFiles(SRC)) {
			if (isAdmin(file)) continue;
			const src = readFileSync(file, 'utf-8');
			for (const [pattern, replacement] of PHYSICAL) {
				for (const hit of src.match(pattern) ?? []) {
					offenders.push(`${file.replace(SRC, 'src')}: ${hit} → use ${replacement}`);
				}
			}
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});
});
