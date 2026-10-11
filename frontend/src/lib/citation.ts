/**
 * Formal citations for a book or sermon on Ochorus — what a student or a
 * preacher pastes into a paper or a footnote: MLA, Chicago (bibliography and
 * footnote, the form Turabian follows) and BibTeX. Pure, so each style is
 * tested apart from the page.
 *
 * Each style comes as plain text and as HTML: the title is italic in a
 * bibliography, and a word processor keeps that only from `text/html`.
 * Citation styles are English conventions ("repr.", "Sermon"), so the words
 * are literals, not catalogue keys; the work's own title and URL are the
 * edition the reader is on.
 */
import { filingName } from './authorIndex';
import { escapeHtml } from './highlight';

/** What is being cited. */
export interface Citable {
	kind: 'book' | 'sermon';
	author: string;
	/** A body, not a person (the house imprint): its name is never inverted. */
	corporate?: boolean;
	title: string;
	/** First published (a book) or preached (a sermon), when known — and only
	 *  for the text as written: a translated edition did not appear that year. */
	year: number | null;
	/** The page's canonical URL. */
	url: string;
}

export type CitationStyle = 'mla' | 'chicago' | 'chicagoNote' | 'bibtex';

export const CITATION_STYLES: { style: CitationStyle; label: string }[] = [
	{ style: 'mla', label: 'MLA' },
	{ style: 'chicago', label: 'Chicago' },
	{ style: 'chicagoNote', label: 'Chicago footnote' },
	{ style: 'bibtex', label: 'BibTeX' }
];

/** A run of a citation: plain text, or the work's title (italic in a
 *  bibliography, quoted for a sermon). The page isolates a title's run, which
 *  may be in a script that runs the other way. */
export type CitationPart = string | { title: string; italic: boolean };

export interface Citation {
	text: string;
	html: string;
	parts: CitationPart[];
}

/** Titles a bibliography leaves unprefixed: "Brother Lawrence", "Saint …". */
const TITLED = /^(brother|sister|saint|st\.|pope|mother|father)\s/i;

/** The bibliography's surname-first form — the A–Z index's filing name, so
 *  the two agree ("ten Boom, Corrie") — or the name as written for a body or
 *  a titled name. */
export const citedName = (c: Pick<Citable, 'author' | 'corporate'>): string =>
	c.corporate || TITLED.test(c.author) ? c.author.trim() : filingName(c.author);

/** A sentence's closing full stop, unless the text already ends in one. */
const stop = (s: string) => (/[.?!]$/.test(s) ? '' : '.');

function both(parts: CitationPart[]): Citation {
	const text = parts.map((p) => (typeof p === 'string' ? p : p.title)).join('');
	const html = parts
		.map((p) => (typeof p === 'string' ? escapeHtml(p) : p.italic ? `<i>${escapeHtml(p.title)}</i>` : escapeHtml(p.title)))
		.join('');
	return { text, html, parts };
}

/** Lowercase ASCII letters and digits only: a key any BibTeX can read. */
const ascii = (s: string) =>
	s
		.normalize('NFKD')
		.toLowerCase()
		.replace(/[^a-z0-9\s-]/g, '')
		.split(/[\s-]+/)
		.filter(Boolean);

/** BibTeX's citation key: the surname, the year and the title's first long
 *  word, e.g. `spurgeon1886grace`. */
function bibKey(c: Citable): string {
	const surname = ascii(citedName(c).split(',')[0]).join('');
	const word = ascii(c.title).find((w) => w.length > 3) ?? '';
	return `${surname || 'ochorus'}${c.year ?? ''}${word}`;
}

/** A BibTeX value: LaTeX's specials escaped, braces dropped. `exact` doubles
 *  the braces, so a style keeps the title's capitals (and a body's name
 *  whole) instead of lowercasing or splitting it. */
const bib = (s: string, exact = false) => {
	const v = s.replace(/[{}\\]/g, '').replace(/([&%#_$])/g, '\\$1');
	return exact ? `{{${v}}}` : `{${v}}`;
};

/** `c` in one style. */
export function cite(c: Citable, style: CitationStyle): Citation {
	const name = citedName(c);
	const lead = `${name}${stop(name)} `;
	const year = c.year ? String(c.year) : '';
	const t = c.title;
	const italic = { title: t, italic: true };
	if (c.kind === 'sermon') {
		const quoted = (after: string) => ['“', { title: t, italic: false }, `${after}”`];
		switch (style) {
			case 'mla':
				return both([lead, ...quoted(stop(t)), ` Sermon${year ? `, ${year}` : ''}. `, { title: 'Ochorus', italic: true }, `, ${c.url}.`]);
			case 'chicago':
				return both([lead, ...quoted(stop(t)), ` Sermon${year ? `, ${year}` : ''}. Ochorus. ${c.url}.`]);
			case 'chicagoNote':
				return both([`${c.author}, `, ...quoted(/[?!]$/.test(t) ? '' : ','), ` sermon${year ? `, ${year}` : ''}, Ochorus, ${c.url}.`]);
			case 'bibtex':
				return both([bibtex('misc', c, { howpublished: bib(`Sermon${year ? `, ${year}` : ''}`), publisher: bib('Ochorus') })]);
		}
	}
	switch (style) {
		case 'mla':
			return both([lead, italic, `${stop(t)} ${year ? `${year}. ` : ''}Ochorus, ${c.url}.`]);
		case 'chicago':
			return both([lead, italic, `${stop(t)} ${year ? `${year}. Reprint, ` : ''}Ochorus. ${c.url}.`]);
		case 'chicagoNote':
			return both([`${c.author}, `, italic, ` (${year ? `${year}; repr., ` : ''}Ochorus), ${c.url}.`]);
		case 'bibtex':
			return both([bibtex('book', c, { publisher: bib('Ochorus') })]);
	}
}

function bibtex(type: string, c: Citable, extra: Record<string, string>): string {
	const fields: Record<string, string> = {
		author: bib(citedName(c), c.corporate),
		title: bib(c.title, true),
		...(c.year ? { year: bib(String(c.year)) } : {}),
		...extra,
		url: `{${c.url}}`
	};
	const body = Object.entries(fields)
		.map(([k, v]) => `  ${k} = ${v}`)
		.join(',\n');
	return `@${type}{${bibKey(c)},\n${body}\n}`;
}
