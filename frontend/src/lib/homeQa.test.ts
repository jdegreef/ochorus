import { describe, expect, it } from 'vitest';
import { HOME_QA_KEYS, homeQa, languageList } from './homeQa';
import en from '../../messages/en.json';

const t = (key: string) =>
	(en as Record<string, string>)[
		key
			.replace(/([a-z0-9])([A-Z])/g, '$1_$2')
			.replace(/\./g, '_')
			.toLowerCase()
	] ?? key;

describe('homeQa', () => {
	const qa = homeQa(t, 'en');

	it('answers every question from the catalogue, none left as a raw key', () => {
		expect(qa).toHaveLength(HOME_QA_KEYS.length);
		for (const { q, a } of qa) {
			expect(q).not.toMatch(/^home\./);
			expect(a).not.toMatch(/^home\./);
		}
	});

	it('opens with the one-sentence definition of Ochorus', () => {
		expect(qa[0].q).toBe('What is Ochorus?');
		expect(qa[0].a.startsWith('Ochorus is a free online library')).toBe(true);
	});

	it('fills the languages answer from the advertised locales', () => {
		const lang = qa.find((x) => x.q.includes('languages'))!;
		expect(lang.a).not.toContain('%languages%');
		expect(lang.a).toContain('English');
	});
});

describe('languageList', () => {
	it('joins autonyms in the reader’s list style', () => {
		expect(languageList('en', ['en', 'es', 'sw'])).toBe('English, Español, and Kiswahili');
	});
});
