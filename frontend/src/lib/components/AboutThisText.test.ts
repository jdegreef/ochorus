import { mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import AboutThisText from './AboutThisText.svelte';
import type { BookDetail } from '$lib/library-public';

/**
 * "About this text" shows only what the API records, a row per value — and a
 * translation says only that it is one: the review state is admin-only
 * (CLAUDE.md), so both translated source types must render alike.
 */
const book = (over: Partial<BookDetail> = {}): BookDetail =>
	({
		slug: 'john-ploughmans-talk',
		language: 'en',
		title: "John Ploughman's Talk",
		source_type: 'public_domain',
		source_url: 'https://archive.org/details/johnploughmansta00spur',
		attribution: 'Public domain — first published 1869.',
		artwork_credit: 'John Constable, “Stoke-by-Nayland” (1836).',
		updated_at: '2026-10-10T18:43:49Z',
		public_domain: true,
		is_modern_edition: false,
		available_languages: ['en', 'es'],
		...over
	}) as BookDetail;

let target: HTMLElement;
let app: ReturnType<typeof mount> | null = null;
const render = (b: BookDetail) => {
	target = document.createElement('div');
	document.body.append(target);
	app = mount(AboutThisText, { target, props: { book: b } });
	return target;
};
const labels = (el: HTMLElement) => [...el.querySelectorAll('dt')].map((d) => d.textContent?.trim());

afterEach(() => {
	if (app) unmount(app);
	app = null;
	target?.remove();
});

describe('AboutThisText', () => {
	it('shows the source note, its link, the cover, the date and the rights', () => {
		const el = render(book());
		expect(labels(el)).toEqual(['Source', 'Cover', 'Last updated', 'Rights']);
		const link = el.querySelector<HTMLAnchorElement>('dd a[href^="https://archive.org"]');
		expect(link?.textContent).toBe('archive.org');
		expect(el.textContent).toContain('first published 1869');
		expect(el.textContent).toContain('The text is in the public domain.');
		expect(el.querySelector('a[href$="/legal#terms"]')).not.toBeNull();
	});

	it('omits every row it has no data for, but keeps the terms', () => {
		const el = render(
			book({ source_url: '', attribution: '', artwork_credit: null, updated_at: undefined, public_domain: false })
		);
		expect(labels(el)).toEqual(['Rights']);
		expect(el.textContent).not.toContain('public domain');
	});

	it('names a translation the same whatever its review state', () => {
		const shown = (['ai_unreviewed', 'ai_reviewed'] as const).map((source_type) => {
			const el = render(book({ language: 'es', source_type, attribution: '', source_url: '' }));
			const html = el.innerHTML;
			unmount(app!);
			app = null;
			target.remove();
			return html;
		});
		expect(shown[0]).toBe(shown[1]);
		expect(shown[0]).toContain('Translated from the English edition');
		expect(shown[0]).not.toMatch(/review|AI/);
	});

	it('links no English edition that is not published', () => {
		const el = render(book({ language: 'es', source_type: 'ai_reviewed', available_languages: ['es'] }));
		expect(labels(el)).not.toContain('Translation');
	});
});
