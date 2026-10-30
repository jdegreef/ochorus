import { closeSync, openSync, readdirSync, readSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Every edition's `library.book` row in the shipped fixture, read once.
 *
 * A work's file is its book row followed by every chapter, and the chapters
 * are nearly all of it: the corpus is ~300 MB. Parsing all of it to read one
 * row per file took ~1.5 s alone, and a test file that did it three times ran
 * past vitest's 5 s timeout whenever the full suite had other files parsing
 * the same corpus alongside it — a flake that looked order-dependent and was
 * only load. So this parses the book row alone (cut off at the first chapter)
 * and memoises the result. It also reads only as far as that cut: reading
 * every file whole was still ~740 MB of I/O, enough to time the first caller
 * out on a busy runner.
 *
 * Not in `src/lib`: see `coverCss.ts` for why test-only readers live here.
 */
export type BookFields = {
	slug: string;
	title: string;
	language: string;
	author: string[];
	cover_url?: string;
	series?: string[] | null;
	series_position?: number | null;
	is_published?: boolean;
};

const BOOKS = join(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content', 'books');

// An unescaped `"model"` key can only be JSON structure, never text inside a
// string, so the first match is where the book row's array element ends.
const FIRST_CHAPTER = /,\s*\{\s*"model":\s*"library\.chapter"/;

type Row = { model: string; fields: BookFields };

const CHUNK = 64 * 1024;

/** The start of a file, read a chunk at a time until the first chapter (or the end). */
function head(path: string): { text: string; cut: RegExpExecArray | null } {
	const fd = openSync(path, 'r');
	try {
		const parts: Buffer[] = [];
		const buf = Buffer.alloc(CHUNK);
		for (;;) {
			const n = readSync(fd, buf, 0, CHUNK, null);
			if (n === 0) return { text: Buffer.concat(parts).toString('utf8'), cut: null };
			parts.push(Buffer.from(buf.subarray(0, n)));
			// Decoded whole each time, so a character split across chunks is whole
			// again before the cut is looked for.
			const text = Buffer.concat(parts).toString('utf8');
			const cut = FIRST_CHAPTER.exec(text);
			if (cut) return { text, cut };
		}
	} finally {
		closeSync(fd);
	}
}

function bookRow(file: string): BookFields | undefined {
	const { text, cut } = head(join(BOOKS, file));
	const rows: Row[] = JSON.parse(cut ? `${text.slice(0, cut.index)}]` : text);
	return rows.find((r) => r.model === 'library.book')?.fields;
}

let cache: BookFields[] | undefined;

export function allBookRows(): BookFields[] {
	cache ??= readdirSync(BOOKS)
		.filter((f) => f.endsWith('.json'))
		.map(bookRow)
		.filter((b): b is BookFields => b !== undefined);
	return cache;
}
