/**
 * The cover's type, as markup, for the renderer that cannot mount a component.
 *
 * TWO RENDERERS DRAW ONE COVER. `BookCover.svelte` draws it in the browser from
 * its own template; `scripts/generate-cover-og.mjs` draws it into a share card
 * with `page.setContent`, and there is no way to mount Svelte inside that. So
 * the og script hand-built the same tree — and nothing held the two copies
 * together, which is exactly how they drifted. At the point this module was
 * written the card was missing all of:
 *
 *   * the `script-<x>` class, so an Arabic, Hindi or Ukrainian card would take
 *     the Latin face — the one thing `coverStyles.scriptOf` exists to prevent;
 *   * `dir="auto"` on the title and subtitle, so an Arabic card would be laid
 *     out left-to-right with its punctuation on the wrong end;
 *   * `lang`, which is what lets a browser shape and hyphenate those words.
 *
 * None of that showed, because twins are only built for English books today.
 * All three were waiting for the first translated card.
 *
 * The markup now lives here, once. `BookCover` still owns its own template —
 * a Svelte component cannot render from a string without `{@html}`, which this
 * repo reserves for server-sanitized prose — so this is not the single source
 * in the sense of one emitter. It is the single source in the sense that
 * `coverMarkupParity.test.ts` renders the component and parses this, and fails
 * when the trees stop matching. That gate is the reason this file is worth
 * having; the module alone would just be a third copy.
 *
 * NO IMPORTS, deliberately: the og script is a plain `.mjs` that Node resolves
 * with no bundler, and `nodeLoadable.test.ts` polices the same rule for
 * `coverStyles.ts` next door.
 */

/** What a card needs to know about a book. Not `BookSummary`: the og script
 *  reads the fixture, not the API, and shares no types with it. */
export interface CoverCardBook {
	/** The author's name, as one row serves every edition. */
	author: string;
	title: string;
	subtitle?: string | null;
	/** A `coverStyles` id — `devotional`, `press`, … */
	style: string;
	/** The series volume numeral, from `coverStyles.volumeNumeral`; null
	 *  outside a series. */
	volume?: string | null;
	/** A `coverStyles` script suffix, or null for Latin. */
	script?: string | null;
	/** The edition's language tag, for shaping. */
	lang: string;
	/** Is the ground a painting? A painting has no emblem beneath it to leave
	 *  room for; a plate does. */
	art: boolean;
	/** How far to scale the scrim over this painting, from `coverScrim`. Only a
	 *  painting has a scrim to scale, so a plate leaves it undefined. */
	scrim?: number | null;
	/** The layout a painting is composed in, from `coverLayouts.coverLayoutFor`;
	 *  null or absent for the framed composition. Ignored on a plate. */
	layout?: { layout: string; hue: string } | null;
	/** Framed type set from the top, from `coverLayouts.typeTopFor`. Painting only. */
	top?: boolean;
}

/**
 * Past this many characters a title steps down a size (`.long-title`).
 *
 * Every recipe sets its title at one size, tuned so the library's titles fit in
 * three lines. A longer one ran to four, and the `.middle` block — centred
 * between the byline and the mark by auto margins — grew up over the byline
 * and clipped it. Counted in characters rather than measured because both
 * renderers must decide it identically without a layout pass: the share-card
 * script builds its markup as a string.
 */
export const LONG_TITLE_CHARS = 48;

export function isLongTitle(title: string): boolean {
	return title.length > LONG_TITLE_CHARS;
}

/** Escape text for an HTML attribute or a text node. */
export function escapeHtml(value: string): string {
	return value
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}

/**
 * The `.cover-type` subtree — everything `BookCover`'s `plateType` snippet
 * draws, in the same order, with the attributes that change how it RENDERS.
 *
 * `lockup` is the brand SVG as a string. It is a parameter rather than an
 * import because the two callers get it from different places: the component
 * through Vite's `?raw`, the script through `readFileSync`.
 */
