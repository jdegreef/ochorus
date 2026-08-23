import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { AUTHOR_STYLE, COVER_STYLES, ERA_STYLE, coverStyleFor } from './coverStyles';
import { ERAS, eraOf } from './eras';

/**
 * The cover style table — the thing that stops a shelf of books reading as one
 * publisher's back catalogue.
 *
 * These are not taste tests. They guard the three ways the table can be wrong
 * in a way nobody sees: a recipe that names a face nothing loads, an override
 * that says what its era already said, and an era with no recipe at all —
 * which would hand `undefined` to a component that would then draw the title in
 * whatever the browser felt like.
 */
describe('cover styles', () => {
	it('gives every era a recipe', () => {
		// A missing one is not a fallback, it is an undefined lookup: the style
		// reaches the pixel as `--cover-face: undefined`.
		for (const era of ERAS) {
			expect(ERA_STYLE[era.id], `no cover style for the ${era.id} era`).toBeTruthy();
			expect(COVER_STYLES[ERA_STYLE[era.id]]).toBeDefined();
		}
	});

	it('names a face token for every recipe, never a family', () => {
		// The stacks live in app.css beside the @import that loads them (see
		// coverStyles.ts). A family named here would be a face nothing fetches —
		// which fails silently, as the browser just uses the next stack entry.
		for (const [id, style] of Object.entries(COVER_STYLES)) {
			expect(style.id, `${id} disagrees with its own key`).toBe(id);
			expect(style.face, `${id} names a family instead of a token`).toMatch(
				/^var\(--cover-face-[a-z]+\)$/
			);
		}
	});

	it('names only face tokens app.css actually declares and loads', () => {
		// The two halves of a face live apart by necessity: the @import that
		// fetches the file and the token that names it are CSS, the recipe that
		// picks one is TypeScript. A token with no declaration resolves to
		// nothing and the title falls to the browser default — no error, no
		// warning, just one book on the shelf in Times.
		const css = readFileSync(join(process.cwd(), 'src/app.css'), 'utf-8');
		for (const style of Object.values(COVER_STYLES)) {
			const token = style.face.slice('var('.length, -1);
			expect(css, `${token} is named by a cover style but not declared`).toContain(`${token}:`);
			// The house recipe is Fraunces, which the app already loads for
			// everything else; the other five each need their own package.
			const family = /'([^']+)'/.exec(
				css.slice(css.indexOf(`${token}:`), css.indexOf('\n', css.indexOf(`${token}:`)))
			);
			if (family) {
				const pkg = family[1].replace(/ Variable$/, '').toLowerCase().replace(/ /g, '-');
				expect(css, `nothing @imports ${family[1]}`).toMatch(new RegExp(`@import '@fontsource[^']*/${pkg}`));
			}
		}
	});

	it('asks each face only for a weight it has', () => {
		// Two of the five are static 400-only files, and asking 600 of those gets
		// a synthesised bold — smeared stems, filled counters. It looks like a
		// bad font rather than a bad number, so it is the kind of thing that
		// ships.
		const STATIC_400 = ['press', 'enlightenment'];
		for (const id of STATIC_400) {
			expect(COVER_STYLES[id as keyof typeof COVER_STYLES].weight, `${id} would synthesise`).toBe(
				400
			);
		}
	});

	it('keeps the override table to actual exceptions', () => {
		// An entry that agrees with its era is a second copy of ERA_STYLE, and
		// the copy is what stops being true when an era's recipe changes.
		// Birth years come from the shipped authors fixture.
		const BIRTHS: Record<string, number> = {
			'thomas-a-kempis': 1380,
			'jeanne-guyon': 1648,
			'william-law': 1686,
			'charles-finney': 1792,
			'andrew-murray': 1828,
			'frederick-brotherton-meyer': 1847,
			'hannah-whitall-smith': 1832,
			'amy-carmichael': 1867
		};
		for (const [slug, id] of Object.entries(AUTHOR_STYLE)) {
			expect(BIRTHS[slug], `${slug} has no birth year here — add one`).toBeTypeOf('number');
			expect(id, `${slug}'s override is what their era already gives them`).not.toBe(
				ERA_STYLE[eraOf(BIRTHS[slug])]
			);
		}
	});

	it('dresses an author it has never heard of', () => {
		// An admin import, or a contributor added this morning. Every branch has
		// to land on a real recipe: a book with no style looks broken next to one
		// with, and "no style" is what a new author is by definition.
		expect(coverStyleFor(eraOf(1620), 'nobody-in-any-table')).toBe(COVER_STYLES.press);
		expect(coverStyleFor(eraOf(null), 'nobody-in-any-table')).toBe(COVER_STYLES.house);
	});

	it('prefers the author over their century', () => {
		// Murray is missionary-era, and his era is set in a Victorian display
		// face; his own books are devotional manuals. Seven editions hang on this
		// line being read in this order.
		expect(coverStyleFor(eraOf(1828), 'andrew-murray')).toBe(COVER_STYLES.devotional);
		expect(coverStyleFor(eraOf(1828), 'charles-h-spurgeon')).toBe(COVER_STYLES.revival);
	});
});
