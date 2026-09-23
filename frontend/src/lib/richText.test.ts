import { describe, expect, it } from 'vitest';
import { applyFormat, hasFormatting, parseInline, parseRichText } from './richText';

describe('parseInline', () => {
	it('reads bold, italic and both', () => {
		expect(parseInline('Be **still** and *know*')).toEqual([
			{ text: 'Be ' },
			{ text: 'still', bold: true },
			{ text: ' and ' },
			{ text: 'know', italic: true }
		]);
		expect(parseInline('***all of it***')).toEqual([{ text: 'all of it', bold: true, italic: true }]);
		expect(parseInline('_grace_ alone')).toEqual([{ text: 'grace', italic: true }, { text: ' alone' }]);
	});

	it('leaves arithmetic, snake_case and lone markers alone', () => {
		expect(parseInline('2 * 3 * 4')).toEqual([{ text: '2 * 3 * 4' }]);
		expect(parseInline('snake_case_name')).toEqual([{ text: 'snake_case_name' }]);
		expect(parseInline('a ** b')).toEqual([{ text: 'a ** b' }]);
	});
});

describe('parseRichText', () => {
	it('keeps a plain entry as one paragraph of its lines', () => {
		expect(parseRichText('One line\nand another')).toEqual([
			{ type: 'p', lines: [[{ text: 'One line' }], [{ text: 'and another' }]] }
		]);
		expect(hasFormatting('Just words.\nMore words.')).toBe(false);
	});

	it('reads lists, numbered lists and quotations, split by blank lines', () => {
		const blocks = parseRichText(
			'Things to thank Him for:\n- rest\n- *Anna*\n\n1. first\n2. second\n\n> Be still\n> and know\nAmen'
		);
		expect(blocks.map((b) => b.type)).toEqual(['p', 'ul', 'ol', 'quote', 'p']);
		expect(blocks[1]).toEqual({ type: 'ul', items: [[{ text: 'rest' }], [{ text: 'Anna', italic: true }]] });
		expect(blocks[2]).toMatchObject({ type: 'ol', start: 1 });
		expect(blocks[3]).toEqual({ type: 'quote', lines: [[{ text: 'Be still' }], [{ text: 'and know' }]] });
		expect(hasFormatting('- a list')).toBe(true);
	});

	it('keeps separate paragraphs apart', () => {
		expect(parseRichText('First.\n\nSecond.').map((b) => b.type)).toEqual(['p', 'p']);
	});
});

describe('applyFormat', () => {
	it('wraps a selection in bold, and unwraps it again', () => {
		const on = applyFormat('Be still', 3, 8, 'bold');
		expect(on).toEqual({ text: 'Be **still**', start: 5, end: 10 });
		expect(applyFormat(on.text, on.start, on.end, 'bold')).toEqual({ text: 'Be still', start: 3, end: 8 });
	});

	it('marks every selected line as a list item, and takes the marks off', () => {
		const text = 'rest\nfood\nAnna';
		const on = applyFormat(text, 0, text.length, 'list');
		expect(on.text).toBe('- rest\n- food\n- Anna');
		expect(applyFormat(on.text, on.start, on.end, 'list').text).toBe(text);
	});

	it('quotes the line the cursor is on', () => {
		expect(applyFormat('first\nBe still\nlast', 8, 8, 'quote').text).toBe('first\n> Be still\nlast');
	});
});
