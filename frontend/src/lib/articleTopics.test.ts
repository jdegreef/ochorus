import { describe, expect, it } from 'vitest';
import { articleTopicSeo } from './articleTopics';

describe('articleTopicSeo', () => {
	it('returns the curated heading for a known topic', () => {
		const seo = articleTopicSeo('prayer', 'On Prayer');
		expect(seo.h1).toBe('Articles on Prayer');
		// The standfirst doubles as the meta description, so it must be non-empty.
		expect(seo.blurb.length).toBeGreaterThan(0);
	});

	it('leads every curated H1 with a real keyword, not the bare chip label', () => {
		// The whole point of the clean URL is a heading a crawler can index — so a
		// curated H1 must never be just "On Prayer"/"The Gospel Call". Each starts
		// with "Articles on …" or "Guides to …".
		for (const [slug, title] of [
			['prayer', 'On Prayer'],
			['holy-spirit', 'The Holy Spirit'],
			['enduring-classics', 'The Enduring Classics'],
			['the-gospel-call', 'The Gospel Call']
		] as const) {
			const { h1 } = articleTopicSeo(slug, title);
			expect(h1).toMatch(/^(Articles on|Guides to)\b/);
			expect(h1).not.toBe(title);
		}
	});

	it('falls back to a template for an unknown (DB-added) topic', () => {
		const seo = articleTopicSeo('brand-new-topic', 'Brand New Topic');
		expect(seo.h1).toBe('Articles on Brand New Topic');
		expect(seo.blurb).toContain('brand New Topic');
	});
});
