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
	/** A `coverStyles` script suffix, or null for Latin. */
	script?: string | null;
	/** The edition's language tag, for shaping. */
	lang: string;
	/** Is the ground a painting? A painting has no emblem beneath it to leave
	 *  room for; a plate does. */
	art: boolean;
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
	const classes = ['cover-type', `style-${book.style}`];
	if (book.script) classes.push(`script-${book.script}`);
	const lang = escapeHtml(book.lang);
	// The byline takes NO `lang`, matching the component: an author's name is
	// one row for every edition, so it is Latin on an Arabic cover too, and
	// claiming otherwise would tell a screen reader to pronounce "Andrew Murray"
	// as Arabic.
	return `<div class="${classes.join(' ')}">
	<div class="byline" dir="auto">${escapeHtml(book.author)}</div>
	<div class="middle">
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
