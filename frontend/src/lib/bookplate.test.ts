import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { COVER_STYLE_IDS } from './coverStyles';
import type { BookSummary } from './library-public';
import {
	PLATE_FACES,
	SANS_SCRIPT_FACE,
	SCRIPT_SHEET,
	finishedPlates,
	isRtl,
	plateDate,
	plateFilename,
	plateFontStack,
	plateName,
	plateStyle,
	plateWords,
	splitAround,
	textScripts
} from './bookplate';

// Midday UTC, so no test time zone moves it to another day.
const NOV_11 = Date.UTC(2026, 10, 11, 12);

describe('plateName — who the plate is made out to', () => {
	it('is the display name, whitespace tidied', () => {
		expect(plateName('  Mary   Okonkwo ')).toBe('Mary Okonkwo');
	});
	it('is null with no name — never a guess from the email', () => {
		expect(plateName('')).toBeNull();
		expect(plateName('   ')).toBeNull();
		expect(plateName(null)).toBeNull();
		expect(plateName(undefined)).toBeNull();
	});
	it('keeps a name in any script as written', () => {
		expect(plateName('مريم')).toBe('مريم');
		expect(plateName('김민지')).toBe('김민지');
	});
});

describe('plateDate — the day written out in the reader’s locale', () => {
	it('writes the month as a word', () => {
		expect(plateDate(NOV_11, 'en')).toBe('November 11, 2026');
		expect(plateDate(NOV_11, 'en-GB')).toBe('11 November 2026');
		expect(plateDate(NOV_11, 'es')).toBe('11 de noviembre de 2026');
		expect(plateDate(NOV_11, 'pt')).toBe('11 de novembro de 2026');
		expect(plateDate(NOV_11, 'fr')).toBe('11 novembre 2026');
		expect(plateDate(NOV_11, 'ja')).toBe('2026年11月11日');
		expect(plateDate(NOV_11, 'uk')).toBe('11 листопада 2026 р.');
	});
	it('falls back to English for a locale tag that cannot be parsed', () => {
		expect(plateDate(NOV_11, 'not a locale!')).toBe('November 11, 2026');
	});
});

describe('plateStyle — the cover face the plate is lettered in', () => {
	it('follows the author’s era', () => {
		expect(plateStyle({ slug: 'someone-puritan', birth_year: 1628 }, 'x')).toBe('press');
		expect(plateStyle({ slug: 'someone-victorian', birth_year: 1834 }, 'x')).toBe('revival');
		expect(plateStyle({ slug: 'someone-father', birth_year: 354 }, 'x')).toBe('inscriptional');
		expect(plateStyle({ slug: 'someone-new', birth_year: null }, 'x')).toBe('house');
	});
	it('takes an author’s own recipe over their era', () => {
		expect(plateStyle({ slug: 'thomas-a-kempis', birth_year: 1380 }, 'x')).toBe('devotional');
	});
	it('has a canvas face for every recipe, the same face app.css leads its token with', () => {
		const css = readFileSync(resolve(__dirname, '../app.css'), 'utf8');
		for (const id of COVER_STYLE_IDS) {
			const token = new RegExp(`--cover-face-${id}:\\s*'([^']+)'`).exec(css);
			expect(token, id).not.toBeNull();
			expect(PLATE_FACES[id].family, id).toBe(token![1]);
			expect(plateFontStack(id).startsWith(`'${token![1]}', `)).toBe(true);
		}
	});
	it('falls back through faces for every script, ending on a generic', () => {
		for (const face of ['Amiri', 'Tiro Devanagari Hindi', 'PT Serif', 'Noto Serif Ethiopic', 'Noto Serif KR', 'Noto Serif JP'])
			expect(plateFontStack('press')).toContain(`'${face}'`);
		expect(plateFontStack('press').endsWith('serif')).toBe(true);
		expect(plateFontStack('young').endsWith('sans-serif')).toBe(true);
	});
});

