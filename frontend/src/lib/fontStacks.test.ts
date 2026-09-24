import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { FONT_STACK, READER_FONTS } from './readerPrefs.svelte';
import { SITE_FONTS } from './siteFont.svelte';

/** app.css with comments stripped: the prose in this file says `--font-display:`
 *  more than once, and a scan that counts those finds a declaration whose value
 *  is a paragraph. */
const stripComments = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, '');
const APP_CSS = stripComments(readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8'));
/** The site styles. Their own file, so nothing reading app.css's declarations
 *  as THE house stack (the share-card script, the gates here) sees a style. */
const SITE_CSS = stripComments(readFileSync(join(process.cwd(), 'src/lib/site-fonts.css'), 'utf-8'));
/** Every `@import '@fontsource…'` in app.css, as written. */
const IMPORTS = [...APP_CSS.matchAll(/@import '(@fontsource[^']+)'/g)].map(([, i]) => i);
/** The quoted family names in a font-family value, in order. */
const familiesIn = (value: string) => [...value.matchAll(/'([^']+)'/g)].map(([, f]) => f);

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

	/** A fontsource package directory name, from the family as CSS names it. */
	const pkgSlug = (family: string) =>
		family
			.replace(/ Variable$/, '')
			.toLowerCase()
			.replace(/ /g, '-');

	/** Does this family ship as a variable font (one file, a weight range)? */
	const isVariable = (family: string) => family.endsWith(' Variable');

	/** The subsets a fontsource family ships, from its file names. */
	// A representative codepoint per script, and coverage is asked of the
	// `unicode-range` declarations rather than of file names.
	//
	// FILE NAMES LIE, and Hanken Grotesk is the proof: it ships
	// `hanken-grotesk-cyrillic-wght-normal.woff2`, whose range is
	// U+0460-052F — the cyrillic EXTENSION block. It cannot draw Б, і, ї or є,
	// every one of which is base Cyrillic, and a filename check calls it a
	// Cyrillic face. That is the exact gap this gate exists to catch, so
	// checking it by name would have made the gate agree with the bug.
	//
	// The package slug is also part of every filename, so a name check is
	// satisfiable by the name alone: `noto-sans-arabic-latin-400-normal.woff2`
	// contains `-arabic-` and holds no Arabic. Three of the six families here
	// are named after their script.
	const PROBE: Record<string, number> = {
		latin: 0x0041, // A
		cyrillic: 0x0411, // Б — base block, not the extension
		arabic: 0x0627, // ا
		devanagari: 0x0915 // क
	};
	const SUBSETS = Object.keys(PROBE);

	/** Does this `unicode-range` value cover the codepoint? */
	const covers = (range: string, cp: number) =>
		range.split(',').some((part) => {
			const [lo, hi] = part.trim().replace(/U\+/i, '').split('-');
			const a = parseInt(lo, 16);
			const b = hi === undefined ? a : parseInt(hi, 16);
			return cp >= a && cp <= b;
		});

	/** The scripts a family can actually draw, from the ranges it declares. */
	const subsetsOf = (family: string) => {
		const slug = pkgSlug(family);
		for (const scope of ['@fontsource-variable', '@fontsource']) {
			const dir = join(process.cwd(), 'node_modules', scope, slug);
			try {
				// Every stylesheet the package ships at its top level: a family is
				// split across weight entrypoints (`400.css`) or one `index.css`, and
				// which of those exists differs between variable and static packages.
				const css = readdirSync(dir)
					.filter((f) => f.endsWith('.css'))
					.map((f) => readFileSync(join(dir, f), 'utf-8'))
					.join('\n');
				const ranges = [...css.matchAll(/unicode-range:\s*([^;}]+)/g)].map(([, r]) => r);
				// No ranges at all means the package declares no `unicode-range` —
				// its faces then cover everything they contain, which this cannot
				// determine, so it claims nothing rather than claiming coverage.
				return new Set(SUBSETS.filter((s) => ranges.some((r) => covers(r, PROBE[s]))));
			} catch {
				/* try the other scope */
			}
		}
		return new Set<string>();
	};

	it('gives --font-sans a face for every script the library is read in', () => {
		// The same property as the display stack below, and it was false for longer
		// — the chrome and the reader's "sans" preference both resolve through it.
		// Cyrillic is checked too, and it is the one that looks fine and is not:
		// Hanken ships `cyrillic-ext` (U+0460-052F) WITHOUT the base block, so a
		// stack that merely "has Hanken" still drops Б, і, ї and є. Coverage is read
		// from the files each package ships, so a family covering only an extension
		// block cannot satisfy this by name.
		const stack = stackOf('font-sans');
		for (const script of ['arabic', 'devanagari', 'cyrillic']) {
			const face = stack.find((f) => subsetsOf(f).has(script));
			expect(
				face,
				`--font-sans names no family with a ${script} subset — a reader who picks ` +
					`"sans" in that script gets a system font, differently on every device`
			).toBeTruthy();
		}
	});

	it('keeps the latin face first in --font-sans', () => {
		// Hanken is the app's UI voice and every Latin surface must keep it. The
		// script faces ship Latin too, so leading with one would quietly reset the
		// whole English interface into Noto's Latin.
		expect(stackOf('font-sans')[0], 'no family at all').toBe('Hanken Grotesk Variable');
	});

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

	/** Every family a font-family value can reach: its quoted names, then the
	 *  families of any token it names. The house tokens are the root's capture
	 *  of --font-display / --font-sans (site-fonts.css), so they resolve to
	 *  those stacks. */
	const resolved = (value: string): string[] => [
		...familiesIn(value),
		...[...value.matchAll(/var\(--(font|house)-(display|sans)\)/g)].flatMap(([, , kind]) =>
			stackOf(`font-${kind}`)
		)
	];

	it('never lets a reader preference resolve to a bare generic', () => {
		// `--reading-font` is ALWAYS set from FONT_STACK, so these strings are the
		// whole of what the app's most-read surface is set in. Resolved through
		// their tokens; the house ones, because --font-* follow the site style.
		expect(FONT_STACK.serif, 'the serif preference should name the house token').toBe(
			'var(--house-display)'
		);
		expect(FONT_STACK.sans, 'the sans preference should name the house token').toBe(
			'var(--house-sans)'
		);

		for (const pref of READER_FONTS) {
			expect(
				FONT_STACK[pref],
				`the ${pref} preference names --font-display / --font-sans, which follow the site style`
			).not.toMatch(/var\(--font-/);
			for (const script of ['arabic', 'devanagari', 'cyrillic']) {
				const face = resolved(FONT_STACK[pref]).find((f) => subsetsOf(f).has(script));
				expect(
					face,
					`the ${pref} preference resolves to no ${script} face, so a ${script} ` +
						`reader who picks it gets a generic and whatever the device substitutes`
				).toBeTruthy();
			}
		}
	});

	it('imports every reader face, upright and italic', () => {
		// A face named in FONT_STACK and never @imported is not a fallback, it is a
		// no-op: the stack skips straight to its tail and the reader's choice
		// silently does nothing. Italic too — these set whole books, and prose has
		// emphasis; without the file the browser synthesises a slant.
		// OpenDyslexic ships no italic; serif and sans name only a house token.
		const named = READER_FONTS.filter((f) => f !== 'dyslexic' && familiesIn(FONT_STACK[f]).length);
		for (const pref of named) {
			const [family] = familiesIn(FONT_STACK[pref]);
			const [scope, up, it] = isVariable(family)
				? ['@fontsource-variable', 'wght', 'wght-italic']
				: ['@fontsource', '400', '400-italic'];
			const pkg = `${scope}/${pkgSlug(family)}`;
			expect(IMPORTS, `${family} (${pref}) is never imported upright`).toContain(`${pkg}/${up}.css`);
			expect(IMPORTS, `${family} (${pref}) is never imported in italic`).toContain(`${pkg}/${it}.css`);
		}
	});

	describe('site styles', () => {
		/** Each `selector { … }` block in site-fonts.css. */
		const blocks = [...SITE_CSS.matchAll(/([^{}]+)\{([^}]*)\}/g)].map(([, sel, body]) => ({
			sel: sel.trim(),
			body
		}));
		const styles = blocks.filter((b) => /data-site-font='[a-z]+'/.test(b.sel));

		it('declares the styles the store offers', () => {
			const declared = styles.map((b) => /data-site-font='([a-z]+)'/.exec(b.sel)![1]);
			expect(new Set(declared)).toEqual(new Set(SITE_FONTS.filter((f) => f !== 'house')));
		});

		it('captures the house stacks on the root and applies a style below it', () => {
			// The whole mechanism. The capture resolves on the root against the house
			// stack; a style declared ON the root would be captured instead, and the
			// reader's "Serif" would follow the menus.
			const root = blocks.find((b) => b.sel === ':root');
			expect(root?.body).toMatch(/--house-display:\s*var\(--font-display\)/);
			expect(root?.body).toMatch(/--house-sans:\s*var\(--font-sans\)/);
			for (const b of blocks.filter((b) => /--font-(display|sans):/.test(b.body))) {
				expect(b.sel, `${b.sel} re-points a font token on the root itself`).toMatch(
					/\s(body|:is\(.+\))$/
				);
			}
		});

		it('keeps covers in the house faces', () => {
			// A cover's byline is the one constant line across the shelf; it must not
			// change with the menus.
			const pin = blocks.find((b) => b.sel.includes('.cover-type'));
			expect(pin?.sel).toContain('.cover-plate');
			expect(pin?.body).toMatch(/--font-display:\s*var\(--house-display\)/);
			expect(pin?.body).toMatch(/--font-sans:\s*var\(--house-sans\)/);
		});

		it('gives every style a face for every script, and imports its lead face', () => {
			for (const { sel, body } of styles) {
				for (const [, token, value] of body.matchAll(/--(font-display|font-sans):([^;]+);/g)) {
					const stack = resolved(value);
					for (const script of ['latin', 'arabic', 'devanagari', 'cyrillic']) {
						expect(
							stack.find((f) => subsetsOf(f).has(script)),
							`${sel} sets --${token} with no ${script} face`
						).toBeTruthy();
					}
					expect(
						IMPORTS.some((i) => i.includes(`/${pkgSlug(stack[0])}/`)),
						`${sel}: ${stack[0]} is never imported`
					).toBe(true);
				}
			}
		});
	});

	it('imports every weight the prose actually sets', () => {
		// A family with no @font-face for the weight asked does NOT fall through to
		// the next family — it renders in the nearest weight it has. PT Serif was
		// imported at 700 alone, correctly, while only `--cover-face-house` named
		// it; the moment `--font-display` did, Ukrainian body prose at 400 would
		// have come out bold. Nothing caught it, because a stack that names the
		// right family looks right.
		//
		// 400 is the floor because `.reading` sets no font-weight, so prose is 400;
		// headings that use --font-display go bolder, but those are Latin-first and
		// land on Fraunces, which is variable.
		const imported = new Set(
			IMPORTS.flatMap((i) => /\/([a-z-]+)\/(\d{3})\.css$/.exec(i)?.slice(1).join('/') ?? [])
		);
		for (const family of [...stackOf('font-display'), ...stackOf('font-sans')]) {
			const slug = pkgSlug(family);
			// Variable faces carry a range and need no per-weight file; a family the
			// app does not import at all is either a device face (Georgia) or is
			// caught by the coverage gate above.
			if (!subsetsOf(family).size || isVariable(family)) continue;
			expect(
				imported.has(`${slug}/400`),
				`--font-display names ${family} for prose but app.css never imports ` +
					`${slug}/400.css — prose would render in whatever weight it did import`
			).toBe(true);
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
