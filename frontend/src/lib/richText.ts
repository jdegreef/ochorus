/**
 * The little formatting a Notebook entry can carry — **bold**, *italic*,
 * "- " lists, "1. " numbered lists and "> " quotations — read from the plain
 * text the entry is stored as.
 *
 * Stored as text, not HTML, on purpose: it syncs, searches, prints and exports
 * as it is (the Markdown export gets real formatting for free), and it is
 * rendered by building text nodes from this structure (RichText.svelte) —
 * never with {@html} — so nothing a reader types can become markup.
 */

/** A run of text with its emphasis. */
export interface Span {
	text: string;
	bold?: boolean;
	italic?: boolean;
}

/** One line: its spans. */
export type Line = Span[];

export type Block =
	| { type: 'p'; lines: Line[] }
	| { type: 'ul'; items: Line[] }
	| { type: 'ol'; items: Line[]; start: number }
	| { type: 'quote'; lines: Line[] };

const UL = /^\s*[-*•]\s+(.*)$/;
const OL = /^\s*(\d{1,3})[.)]\s+(.*)$/;
const QUOTE = /^\s*>\s?(.*)$/;

/**
 * Emphasis within a line: **bold**, *italic* or _italic_ (and ***both***).
 * A marker only counts when it opens and closes on the same line and hugs its
 * text ("2 * 3 * 4" and "snake_case_name" stay as they are).
 */
export function parseInline(line: string): Line {
	const out: Line = [];
	const re = /(\*\*\*|\*\*|\*|_)(?=\S)(.+?)(?<=\S)\1(?![\p{L}\p{N}])/gu;
	let last = 0;
	for (const m of line.matchAll(re)) {
		const at = m.index ?? 0;
		// `_` inside a word ("snake_case") is not emphasis.
		if (m[1] === '_' && at > 0 && /[\p{L}\p{N}]/u.test(line[at - 1])) continue;
		if (at > last) out.push({ text: line.slice(last, at) });
		const marker = m[1];
		out.push({
			text: m[2],
			...(marker === '**' || marker === '***' ? { bold: true } : {}),
			...(marker === '*' || marker === '_' || marker === '***' ? { italic: true } : {})
		});
		last = at + m[0].length;
	}
	if (last < line.length) out.push({ text: line.slice(last) });
	return out.length ? out : [{ text: '' }];
}

/** An entry's text as blocks: paragraphs, lists and quotations. */
export function parseRichText(text: string): Block[] {
	const blocks: Block[] = [];
	const push = (type: Block['type'], line: string, start = 1) => {
		const last = blocks[blocks.length - 1];
		const spans = parseInline(line);
		if (type === 'p' || type === 'quote') {
			if (last && last.type === type) last.lines.push(spans);
			else blocks.push({ type, lines: [spans] });
		} else if (type === 'ul') {
			if (last && last.type === 'ul') last.items.push(spans);
			else blocks.push({ type: 'ul', items: [spans] });
		} else {
			if (last && last.type === 'ol') last.items.push(spans);
			else blocks.push({ type: 'ol', items: [spans], start });
		}
	};
	let blank = false;
	for (const raw of text.replace(/\r\n?/g, '\n').split('\n')) {
		if (!raw.trim()) {
			// A blank line ends a paragraph, list or quotation.
			blank = true;
			continue;
		}
		if (blank && blocks.length) blocks.push({ type: 'p', lines: [] });
		blank = false;
		let m: RegExpMatchArray | null;
		if ((m = raw.match(UL))) push('ul', m[1]);
		else if ((m = raw.match(OL))) push('ol', m[2], Number(m[1]));
		else if ((m = raw.match(QUOTE))) push('quote', m[1]);
		else push('p', raw);
	}
	// The empty paragraphs above are block breaks; drop them.
	return blocks.filter((b) => !(b.type === 'p' && b.lines.length === 0));
}

/** Whether a text uses any of the formatting (a plain entry renders as before). */
export function hasFormatting(text: string): boolean {
	return parseRichText(text).some(
		(b) =>
			b.type !== 'p' ||
			b.lines.some((l) => l.some((s) => s.bold || s.italic))
	);
}

/**
 * The composer's toolbar, as a pure edit of the textarea: wrap the selection
 * in a marker ("**", "*"), or put a line marker ("- ", "> ") in front of every
 * selected line — or take it off again when they all have it. Returns the new
 * text and selection.
 */
export function applyFormat(
	text: string,
	start: number,
	end: number,
	format: 'bold' | 'italic' | 'list' | 'quote'
): { text: string; start: number; end: number } {
	if (format === 'bold' || format === 'italic') {
		const mark = format === 'bold' ? '**' : '*';
		const selected = text.slice(start, end);
		const before = text.slice(start - mark.length, start);
		const after = text.slice(end, end + mark.length);
		if (before === mark && after === mark) {
			// Already wrapped: unwrap.
			return {
				text: text.slice(0, start - mark.length) + selected + text.slice(end + mark.length),
				start: start - mark.length,
				end: end - mark.length
			};
		}
		return {
			text: text.slice(0, start) + mark + selected + mark + text.slice(end),
			start: start + mark.length,
			end: end + mark.length
		};
	}
	const prefix = format === 'list' ? '- ' : '> ';
	const lineStart = text.lastIndexOf('\n', start - 1) + 1;
	const nl = text.indexOf('\n', Math.max(end - (end > start && text[end - 1] === '\n' ? 1 : 0), start));
	const lineEnd = nl === -1 ? text.length : nl;
	const lines = text.slice(lineStart, lineEnd).split('\n');
	const all = lines.every((l) => l.startsWith(prefix));
	const changed = lines.map((l) => (all ? l.slice(prefix.length) : l.startsWith(prefix) ? l : prefix + l));
	const replaced = changed.join('\n');
	return {
		text: text.slice(0, lineStart) + replaced + text.slice(lineEnd),
		start: lineStart,
		end: lineStart + replaced.length
	};
}
