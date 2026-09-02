/**
 * Type-scale guard.
 *
 * STYLE_GUIDE §2 fixes the type scale at six steps and says, in as many words,
 * "never invent a size with `text-[1.02rem]`-style arbitrary values — pick the
 * nearest step". Convention alone did not hold: the app had drifted to 52
 * arbitrary `text-[…rem]` utilities and 36 hardcoded `font-size:` declarations
 * in scoped blocks, i.e. roughly twenty unofficial steps between 0.6rem and
 * 1.5rem, so nothing lined up optically from one page to the next.
 *
 * The sizes are back on the scale; this keeps them there. It is a source-text
 * check like rtl.test.ts beside it — the mistake it catches is one of
 * authoring, and it costs nothing to run.
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

/** The sanctioned steps, smallest first. Mirrors the --fs-* tokens in app.css. */
const SCALE = ['micro', 'eyebrow', 'small', 'body', 'h3', 'h2', 'h1', 'display'];

describe('type scale', () => {
	it('app.css defines every step the utilities are built from', () => {
		const css = readFileSync(join(SRC, 'app.css'), 'utf-8');
		for (const step of SCALE) {
			expect(css, `--fs-${step} is missing from app.css`).toContain(`--fs-${step}:`);
		}
	});

	it('no arbitrary text-[…] sizes in markup', () => {
		const offenders: string[] = [];
		for (const file of svelteFiles(SRC)) {
			const src = readFileSync(file, 'utf-8');
			for (const hit of src.match(/text-\[[0-9.]+(rem|px|em)\]/g) ?? []) {
				offenders.push(`${file.replace(SRC, 'src')}: ${hit} → use a --fs-* step`);
			}
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});

	it('scoped <style> blocks size text from the scale', () => {
		const offenders: string[] = [];
		for (const file of svelteFiles(SRC)) {
			const style = /<style>([\s\S]*?)<\/style>/.exec(readFileSync(file, 'utf-8'))?.[1];
			if (!style) continue;
			// `em` is proportional to its parent — a verse marker set inside prose
			// is sized relative to that prose on purpose, not bypassing the scale.
			for (const hit of style.match(/font-size:\s*[0-9.]+(rem|px)\s*;/g) ?? []) {
				offenders.push(`${file.replace(SRC, 'src')}: ${hit.trim()} → use var(--fs-*)`);
			}
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});

	it('reserves .text-display for the home hero', () => {
		// STYLE_GUIDE §2: display is the one step above a page title, and a page
		// that uses it for its own <h1> makes every other page's title look like a
		// subheading. Three public pages had drifted there (a topic, a
		// biographies era, the notebook) alongside the admin surface, which is
		// English-only, has its own header language, and is exempt.
		//
		// The home hero now lives in HomeMarketing.svelte (the logged-out home was
		// split out of +page.svelte into HomeMarketing / HomeDashboard), so the
		// exemption follows it there — it is still the one and only home hero.
		const offenders: string[] = [];
		for (const file of svelteFiles(SRC)) {
			const rel = file.replace(SRC, 'src');
			if (
				rel.includes('/admin/') ||
				rel.endsWith('src/routes/+page.svelte') ||
				rel.endsWith('src/lib/components/HomeMarketing.svelte')
			)
				continue;
			const src = readFileSync(file, 'utf-8');
			// Only markup — PageHeader's doc comment names the class on purpose.
			for (const line of src.split('\n')) {
				if (/class=[^>]*\btext-display\b/.test(line)) offenders.push(`${rel}: ${line.trim()}`);
			}
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});

	it('app.css itself sizes text from the scale', () => {
		const css = readFileSync(join(SRC, 'app.css'), 'utf-8');
		const offenders = (css.match(/font-size:\s*[0-9.]+(rem|px)\s*;/g) ?? []).map(
			(hit) => `src/app.css: ${hit.trim()} → use var(--fs-*)`
		);
		expect(offenders, offenders.join('\n')).toEqual([]);
	});
});
