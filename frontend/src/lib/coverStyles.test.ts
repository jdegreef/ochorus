import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import type { CoverScript } from './coverStyles';
import {
	AUTHOR_STYLE,
	COVER_SCRIPTS,
	COVER_STYLE_IDS,
	CURSIVE_SCRIPTS,
	ERA_STYLE,
	coverStyleFor,
	scriptOf
} from './coverStyles';
import { ERAS, eraOf } from './eras';
import { COVER_CSS, COVER_CSS_CODE, lastDecl } from '../test/coverCss';

const CONTENT = resolve(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content');

/** A font family's fontsource package name. One rule, three readers: the two
 *  `@import` gates and the package-directory probe. */
const pkgSlug = (family: string) =>
	family
		.replace(/ Variable$/, '')
		.toLowerCase()
		.replace(/ /g, '-');
const APP_CSS = readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8');


/**
 * The cover style table — the thing that stops a shelf of books reading as one
 * publisher's back catalogue.
 *
 * These are not taste tests. The table decides a recipe's NAME and
 * `cover-type.css` describes it, so what can go wrong silently is the join
 * between them: a name with no block renders in the house serif, and a block
 * naming a face nothing loads renders in whatever the browser felt like. Both
 * look like a design decision rather than a fault, which is why they are gated
 * here — that exact defect shipped 37 share cards set in Times.
 */
describe('cover styles', () => {
	/** The `.style-<id> .title` recipes the CSS actually defines. */
	const cssRecipes = () =>
		new Set([...COVER_CSS.matchAll(/\.cover-type\.style-([a-z]+)\s+\.title/g)].map(([, id]) => id));

	it('gives every era a recipe', () => {
		// A missing one is not a fallback, it is an undefined lookup.
		for (const era of ERAS) {
			expect(ERA_STYLE[era.id], `no cover style for the ${era.id} era`).toBeTruthy();
			expect(COVER_STYLE_IDS).toContain(ERA_STYLE[era.id]);
		}
	});

	it('describes every recipe in the CSS, and names every CSS recipe here', () => {
		// Both directions: an id with no block is a book in the house serif that
		// was meant to look like its century, and a block with no id is dead CSS
		// nothing can select.
		const inCss = cssRecipes();
		for (const id of COVER_STYLE_IDS) {
			expect(inCss, `.cover-type.style-${id} .title is missing from cover-type.css`).toContain(id);
		}
		for (const id of inCss) {
			expect(
				COVER_STYLE_IDS,
				`cover-type.css styles .style-${id}, which no recipe names`
			).toContain(id);
		}
	});

	it('names only face tokens app.css declares and loads', () => {
		// The halves of a face live apart by necessity: the @import that fetches
		// the file and the token that names it are CSS, the recipe that picks one
		// is a class. A token with no declaration makes the whole declaration
		// invalid and the title falls back — silently, and only on the covers
		// wearing that one recipe.
		const tokens = [...COVER_CSS.matchAll(/var\((--cover-face-[a-z]+)\)/g)].map(([, t]) => t);
		expect(tokens.length, 'no recipe names a face token').toBeGreaterThan(0);
		for (const token of new Set(tokens)) {
			expect(APP_CSS, `${token} is named by a recipe but not declared`).toContain(`${token}:`);
			const decl = APP_CSS.slice(APP_CSS.indexOf(`${token}:`));
			const family = /'([^']+)'/.exec(decl.slice(0, decl.indexOf('\n')));
			// The house recipe is Fraunces, which the app already loads for
			// everything else; the other five each need their own package.
			if (family) {
				const pkg = pkgSlug(family[1]);
				expect(APP_CSS, `nothing @imports ${family[1]}`).toMatch(
					new RegExp(`@import '@fontsource[^']*/${pkg}`)
				);
			}
		}
	});

	it('asks each face only for a weight it has', () => {
		// Two of the five ship one static weight, and asking those for a bolder
		// one gets a synthesised bold — smeared stems, filled counters. It looks
		// like a bad font rather than a bad number, so it is the kind of thing
		// that ships.
		for (const id of ['press', 'enlightenment']) {
			// The weight that WINS, not the first written: a style writes `.title`
			// twice now — once in the container gate for its face, once outside for
			// its composition's leading — and reading the first found reported no
			// weight at all. `lastDecl` is that cascade rule, kept in one place.
			const weight = lastDecl(`.cover-type.style-${id} .title`, /font-weight:\s*(\d+)/);
			expect(weight, `.style-${id} asks for no weight at all`).not.toBeNull();
			expect(weight, `${id} would synthesise a bold`).toBe('400')
		}
	});

	it('only asks for a face once a cover is big enough to show one', () => {
		// A cover is drawn at 48px in a list row and 64px in an author's rail,
		// where the title sets at ~4.5px. /biographies renders nothing but those
		// rails, and would otherwise pull ~184 KB of display faces to draw type
		// nobody can tell apart. A font file is fetched only when a glyph renders
		// in it, so the container gate is what keeps that page from paying.
		//
		// BOTH OFFSETS COME FROM THE COMMENT-STRIPPED TEXT, and they have to: the
		// ornament section now contains the words "@container" in PROSE, 237 lines
		// above the real at-rule, so a raw `indexOf` anchors on the paragraph and
		// every face below it clears a threshold that means nothing — the gate
		// would have stayed green over a `var(--cover-face-*)` added anywhere in
		// the composition section. Mixing the two texts is just as bad: a stripped
		// index and a raw one are different coordinate systems, and comparing them
		// drifts by the length of every comment between.
		const gate = COVER_CSS_CODE.indexOf('@container');
		expect(gate, 'the recipes are no longer behind a container query').toBeGreaterThan(-1);
		for (const token of [...COVER_CSS_CODE.matchAll(/var\((--cover-face-[a-z]+)\)/g)]) {
			expect(
				token.index,
				`${token[1]} is named outside the container gate — a thumbnail would fetch it`
			).toBeGreaterThan(gate);
		}
	});

	it('keeps the override table to actual exceptions', () => {
		// An entry that agrees with its era is a second copy of ERA_STYLE, and the
		// copy is what stops being true when an era's recipe changes. Birth years
		// come from the shipped fixture — a hardcoded table here would keep
		// asserting against a year the library had since corrected.
		const births = new Map<string, number | null>(
			JSON.parse(readFileSync(join(CONTENT, 'authors.json'), 'utf8')).map(
				(r: { fields: { slug: string; birth_year: number | null } }) => [
					r.fields.slug,
					r.fields.birth_year ?? null
				]
			)
		);
		for (const [slug, id] of Object.entries(AUTHOR_STYLE)) {
			expect(births.has(slug), `${slug} is styled but is not in authors.json`).toBe(true);
			expect(id, `${slug}'s override is what their era already gives them`).not.toBe(
				ERA_STYLE[eraOf(births.get(slug) ?? null)]
			);
		}
	});

	it('dresses an author it has never heard of', () => {
		// An admin import, or a contributor added this morning. Every branch has
		// to land on a real recipe: a book with no style looks broken next to one
		// with, and "no style" is what a new author is by definition.
		expect(coverStyleFor(eraOf(1620), 'nobody-in-any-table')).toBe('press');
		expect(coverStyleFor(eraOf(null), 'nobody-in-any-table')).toBe('house');
	});

	it('prefers the author over their century', () => {
		// Murray is missionary-era, and his era is set in a Victorian display
		// face; his own books are devotional manuals. Seven editions hang on this
		// line being read in this order.
		expect(coverStyleFor(eraOf(1828), 'andrew-murray')).toBe('devotional');
		expect(coverStyleFor(eraOf(1828), 'charles-h-spurgeon')).toBe('revival');
	});
});

