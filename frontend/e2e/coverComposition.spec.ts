import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

import { coverPlateMarkup, type CoverCardBook } from '../src/lib/coverCardMarkup';

/**
 * A cover's composition, MEASURED — the one thing no other gate can see.
 *
 * Three files already guard this stylesheet and not one of them renders it.
 * `coverComposition.test.ts` matches regexes against the CSS text, so it proves
 * the sheet SAYS something; `coverMarkupParity.test.ts` compares two element
 * trees in jsdom, which has no layout engine and so reports every box as 0x0;
 * `tests_fixture` measures contrast against the artwork, before any type exists.
 * Between them they cover what the cover is made of and nothing about where any
 * of it lands.
 *
 * That gap is not theoretical. Editing this stylesheet by replacing the span
 * between two anchors, I once swallowed the whole `.cover-type` block — the flex
 * column, the padding, the frame inset. Every gate stayed green. I looked at the
 * broken render, decided it was an artifact of my harness, and moved on; what
 * eventually caught it was a completely unrelated byte diff in the share cards.
 * A rule that says "the byline is above the title" cannot be satisfied by a
 * stylesheet that no longer lays anything out.
 *
 * WHY IT ASSERTS RELATIONSHIPS RATHER THAN COORDINATES. A reference screenshot
 * would catch this too, and would also fail on every deliberate change, on a
 * font tweak, and on a different Chromium build — a gate that cries wolf gets
 * `--update-snapshots` run on it unread, which is worse than no gate. What is
 * asserted here is what a person means by "the cover isn't broken": the parts
 * are in the right order, none of them has collapsed, and nothing has escaped
 * the plate. Those hold for every style, every script, and any reasonable
 * redesign — so a failure here is a real failure.
 *
 * It lives in `e2e/` for one practical reason: Chromium. CI installs the browser
 * for this job only, after the vitest job has already run, so a rendering test
 * anywhere else would have nothing to render in. It needs neither the dev server
 * nor the API — `setContent` is the whole harness, the same way
 * `scripts/generate-cover-og.mjs` draws a share card.
 */

const W = 600;
const H = 800;

const CSS = readFileSync(join(process.cwd(), 'src/lib/components/cover-type.css'), 'utf8');
const LOCKUP = readFileSync(join(process.cwd(), 'src/lib/brand/ochorus-lockup.svg'), 'utf8');

/**
 * The cover, alone on a page.
 *
 * The three rules under the stylesheet are the ones a cover normally gets from
 * the app around it: the card's box, the ground's placement, and the container
 * the `cq` units resolve against. Copied from `generate-cover-og.mjs`, which
 * needs exactly the same three for exactly the same reason — a `.cover-plate`
 * with no sized ancestor makes every `cq` length zero, and this file would then
 * be measuring a cover that is 0px wide and calling the relationships fine.
 */
function page(book: CoverCardBook): string {
	return `<!doctype html><style>${CSS}
html,body{margin:0}
.card{position:relative;width:${W}px;height:${H}px;overflow:hidden}
.ground{position:absolute;inset:0;width:100%;height:100%;background:#243b53}
.cover-type{box-sizing:border-box}
.brandmark svg{height:var(--h);width:auto;display:block;margin:0 auto}
</style><div class="card"><div class="ground"></div>${coverPlateMarkup(book, LOCKUP)}</div>`;
}

type Box = { x: number; y: number; width: number; height: number };

/** The rendered box of one selector, failing loudly when it is not there. */
async function box(p: Page, selector: string): Promise<Box> {
	const el = p.locator(selector);
	await expect(el, `${selector} is not in the cover at all`).toHaveCount(1);
	const b = await el.boundingBox();
	expect(b, `${selector} has no box — it is display:none or detached`).not.toBeNull();
	return b!;
}

const BOOKS: Array<[string, CoverCardBook]> = [
	[
		'a plate',
		{ author: 'Andrew Murray', title: 'Waiting on God', style: 'devotional', lang: 'en', art: false }
	],
	[
		'a painting with a subtitle',
		{
			author: 'Hannah Whitall Smith',
			title: 'The God of All Comfort',
			subtitle: 'A Study in the Life of Faith',
			style: 'revival',
			lang: 'en',
			art: true,
			scrim: 0.9
		}
	],
	[
		'a long title in Devanagari',
		{
			author: 'Andrew Murray',
			title: 'परमेश्वर की प्रतीक्षा करना सीखो',
			style: 'devotional',
			script: 'devanagari',
			lang: 'hi',
			art: false
		}
	],
	[
		// The tallest title block the library draws: a series numeral above a
		// four-line title in the heaviest recipe, over a two-line subtitle.
		'a series volume with a long title and subtitle',
		{
			author: 'John Bunyan',
			title: "The Pilgrim's Progress in Words of One Syllable",
			subtitle: "Bunyan's classic retold for young readers by Mary Godolphin",
			style: 'young',
			volume: '3',
			lang: 'en',
			art: false
		}
	],
	[
		'right-to-left Arabic',
		{
			author: 'Andrew Murray',
			title: 'انتظار الله',
			style: 'press',
			script: 'arabic',
			lang: 'ar',
			art: false
		}
	]
];

