import { readFileSync, readdirSync } from 'node:fs';
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
 * and memoises the result.
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
	is_published?: boolean;
};

const BOOKS = join(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content', 'books');

// An unescaped `"model"` key can only be JSON structure, never text inside a
// string, so the first match is where the book row's array element ends.
const FIRST_CHAPTER = /,\s*\{\s*"model":\s*"library\.chapter"/;

type Row = { model: string; fields: BookFields };

function bookRow(file: string): BookFields | undefined {
	const text = readFileSync(join(BOOKS, file), 'utf8');
	const cut = FIRST_CHAPTER.exec(text);
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
