import { browser } from '$app/environment';
import type { ReaderFont } from './readerPrefs.svelte';
import type { SiteFont } from './siteFont.svelte';
import amFonts from './fonts-am.css?url';
import arFonts from './fonts-ar.css?url';
import hiFonts from './fonts-hi.css?url';
import koFonts from './fonts-ko.css?url';
import ukFonts from './fonts-uk.css?url';
import readerFonts from './fonts-reader.css?url';

/**
 * The font stylesheets app.css does NOT carry, and who links them (app.css's
 * header says why: it is render-blocking on every page, and an @font-face
 * costs CSS bytes whether or not its font is ever drawn).
 *
 * A script's faces, by locale: the root layout links the document's own in
 * <svelte:head>, so a prerendered Arabic page has Amiri before first paint, as
 * it did when app.css carried it. The Latin locales need none.
 */
export const SCRIPT_FONTS: Readonly<Record<string, string>> = {
	ar: arFonts,
	hi: hiFonts,
	uk: ukFonts,
	am: amFonts,
	ko: koFonts
};

/** The reader's optional faces (fonts-reader.css). */
export const READER_FONTS_SHEET = readerFonts;

/** Reader faces whose files live in fonts-reader.css. The others are the house
 *  tokens or a face app.css declares for its own reasons (Atkinson is also a
 *  site style). fontStacks.test.ts holds this list to the two files. */
export const READER_SHEET_FONTS: readonly ReaderFont[] = [
	'literata',
	'garamond',
	'sourceSerif',
	'lora',
	'baskerville',
	'merriweather',
	'dyslexic'
];

/** Does this choice need fonts-reader.css? "classic" sets headings in EB
 *  Garamond, whose upright app.css has (a cover face) and whose italic is here. */
export const needsReaderSheet = (font: ReaderFont, site: SiteFont) =>
	READER_SHEET_FONTS.includes(font) || site === 'classic';

/**
 * Link a stylesheet into <head>, once. Client-only and never removed: a sheet
 * of @font-face rules does nothing until a glyph asks for one, so leaving it
 * after the choice changes costs nothing, and re-adding it would refetch. A
 * <link> the layout server-rendered counts as already linked.
 */
export function linkSheet(href: string): void {
	if (!browser) return;
	for (const l of document.head.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')) {
		if (l.getAttribute('href') === href) return;
	}
	const link = document.createElement('link');
	link.rel = 'stylesheet';
	link.href = href;
	document.head.append(link);
}

/** Link a content language's script faces when it has its own sheet — for a
 *  page that draws covers in other scripts than its own (/for's languages
 *  band). A Latin language is a no-op. */
export function linkScriptFonts(language: string): void {
	const href = SCRIPT_FONTS[language];
	if (href) linkSheet(href);
}
