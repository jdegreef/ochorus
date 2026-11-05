/**
 * System classes are owned by app.css — a component must not redefine one in a
 * scoped <style> block.
 *
 * The shared component classes (`.btn`, `.field`, `.seg`, `.chip`, `.eyebrow`,
 * `.section-label`, `.count`, `.page-col`, `.subnav-link`) are UNLAYERED in app.css, and a
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
const SYSTEM = [
	'btn',
	'field',
	'seg',
	'chip',
	'tag',
	'eyebrow',
	'section-label',
	'count',
	'page-col',
	'subnav-link',
	'sep'
];
const RULE = new RegExp(`^\\s*\\.(?:${SYSTEM.join('|')})(?![\\w-])`);
/** Classes guarded ANYWHERE in a selector, not just at its start: a
 *  descendant override (`.author-subnav .subnav-link {…}`) forks them just as
 *  well. Their variants are app.css modifiers (`.subnav-link-tight`). */
const STRICT = /\.subnav-link(?![\w-])/;

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
				const selector = /[{,]\s*$/.test(line);
				if (RULE.test(line) || (selector && STRICT.test(line)))
					offenders.push(`${rel}: ${line.trim()}`);
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

	// One disabled look (audit I5): 0.4, 0.5 and 0.6 had all shipped, so a
	// disabled control looked more or less dead depending on who drew it.
	it('every disabled control fades to the same 0.5', () => {
		const offenders: string[] = [];
		const files = [...svelteFiles(SRC), join(SRC, 'app.css')];
		for (const file of files) {
			const rel = file.replace(SRC, 'src');
			if (rel.startsWith('src/routes/admin')) continue;
			const text = readFileSync(file, 'utf8');
			for (const m of text.matchAll(/:disabled[^{]*\{([^}]*)\}/g)) {
				const o = /opacity:\s*([\d.]+)/.exec(m[1]);
				if (o && Number(o[1]) !== 0.5) offenders.push(`${rel}: opacity ${o[1]}`);
			}
			for (const m of text.matchAll(/disabled:opacity-(\d+)/g)) {
				if (m[1] !== '50') offenders.push(`${rel}: disabled:opacity-${m[1]}`);
			}
		}
		expect(offenders, 'use opacity 0.5 (disabled:opacity-50) for a disabled control').toEqual([]);
	});

	// Full-round is one token (audit K5): `999px` and `9999px` were both typed by
	// hand. Markup uses `rounded-full`; scoped CSS uses var(--radius-pill).
	it('no hand-typed pill radius', () => {
		const offenders: string[] = [];
		for (const file of [...svelteFiles(SRC), join(SRC, 'app.css')]) {
			const text = readFileSync(file, 'utf8');
			if (/border-radius:[^;]*\b9{3,}px/.test(text)) offenders.push(file.replace(SRC, 'src'));
		}
		expect(offenders, 'write border-radius: var(--radius-pill)').toEqual([]);
	});

	// One middot (audit K3): a hand-weighted `<span class="opacity-50">·</span>`
	// is how it drifted to four weights. The separator wears `.sep`.
	it('every middot separator wears .sep', () => {
		const offenders: string[] = [];
		const SPAN = /<span([^>]*)>(\{' · '\}|\{" · "\}|·| · )<\/span>/g;
		for (const file of svelteFiles(SRC)) {
			const rel = file.replace(SRC, 'src');
			if (rel.startsWith('src/routes/admin')) continue;
			for (const m of readFileSync(file, 'utf8').matchAll(SPAN)) {
				if (!/class="[^"]*\bsep\b/.test(m[1])) offenders.push(`${rel}: ${m[0]}`);
			}
		}
		expect(offenders, 'write <span class="sep">·</span>').toEqual([]);
	});
});
