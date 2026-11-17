import { describe, expect, it } from 'vitest';
import { aiReferral, assistantFor, pageKind } from './aiReferral';

const at = (path: string) => new URL(`https://ochorus.com${path}`);

describe('assistantFor', () => {
	it('names the assistants by their hosts', () => {
		expect(assistantFor('chatgpt.com')).toBe('ChatGPT');
		expect(assistantFor('www.perplexity.ai')).toBe('Perplexity');
		expect(assistantFor('gemini.google.com')).toBe('Gemini');
		expect(assistantFor('copilot.microsoft.com')).toBe('Copilot');
		expect(assistantFor('claude.ai')).toBe('Claude');
	});

	it('leaves search engines and look-alikes alone', () => {
		expect(assistantFor('www.google.com')).toBeNull();
		expect(assistantFor('bing.com')).toBeNull();
		expect(assistantFor('notchatgpt.com')).toBeNull();
		expect(assistantFor('')).toBeNull();
	});
});

describe('aiReferral', () => {
	it('reads the referrer first', () => {
		expect(aiReferral('https://chatgpt.com/', at('/books/humility-2/'))).toBe('ChatGPT');
	});

	it('falls back to the utm_source an assistant stamps on its links', () => {
		expect(aiReferral('', at('/books/humility-2/?utm_source=chatgpt.com'))).toBe('ChatGPT');
		expect(aiReferral('', at('/?utm_source=perplexity.ai'))).toBe('Perplexity');
	});

	it('is null for ordinary visits and a garbled referrer', () => {
		expect(aiReferral('https://www.google.com/', at('/'))).toBeNull();
		expect(aiReferral('not a url', at('/'))).toBeNull();
		expect(aiReferral('', at('/?utm_source=newsletter'))).toBeNull();
	});
});

describe('pageKind', () => {
	it('labels the landing by kind, locale prefix ignored', () => {
		expect(pageKind('/')).toBe('home');
		expect(pageKind('/es/')).toBe('home');
		expect(pageKind('/books/humility-2/')).toBe('book');
		expect(pageKind('/books/humility-2/3/')).toBe('chapter');
		expect(pageKind('/books/humility-2/modern/3/')).toBe('chapter');
		expect(pageKind('/hi/sermons/x/')).toBe('sermon');
		expect(pageKind('/articles/what-is-the-trinity/')).toBe('article');
		expect(pageKind('/settings/')).toBe('other');
	});
});
