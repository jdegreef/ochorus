/**
 * `url.searchParams` must never be read where prerendering can see it.
 *
 * Public routes are prerendered, and SvelteKit throws outright on
 * `url.searchParams` during a prerender — "Cannot access url.searchParams on a
 * page with prerendering enabled". The rule behind the error is the real point:
 * one baked HTML file is served for `/login`, `/login?mode=signup` and
 * `/login?mode=reset` alike, so its markup cannot depend on the query string.
 *
 * The safe shape is an `$effect`, which does not run during prerender: the
 * baked page is the bare one, and the query string is applied on the client.
 *
 * A `$derived` is only a problem if something READS it while prerendering —
 * runes are lazy, so the chapter reader's `?q=` and `?plan=` deriveds are fine:
 * nothing in the prerendered markup touches them. `<svelte:head>` is the case
 * that always renders, which is exactly where this went wrong: the login page's
 * `<title>` read a mode that came from `searchParams`.
 *
 * So the check is narrow on purpose — a guard that failed on the three working
 * deriveds in the reader would block every PR until someone rewrote correct
 * code, and would be deleted rather than obeyed.
 *
 * This is worth a guard rather than trust. The Books shelf and the Biographies
 * page both carry a comment stating the rule, written after it bit once; the
 * login page then read `searchParams` in a `$derived` anyway, and nothing found
 * it until a ten-minute CI build failed on the prerender step. `npm run dev`
 * cannot catch it, because dev does not prerender.
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

/**
 * The source spans of every `$derived(...)` / `$derived.by(...)` in a file,
 * found by balancing parentheses from the opening one.
 */
function derivedSpans(source: string): { span: string; index: number }[] {
	const spans: { span: string; index: number }[] = [];
	// `<Mode>` matters: this codebase annotates almost every derived, and a
	// finder that missed `$derived<T>(` would silently match nothing here.
	const re = /\$derived(?:\.by)?(?:<[^>()]*>)?\s*\(/g;
	let match: RegExpExecArray | null;
	while ((match = re.exec(source)) !== null) {
		let depth = 0;
		for (let i = match.index + match[0].length - 1; i < source.length; i++) {
			if (source[i] === '(') depth++;
			else if (source[i] === ')') {
				depth--;
				if (depth === 0) {
					spans.push({ span: source.slice(match.index, i + 1), index: match.index });
					break;
				}
			}
		}
	}
	return spans;
}

describe('prerender safety', () => {
	it('nothing in <svelte:head> depends on url.searchParams', () => {
		const offenders: string[] = [];
		for (const file of svelteFiles(SRC)) {
			const rel = file.replace(SRC, 'src');
			// Admin is client-only (prerender = false; ssr = false).
			if (rel.includes('/admin/')) continue;
			const source = readFileSync(file, 'utf-8');
			const head = /<svelte:head>([\s\S]*?)<\/svelte:head>/.exec(source)?.[1];
			if (!head) continue;

			// Names bound to a $derived that reads the query string.
			const tainted = new Set<string>();
			for (const { span, index } of derivedSpans(source)) {
				if (!span.includes('searchParams')) continue;
				const lineStart = source.lastIndexOf('\n', index) + 1;
				const decl = /(?:const|let)\s+([A-Za-z_$][\w$]*)/.exec(source.slice(lineStart, index));
				if (decl) tainted.add(decl[1]);
			}
			if (head.includes('searchParams')) tainted.add('searchParams');

			for (const name of tainted) {
				if (new RegExp(`\\b${name}\\b`).test(head)) {
					offenders.push(
						`${rel}: <svelte:head> reads \`${name}\`, which comes from url.searchParams. ` +
							`The head always renders, so this throws during prerender — read it in an $effect.`
					);
				}
			}
		}
		expect(offenders, offenders.join('\n')).toEqual([]);
	});

	it('finds the spans it claims to (the guard is not vacuous)', () => {
		// A guard that silently matched nothing would pass forever.
		const spans = derivedSpans(
			'const a = $derived(1 + (2 * 3));\n' +
				'const b = $derived.by(() => url.searchParams.get(\'q\'));\n' +
				"const c = $derived<Mode>(url.searchParams.get('mode'));"
		).map((s) => s.span);
		expect(spans).toHaveLength(3);
		expect(spans[0]).toBe('$derived(1 + (2 * 3))');
		expect(spans[1]).toContain('searchParams');
		// The annotated form is the one this codebase actually writes.
		expect(spans[2]).toContain('searchParams');
	});
});