test.describe('a cover is composed the way a cover is', () => {
	for (const [name, book] of BOOKS) {
		test(`${name} keeps its parts in place`, async ({ page: p }) => {
			await p.setViewportSize({ width: W, height: H });
			await p.setContent(page(book));
			await p.evaluate(() => document.fonts.ready);

			const plate = await box(p, '.cover-plate');
			const type = await box(p, '.cover-type');
			const byline = await box(p, '.byline');
			const title = await box(p, '.title');
			const mark = await box(p, '.brandmark');

			// THE PLATE FILLS THE CARD. Everything below is relative to it, so a
			// collapsed plate would make every other assertion vacuously true.
			expect(plate.width, 'the plate is not the width of the card').toBeCloseTo(W, 0);
			expect(plate.height, 'the plate is not the height of the card').toBeCloseTo(H, 0);

			// THE TYPE BLOCK FILLS THE PLATE. Not the check that catches a deleted
			// `.cover-type` — verified by deleting it, and this still passed,
			// because `.cover-plate.over-file .cover-type` sizes the box from a
			// different rule. It covers the case where THAT one goes instead.
			expect(type.height, 'the type block has collapsed — it no longer fills the plate')
				.toBeGreaterThan(H * 0.9);

			// READING ORDER, top to bottom, with no overlap. Each of these is a real
			// way a cover breaks: a byline that has fallen through the title, a
			// brandmark that has floated up into it.
			expect(byline.y + byline.height, 'the byline overlaps the title')
				.toBeLessThanOrEqual(title.y + 1);
			expect(title.y + title.height, 'the title overlaps the brandmark')
				.toBeLessThanOrEqual(mark.y + 1);
			// A series numeral sits between the two, and is the element most
			// likely to push the title block into the byline above it.
			if (book.volume) {
				const volume = await box(p, '.volume');
				expect(byline.y + byline.height, 'the byline overlaps the series numeral')
					.toBeLessThanOrEqual(volume.y + 1);
				expect(volume.y + volume.height, 'the series numeral overlaps the title')
					.toBeLessThanOrEqual(title.y + 1);
			}
			// A long title pushes its subtitle down, and on a plate the emblem is
			// drawn into the band below — which is exactly where this broke while
			// the young recipe's title size was being set.
			if (book.subtitle && !book.art) {
				const subtitle = await box(p, '.subtitle');
				const band = await box(p, '.emblem-band');
				expect(subtitle.y + subtitle.height, 'the subtitle runs into the emblem')
					.toBeLessThanOrEqual(band.y + 1);
			}

			// NOTHING IS INVISIBLE. A zero-width title still has a position, and
			// every ordering assertion above is happy with it.
			for (const [what, b] of [['byline', byline], ['title', title], ['brandmark', mark]] as const) {
				expect(b.width, `the ${what} has no width`).toBeGreaterThan(0);
				expect(b.height, `the ${what} has no height`).toBeGreaterThan(0);
			}

			// NOTHING ESCAPES THE PLATE. `.card` clips overflow, so an element that
			// has run off the edge is simply not visible in the render — and the
			// share card would ship with a title cut in half.
			for (const [what, b] of [['byline', byline], ['title', title], ['brandmark', mark]] as const) {
				expect(b.x, `the ${what} starts off the left edge`).toBeGreaterThanOrEqual(plate.x - 1);
				expect(b.y, `the ${what} starts above the top edge`).toBeGreaterThanOrEqual(plate.y - 1);
				expect(b.x + b.width, `the ${what} runs off the right edge`)
					.toBeLessThanOrEqual(plate.x + plate.width + 1);
				expect(b.y + b.height, `the ${what} runs off the bottom edge`)
					.toBeLessThanOrEqual(plate.y + plate.height + 1);
			}

			// THE TITLE IS INSET FROM THE EDGE. THIS is the one that catches the
			// deleted `.cover-type` block — checked by deleting it again, which
			// fails four of these five tests here and nowhere above. The block
			// carries the padding, so without it the words run to the edge and
			// through the frame the cover draws at `--frame-inset`.
			expect(title.x, 'the title is flush against the left edge')
				.toBeGreaterThan(plate.x + 1);
			expect(title.x + title.width, 'the title is flush against the right edge')
				.toBeLessThan(plate.x + plate.width - 1);
		});
	}

	test('a plate leaves room for the emblem and a painting does not', async ({ page: p }) => {
		// The one composition difference between the two grounds, and it moves
		// every painted cover's title if it goes wrong. Asserted on the rendered
		// box rather than the markup, which `coverMarkupParity.test.ts` covers.
		await p.setViewportSize({ width: W, height: H });

		await p.setContent(page({ ...BOOKS[0][1], art: false }));
		const band = await box(p, '.emblem-band');
		expect(band.height, 'the emblem band has no height on a plate').toBeGreaterThan(0);

		await p.setContent(page({ ...BOOKS[0][1], art: true }));
		await expect(
			p.locator('.emblem-band'),
			'a painting drew an emblem band — its title now sits too high'
		).toHaveCount(0);
	});
});
