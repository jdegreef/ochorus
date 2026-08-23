import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { AUTHOR_STYLE, COVER_STYLE_IDS, ERA_STYLE, coverStyleFor } from './coverStyles';
import { ERAS, eraOf } from './eras';

const CONTENT = resolve(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content');
const APP_CSS = readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8');
const COVER_CSS = readFileSync(join(process.cwd(), 'src/lib/components/cover-type.css'), 'utf-8');

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
				const pkg = family[1]
					.replace(/ Variable$/, '')
					.toLowerCase()
					.replace(/ /g, '-');
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
			const block = new RegExp(`\\.cover-type\\.style-${id} \\.title \\{([^}]*)\\}`).exec(COVER_CSS);
			expect(block, `no .style-${id} block to check`).not.toBeNull();
			expect(block![1], `${id} would synthesise a bold`).toMatch(/font-weight:\s*400/);
		}
	});

	it('only asks for a face once a cover is big enough to show one', () => {
		// A cover is drawn at 48px in a list row and 64px in an author's rail,
		// where the title sets at ~4.5px. /biographies renders nothing but those
		// rails, and would otherwise pull ~184 KB of display faces to draw type
		// nobody can tell apart. A font file is fetched only when a glyph renders
		// in it, so the container gate is what keeps that page from paying.
		const gate = COVER_CSS.indexOf('@container');
		expect(gate, 'the recipes are no longer behind a container query').toBeGreaterThan(-1);
		for (const token of [...COVER_CSS.matchAll(/var\((--cover-face-[a-z]+)\)/g)]) {
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