/**
 * The scripts the recipes were not written in.
 *
 * Ochorus reads in eight languages and the recipes above were evened out by eye
 * against Latin faces. Three of those languages are not Latin, and until now not
 * one of the six stacks named a face that could draw them — so every Arabic and
 * Hindi cover, and four of six Ukrainian ones, came out in whatever serif the
 * device happened to ship. That is the defect these gate; each of them fails on
 * a way of half-fixing it that would still look deliberate.
 */
describe('cover scripts', () => {
	/** A fontsource package's directory, from the family name in a stack. */
	const packageDir = (family: string) => {
		const slug = pkgSlug(family);
		for (const scope of ['@fontsource-variable', '@fontsource']) {
			const dir = join(process.cwd(), 'node_modules', scope, slug);
			try {
				readFileSync(join(dir, 'index.css'));
				return dir;
			} catch {
				/* try the other scope */
			}
		}
		return null;
	};

	/** The unicode subsets a family ships, read off its files.
	 *
	 *  Matched against a known vocabulary rather than parsed positionally: a
	 *  family name can itself contain the separator, and `im-fell-english-latin
	 *  -400-normal.woff2` read positionally says its subset is "fell". */
	const SUBSETS = ['latin', 'cyrillic', 'arabic', 'devanagari', 'greek', 'vietnamese'];
	const subsetsOf = (family: string) => {
		const dir = packageDir(family);
		if (!dir) return new Set<string>();
		const files = readdirSync(join(dir, 'files')).join('\n');
		// `-latin-` would also match inside `-latin-ext-`, and a family can ship
		// the extension without the base; the negative lookahead keeps them apart.
		return new Set(SUBSETS.filter((s) => new RegExp(`-${s}-(?!ext-)`).test(files)));
	};

	/** The weights a family can actually draw — a range for a variable face. */
	const weightsOf = (family: string) => {
		const dir = packageDir(family);
		if (!dir) return null;
		const css = readFileSync(join(dir, 'index.css'), 'utf-8');
		const variable = /font-weight:\s*(\d+)\s+(\d+)/.exec(css);
		if (variable) {
			const [, lo, hi] = variable;
			return (w: number) => w >= Number(lo) && w <= Number(hi);
		}
		const have = new Set(
			readdirSync(join(dir, 'files')).flatMap((f) => {
				const m = /-(\d{3})-/.exec(f);
				return m ? [Number(m[1])] : [];
			})
		);
		return (w: number) => have.has(w);
	};

	/** The families a `--cover-face-*` stack names, in order. */
	const stackOf = (style: string) => {
		const at = APP_CSS.indexOf(`--cover-face-${style}:`);
		expect(at, `--cover-face-${style} is not declared`).toBeGreaterThan(-1);
		const decl = APP_CSS.slice(at, APP_CSS.indexOf(';', at));
		return [...decl.matchAll(/'([^']+)'/g)].map(([, f]) => f);
	};

	/** What `font-weight` a (script, style) cover actually resolves to.
	 *
	 *  The cascade, spelled out: a block carrying BOTH classes outranks either
	 *  alone; a script-only block and a style-only block tie on specificity, and
	 *  the script blocks sit later in the file, so they win. */
	const weightFor = (script: CoverScript, style: string): number => {
		// EVERY block for a selector, and the LAST declaration wins — not the
		// first match. A selector legitimately appears twice now (the sizes sit
		// inside the container gate, the corrections outside it), and a
		// first-match lookup silently read the block that does not set the
		// property and reported the wrong answer.
		const find = (selector: string) => {
			const blocks = [
				...COVER_CSS.matchAll(
					new RegExp(`${selector.replace(/[.\\]/g, '\\$&')}[^{]*\\{([^}]*)\\}`, 'g')
				)
			];
			const weights = blocks.flatMap((b) => {
				const w = /font-weight:\s*(\d+)/.exec(b[1]);
				return w ? [Number(w[1])] : [];
			});
			return weights.length ? weights[weights.length - 1] : null;
		};
		return (
			find(`.cover-type.script-${script}.style-${style} .title`) ??
			find(`.cover-type.script-${script} .title`) ??
			find(`.cover-type.style-${style} .title`) ??
			600
		);
	};

	it('describes every script in the CSS, and names every CSS script here', () => {
		const inCss = new Set(
			[...COVER_CSS.matchAll(/\.cover-type\.script-([a-z]+)/g)].map(([, id]) => id)
		);
		for (const script of COVER_SCRIPTS) {
			expect(inCss, `.cover-type.script-${script} is missing from cover-type.css`).toContain(
				script
			);
		}
		for (const id of inCss) {
			expect(COVER_SCRIPTS, `cover-type.css corrects .script-${id}, which no script names`).toContain(
				id
			);
		}
	});

	it('gives every recipe a face for every script', () => {
		// The whole point. A stack with no Arabic family in it does not fall back
		// to something reasonable — it falls back to Georgia, which has no Arabic
		// either, and then to whatever the device picked.
		for (const style of COVER_STYLE_IDS) {
			const stack = stackOf(style);
			for (const script of COVER_SCRIPTS) {
				// A script id IS its fontsource subset name, so there is nothing to
				// translate between them.
				const face = stack.find((f) => subsetsOf(f).has(script));
				expect(
					face,
					`--cover-face-${style} names no family with a ${script} subset — a ${script} ` +
						`title in that recipe renders in a system font`
				).toBeTruthy();
			}
		}
	});

	it('keeps the latin face first in every stack', () => {
		// `scripts/generate-cover-og.mjs` takes the FIRST quoted family in a token
		// as the one to inline into a share card, and the cards are English — so
		// that family has to be the one that draws Latin. Lead a stack with a
		// script face and the card embeds an Arabic font while its real face goes
		// unembedded, which is the defect that once shipped 37 cards set in Times.
		//
		// "Ships a latin subset" is not enough on its own to express this: Amiri
		// ships one too, and an English title set in Amiri's Latin is exactly the
		// mistake. So a leading family must also NOT be a non-Latin script face.
		// A Latin-and-Cyrillic face leading (PT Serif, Old Standard TT) would pass
		// here, and should: it can still draw the card. The gate is against a
		// script face leading, not against every reordering.
		for (const style of COVER_STYLE_IDS) {
			const [first] = stackOf(style);
			expect(first, `--cover-face-${style} names no family at all`).toBeTruthy();
			const subsets = subsetsOf(first);
			expect(
				subsets.has('latin'),
				`--cover-face-${style} leads with ${first}, which ships no latin subset`
			).toBe(true);
			for (const script of ['arabic', 'devanagari']) {
				expect(
					subsets.has(script),
					`--cover-face-${style} leads with ${first}, a ${script} face — an English ` +
						`share card would embed it and set the title in its latin`
				).toBe(false);
			}
		}
	});

	it('imports every family every stack names, not just the first', () => {
		// The existing gate above checks the first family; these stacks now carry
		// four, and an unimported one is a silent fallback for one script only.
		for (const style of COVER_STYLE_IDS) {
			for (const family of stackOf(style)) {
				const pkg = pkgSlug(family);
				expect(APP_CSS, `nothing @imports ${family}, named by --cover-face-${style}`).toMatch(
					new RegExp(`@import '@fontsource[^']*/${pkg}[/']`)
				);
			}
		}
	});

	it('asks each script face only for a weight it has', () => {
		// The same rule the Latin recipes follow, and it bites harder here: Amiri
		// and Tiro ship fewer weights than the faces they stand beside, so the
		// recipes asking 500 and 600 would every one of them have been served a
		// synthesised bold.
		for (const script of COVER_SCRIPTS) {
			for (const style of COVER_STYLE_IDS) {
				const face = stackOf(style).find((f) => subsetsOf(f).has(script));
				if (!face) continue; // the gate above owns that failure
				const has = weightsOf(face);
				const asked = weightFor(script, style);
				expect(
					has && has(asked),
					`${script} + ${style} resolves to ${face} at weight ${asked}, which it has ` +
						`not got — that is a synthesised bold`
				).toBe(true);
			}
		}
	});

	it('never tracks a cursive script', () => {
		// Not taste. Arabic letters JOIN, and letter-spacing prises the joins
		// apart into disconnected shapes; Devanagari has conjuncts that break the
		// same way. Five of the six recipes set a tracking, `inscriptional` at
		// 0.06em, and every one of them was doing this.
		for (const script of CURSIVE_SCRIPTS) {
			// Across every block for the selector: the tracking is set in the one
			// outside the container gate, the sizes in the one inside it.
			const blocks = [
				...COVER_CSS.matchAll(
					new RegExp(`\\.cover-type\\.script-${script} \\.title \\{([^}]*)\\}`, 'g')
				)
			];
			expect(blocks.length, `no .script-${script} .title block`).toBeGreaterThan(0);
			expect(
				blocks.map((b) => b[1]).join(''),
				`${script} titles would be tracked apart`
			).toMatch(/letter-spacing:\s*0(?![.\d])/);
		}
	});

	it('never fakes an italic in a script that has none', () => {
		// The subtitle is italic, and neither Arabic nor Devanagari has one — so
		// the browser obliges by slanting the upright, which is a synthesis
		// nobody drew. Cyrillic is absent on purpose: both its faces ship a real
		// italic.
		for (const script of ['arabic', 'devanagari']) {
			expect(
				COVER_CSS,
				`.script-${script} .subtitle still asks for an italic that does not exist`
			).toMatch(
				new RegExp(`\\.cover-type\\.script-${script} \\.subtitle[^{]*\\{[^}]*font-style:\\s*normal`)
			);
		}
	});

	it('corrects the scripts after the recipes it is correcting', () => {
		// `.cover-type.script-arabic .title` and `.cover-type.style-press .title`
		// are both three classes, so nothing but source order decides which wins.
		// Move the script blocks above the recipes and the corrections silently
		// stop applying — every gate here would still pass.
		const lastRecipe = Math.max(
			...COVER_STYLE_IDS.map((id) => COVER_CSS.indexOf(`.cover-type.style-${id} .title`))
		);
		const firstScript = COVER_CSS.indexOf('.cover-type.script-');
		expect(firstScript, 'no script block at all').toBeGreaterThan(-1);
		expect(
			firstScript,
			'a script block sits above the recipes it corrects, so it loses the cascade'
		).toBeGreaterThan(lastRecipe);
	});

	it('derives a script for languages nobody has added yet', () => {
		// The staleness this is here to prevent: an admin can add a language with
		// no deploy, so a hand-written table of language codes would be right
		// about every code it listed and silently wrong about the new one — the
		// face still working while every correction stopped. Deriving through
		// `Intl.Locale.maximize()` means Urdu and Farsi and Marathi are already
		// answered.
		const expected: Record<string, string | null> = {
			// shipped today
			ar: 'arabic',
			hi: 'devanagari',
			uk: 'cyrillic',
			en: null,
			es: null,
			pt: null,
			sw: null,
			lg: null,
			// not shipped, and answered anyway
			ur: 'arabic',
			fa: 'arabic',
			ps: 'arabic',
			mr: 'devanagari',
			ne: 'devanagari',
			ru: 'cyrillic',
			sr: 'cyrillic',
			// a script with no recipe corrections is left exactly as it is today,
			// rather than corrected by numbers measured against another font
			he: null,
			ja: null,
			ta: null
		};
		for (const [code, script] of Object.entries(expected)) {
			expect(scriptOf(code), `${code} should resolve to ${script}`).toBe(script);
		}
	});

	it('corrects the language codes the library actually ships', () => {
		// Every language with book rows must resolve to something the CSS knows,
		// or to null — a language resolving to a script with no `.script-*` block
		// would take a class nothing styles.
		const languages = new Set(
			readdirSync(join(CONTENT, 'books')).map((f) => f.split('.')[1])
		);
		for (const code of languages) {
			const script = scriptOf(code);
			if (script !== null) {
				expect(COVER_SCRIPTS, `${code} resolves to ${script}, which has no block`).toContain(
					script
				);
			}
		}
	});

	it('leaves no script correction unreachable', () => {
		// A `.script-*` block no language can ever wear is CSS nobody reads.
		const reachable = new Set(
			[...new Set(readdirSync(join(CONTENT, 'books')).map((f) => f.split('.')[1]))]
				.map((code) => scriptOf(code))
				.filter((s) => s !== null)
		);
		for (const script of COVER_SCRIPTS) {
			expect(
				reachable,
				`no language in the library resolves to ${script} — its corrections never apply`
			).toContain(script);
		}
	});
});
