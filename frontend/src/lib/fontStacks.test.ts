import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { FONT_STACK } from './readerPrefs.svelte';

/** app.css with comments stripped: the prose in this file says `--font-display:`
 *  more than once, and a scan that counts those finds a declaration whose value
 *  is a paragraph. */
const APP_CSS = readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8').replace(
	/\/\*[\s\S]*?\*\//g,
	''
);

/**
 * The app's own type, in the scripts it is read in.
 *
 * Ochorus reads in eight languages and three of them are not Latin. Fraunces
 * has no Arabic and no Devanagari, and Georgia behind it has no Devanagari
 * either — so ~609,000 words of Arabic and Hindi prose were drawn by whatever
 * the DEVICE chose. That is not a fallback, it is an absence: it looks like a
 * decision, it differs on every phone, and measured in Chromium it came out
 * SANS-SERIF on the surface the style guide asks to be set like a printed page.
 *
 * These gate the join that made it possible: a stack that names no face for a
 * script, a copy of a stack that drifts from the one beside it, and a reader
 * preference that quietly resolves to a generic.
 */
describe('font stacks', () => {
	/** Every family named in a `--font-*` declaration, in order. */
	const stackOf = (token: string, from = APP_CSS) => {
		const at = from.indexOf(`--${token}:`);
		expect(at, `--${token} is not declared`).toBeGreaterThan(-1);
		return [...from.slice(at, from.indexOf(';', at)).matchAll(/'([^']+)'/g)].map(([, f]) => f);
	};

	/** The subsets a fontsource family ships, from its file names. */
	const SUBSETS = ['latin', 'cyrillic', 'arabic', 'devanagari'];
	const subsetsOf = (family: string) => {
		const slug = family
			.replace(/ Variable$/, '')
			.toLowerCase()
			.replace(/ /g, '-');
		for (const scope of ['@fontsource-variable', '@fontsource']) {
			try {
				const files = readdirSync(join(process.cwd(), 'node_modules', scope, slug, 'files')).join(
					'\n'
				);
				// `-latin-` also matches inside `-latin-ext-`, and a family can ship
				// the extension without the base — Hanken ships `cyrillic-ext` and no
				// `cyrillic`, which is exactly how Ukrainian fell out of the UI font.
				return new Set(SUBSETS.filter((s) => new RegExp(`-${s}-(?!ext-)`).test(files)));
			} catch {
				/* try the other scope */
			}
		}
		return new Set<string>();
	};

	it('gives --font-display a face for every script the library is read in', () => {
		// The whole point. A stack with no Arabic family does not degrade to
		// something reasonable — it degrades to Georgia, which has no Arabic
		// either, and then to whatever the device picked.
		const stack = stackOf('font-display');
		for (const script of ['arabic', 'devanagari', 'cyrillic']) {
			const face = stack.find((f) => subsetsOf(f).has(script));
			expect(
				face,
				`--font-display names no family with a ${script} subset — ${script} prose ` +
					`renders in a system font, differently on every device`
			).toBeTruthy();
		}
	});

	it('keeps the latin face first in --font-display', () => {
		// Fraunces is the app's voice and every Latin page must still get it. The
		// script faces ship Latin too, so leading with one would quietly reset the
		// English library into Amiri's Latin. Only the FIRST is pinned: the rest of
		// the stack is checked by script coverage above, and the tail is device
		// families ('Georgia', 'Times New Roman') that no package ships.
		expect(stackOf('font-display')[0], 'no family at all').toBe('Fraunces Variable');
	});

	it('puts the chosen cyrillic face ahead of the device one', () => {
		// Georgia has Cyrillic, so Ukrainian "worked" before this — by landing on
		// whatever the platform substitutes for Georgia. A named face has to come
		// first or that is still what happens.
		const stack = stackOf('font-display');
		const chosen = stack.findIndex((f) => subsetsOf(f).has('cyrillic'));
		const decl = APP_CSS.slice(APP_CSS.indexOf('--font-display:'));
		const georgia = decl.slice(0, decl.indexOf(';')).indexOf('Georgia');
		const chosenAt = decl.slice(0, decl.indexOf(';')).indexOf(stack[chosen]);
		expect(chosen, 'no cyrillic face in --font-display').toBeGreaterThan(-1);
		expect(
			chosenAt,
			`${stack[chosen]} sits after Georgia, so Cyrillic still falls to the device face`
		).toBeLessThan(georgia);
	});

	it('declares the same stack in @theme and :root', () => {
		// The tokens are declared TWICE — once in Tailwind's `@theme inline`, which
		// generates the `font-display` utility, and once in `:root`, which is what
		// `var()` reads. They had already drifted (one carried 'Times New Roman'
		// and the other did not), and a change applied to one of them reaches only
		// half the app.
		for (const token of ['font-display', 'font-sans']) {
			// Every declaration of the token, wherever it lives — which is more
			// honest than slicing the two blocks by name, and catches a third copy
			// if one ever appears.
			const declared = [
				...APP_CSS.matchAll(new RegExp(`--${token}:([^;]+);`, 'g'))
			].map(([, value]) => [...value.matchAll(/'([^']+)'/g)].map(([, f]) => f));
			expect(declared.length, `--${token} is declared once; expected @theme and :root`)
				.toBeGreaterThan(1);
			for (const stack of declared.slice(1)) {
				expect(stack, `--${token} differs between its declarations`).toEqual(declared[0]);
			}
		}
	});

	it('never lets a reader preference resolve to a bare generic', () => {
		// `--reading-font` is ALWAYS set from FONT_STACK, so `.reading`'s
		// `var(--reading-font, var(--font-display))` fallback never fires and these
		// three strings are the whole of what the app's most-read surface is set
		// in. Two now name a token so they cannot drift from it; `dyslexic` cannot,
		// because no Arabic or Devanagari dyslexic face exists — but it must still
		// end at a real family rather than handing the script to `cursive`, which
		// matches every glyph and resolves to whatever the device felt like.
		expect(FONT_STACK.serif).toBe('var(--font-display)');
		expect(FONT_STACK.sans).toBe('var(--font-sans)');
		for (const script of ['arabic', 'devanagari']) {
			const face = [...FONT_STACK.dyslexic.matchAll(/'([^']+)'/g)]
				.map(([, f]) => f)
				.find((f) => subsetsOf(f).has(script));
			expect(
				face,
				`the dyslexic preference names no ${script} face, so an ${script} reader ` +
					`who picks it gets \`cursive\` and a device font`
			).toBeTruthy();
		}
	});

	it('does not float an initial in a script that has no such convention', () => {
		// Arabic was already excluded. Devanagari had to join it once it had a real
		// face to render in: a "letter" there is an akshara hung from the
		// shirorekha, so `::first-letter` split `मैरी` into `मै` | `री` and broke the
		// word's top bar across the float.
		const rule = /\.reading > p:first-of-type([^{]*)::first-letter/.exec(APP_CSS);
		expect(rule, 'the drop-cap rule is gone').not.toBeNull();
		for (const lang of ['ar', 'hi']) {
			expect(rule![1], `${lang} is not excluded from the floated initial`).toContain(
				`:not(:lang(${lang}))`
			);
		}
	});
});