describe('scripts and direction', () => {
	it('finds the scripts a name or title needs a face for', () => {
		expect(textScripts('Mary Okonkwo')).toEqual([]);
		expect(textScripts('مريم · All of Grace')).toEqual(['arabic']);
		expect(textScripts('Олена')).toEqual(['cyrillic']);
		expect(textScripts('ማርያም')).toEqual(['ethiopic']);
		expect(textScripts('김민지')).toEqual(['korean']);
		expect(textScripts('山田はなこ')).toEqual(['japanese']);
		expect(textScripts('प्रिया')).toEqual(['devanagari']);
	});
	it('reads RTL from the first strong letter', () => {
		expect(isRtl('مريم أحمد')).toBe(true);
		expect(isRtl('“مريم”')).toBe(true);
		expect(isRtl('Mary مريم')).toBe(false);
		expect(isRtl('2026')).toBe(false);
	});
});

describe('splitAround', () => {
	it('splits a template around its placeholder, in the catalogue’s order', () => {
		expect(splitAround('finished %title%', '%title%')).toEqual(['finished', '']);
		expect(splitAround('読了：%title%', '%title%')).toEqual(['読了：', '']);
		expect(splitAround('%title% を読了', '%title%')).toEqual(['', 'を読了']);
		expect(splitAround('no token', '%title%')).toEqual(['no token', '']);
	});
});

describe('plateWords — one reading of the catalogue for the page and the PNG', () => {
	const catalogue = (finished: string, by: string) => (key: string) =>
		key === 'bookplate.finished' ? finished : key === 'bookplate.by' ? by : key;
	it('puts the words around the title and the author in the byline', () => {
		expect(plateWords(catalogue('finished %title%', 'by %author%'), 'John Bunyan')).toEqual({
			before: 'finished',
			after: '',
			byline: 'by John Bunyan'
		});
	});
	it('keeps the catalogue’s word order', () => {
		expect(plateWords(catalogue('%title% を読了', '%author% 著'), 'バニヤン')).toEqual({
			before: '',
			after: 'を読了',
			byline: 'バニヤン 著'
		});
	});
});

describe('the young-reader plate’s sans faces', () => {
	it('names every script’s sans face in its stack, so the PNG loads what it draws', () => {
		for (const face of Object.values(SANS_SCRIPT_FACE)) expect(plateFontStack('young')).toContain(`'${face}'`);
		expect(Object.keys(SANS_SCRIPT_FACE).sort()).toEqual(Object.keys(SCRIPT_SHEET).sort());
	});
});

const book = (slug: string, title = slug): BookSummary =>
	({ slug, title, language: 'en', author: { slug: 'a', name: 'A', birth_year: 1834 } }) as unknown as BookSummary;
const row = (slug: string, finished_at: number | null, kind: 'book' | 'sermon' = 'book') => ({
	slug,
	kind,
	order: 1,
	paragraph_index: 0,
	language: 'en',
	at: 1,
	finished_at,
	furthest: 1
});

describe('finishedPlates — the Bookshelf’s collection', () => {
	it('is one plate per finished book, newest first', () => {
		const plates = finishedPlates(
			[row('old', 100), row('reading', null), row('new', 300), row('mid', 200)],
			[book('old'), book('reading'), book('new'), book('mid')]
		);
		expect(plates.map((p) => [p.book.slug, p.at])).toEqual([
			['new', 300],
			['mid', 200],
			['old', 100]
		]);
	});
	it('leaves out sermons and books with no row in this language', () => {
		const plates = finishedPlates([row('s', 5, 'sermon'), row('elsewhere', 6), row('here', 7)], [book('s'), book('here')]);
		expect(plates.map((p) => p.book.slug)).toEqual(['here']);
	});
	it('is empty when nothing is finished', () => {
		expect(finishedPlates([], [book('x')])).toEqual([]);
	});
	it('names the saved file after the book', () => {
		expect(plateFilename('all-of-grace')).toBe('ochorus-bookplate-all-of-grace.png');
	});
});