export function coverTypeMarkup(book: CoverCardBook, lockup: string): string {
	// `script` IS the class suffix, so it is used as one rather than compared
	// against three times — the same reasoning as the component's template, and
	// the same reason a Latin cover emits no script class at all.
	// Escaped like everything else here. Both come from closed tables today
	// (`COVER_STYLE_IDS`, `COVER_SCRIPTS`) so nothing can currently carry a
	// quote — but they are typed `string`, they are interpolated into an
	// attribute, and the two lines below escape their inputs. One of these
	// being the exception is how the exception stops being noticed.
	const classes = ['cover-type', `style-${escapeHtml(book.style)}`];
	if (book.script) classes.push(`script-${escapeHtml(book.script)}`);
	if (isLongTitle(book.title)) classes.push('long-title');
	if (book.art && book.top) classes.push('type-top');
	const lang = escapeHtml(book.lang);
	// The byline takes NO `lang`, matching the component: an author's name is
	// one row for every edition, so it is Latin on an Arabic cover too, and
	// claiming otherwise would tell a screen reader to pronounce "Andrew Murray"
	// as Arabic.
	// Right-to-left for an Arabic edition, matching the component: the title
	// sets its own direction (`dir="auto"`), but the byline is a Latin name and
	// the rule has no text, so without this a layout that ranges its type to the
	// start edge put the title on the right and everything under it on the left.
	const dir = book.script === 'arabic' ? ' dir="rtl"' : '';
	return `<div class="${classes.join(' ')}"${dir}>
	<div class="byline" dir="auto">${escapeHtml(book.author)}</div>
	<div class="middle">
		${book.volume ? `<div class="volume" lang="${lang}">${escapeHtml(book.volume)}</div>` : ''}
		<div class="title" lang="${lang}" dir="auto">${escapeHtml(book.title)}</div>
		<div class="rule"></div>
		${
			book.subtitle
				? `<div class="subtitle" lang="${lang}" dir="auto">${escapeHtml(book.subtitle)}</div>`
				: ''
		}
	</div>
	${book.art ? '' : '<div class="emblem-band" aria-hidden="true"></div>'}
	<span class="brandmark" style="--h: 13.7cqw" role="img" aria-label="Ochorus">${lockup}</span>
</div>`;
}

/**
 * The plate the type sits in — `BookCover`'s `overFile` branch.
 *
 * Included here because it was the last hand-built piece, and it carries a
 * class that decides pixels: `.over-art` is what puts the four-stop scrim under
 * white type on a painting. Left outside, a renamed or added class on that
 * wrapper would leave every painted card wearing the old scrim with the parity
 * gate green, since the gate started one element lower down.
 *
 * `role="img"` and `aria-label` are the component's and are deliberately NOT
 * here: a card is a raster with no accessibility tree, the label it would carry
 * is the alt text of the `<img>` that embeds the finished PNG, and putting one
 * here would be inventing a difference for the gate to ignore.
 */
export function coverPlateMarkup(book: CoverCardBook, lockup: string): string {
	const classes = ['cover-plate', 'over-file'];
	if (book.art) classes.push('over-art');
	// The subtitle's own scrim band, which only exists on covers that draw one.
	// On the wrapper rather than the type block because the scrim is drawn by
	// `.cover-plate.over-art::before`, and a pseudo-element cannot be selected
	// from a descendant.
	if (book.subtitle) classes.push('has-subtitle');
	// A layout repaints the plate — paper, band, the ink — so it is a class here,
	// where the scrim it replaces is drawn, and not on the type block below.
	if (book.art && book.layout) {
		classes.push(
			'has-layout',
			`cover-layout-${escapeHtml(book.layout.layout)}`,
			`cover-hue-${escapeHtml(book.layout.hue)}`
		);
	}
	// Matching the component: the property is set only where there is a scrim to
	// scale, so a plate's markup is unchanged and the parity gate compares like
	// with like. A painting without a measured strength takes 1, which is what
	// every painting carried before the table existed.
	const style =
		book.art && book.scrim != null ? ` style="--scrim-strength: ${Number(book.scrim)}"` : '';
	return `<div class="${classes.join(' ')}"${style}>${coverTypeMarkup(book, lockup)}</div>`;
}
