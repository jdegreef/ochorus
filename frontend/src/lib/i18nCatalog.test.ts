import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import * as m from '$lib/paraglide/messages.js';
import { overwriteGetLocale, getLocale } from '$lib/paraglide/runtime';
import { i18n } from '$lib/i18n.svelte';
import settings from '../../project.inlang/settings.json';

/**
 * `t()` serves the raw locale catalogue (messages/<locale>.json) instead of
 * Paraglide's compiled message functions, so a page loads one language's
 * strings rather than all of them ($lib/i18n). Pin that the swap changed no
 * string a reader sees: every parameter-free message, in every locale, reads
 * exactly as Paraglide renders it.
 */
type MessageFn = (inputs?: object, options?: { locale?: string }) => string;
const compiled = m as unknown as Record<string, MessageFn>;
const en = JSON.parse(readFileSync('messages/en.json', 'utf8')) as Record<string, string>;
const plain = Object.keys(en).filter((k) => k !== '$schema' && !/[{}]/.test(en[k]));

describe('t() and Paraglide agree', () => {
	it.each(settings.locales)('%s', (locale) => {
		const original = getLocale;
		overwriteGetLocale(() => locale as ReturnType<typeof getLocale>);
		try {
			const diffs = plain.filter((k) => i18n.t(k) !== compiled[k]({}, { locale }));
			expect(diffs).toEqual([]);
		} finally {
			overwriteGetLocale(original);
		}
	});
});

describe('the client bundle', () => {
	it("doesn't pull every locale's messages in through t()", () => {
		// A namespace import + lookup by a computed key can't tree-shake: it is
		// how every string in every language reached every page.
		const src = readFileSync('src/lib/i18n.svelte.ts', 'utf8');
		expect(src).not.toMatch(/from\s+['"]\$lib\/paraglide\/messages/);
	});
});
