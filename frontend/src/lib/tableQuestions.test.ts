import { describe, expect, it } from 'vitest';
import { TABLE_QUESTIONS, tableQuestion } from './tableQuestions';

describe('tableQuestion', () => {
	it('has one question per story, each a question', () => {
		for (const [book, langs] of Object.entries(TABLE_QUESTIONS)) {
			for (const [lang, qs] of Object.entries(langs)) {
				expect(qs, `${book}.${lang}`).toHaveLength(6);
				for (const q of qs) expect(q.trim().endsWith('?'), q).toBe(true);
			}
		}
	});
	it('reads by chapter order, and is null off the list', () => {
		expect(tableQuestion('brave-for-god', 1, 'en')).toMatch(/^Samuel/);
		expect(tableQuestion('brave-for-god', 7, 'en')).toBeNull();
		expect(tableQuestion('brave-for-god', 1, 'xx')).toBeNull();
		expect(tableQuestion('pilgrims-progress', 1, 'en')).toBeNull();
	});
});
