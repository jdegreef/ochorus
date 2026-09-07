import { describe, expect, it } from 'vitest';
import { articleTopicSeo } from './articleTopics';

// The ten curated shelves (slug + chip title), mirroring topic_seed.py. Used to
// assert the visible intro and the meta blurb hold their separate contracts on
// EVERY curated topic, not just a sampled one.
const CURATED_TOPICS = [
	['prayer', 'On Prayer'],
	['holy-spirit', 'The Holy Spirit'],
	['deeper-life', 'The Deeper Life'],
	['grace-and-comfort', 'Grace & Comfort'],
	['revival-and-missions', 'Revival & Missions'],
	['faith-and-guidance', 'Faith & Guidance'],
	['the-gospel-call', 'The Gospel Call'],
	['enduring-classics', 'The Enduring Classics'],
	['the-way-of-holiness', 'The Way of Holiness'],
	['the-preached-word', 'The Preached Word']
] as const;

const wordCount = (s: string) => s.trim().split(/\s+/).length;

describe('articleTopicSeo', () => {
	it('returns the curated heading for a known topic', () => {
		const seo = articleTopicSeo('prayer', 'On Prayer');
		expect(seo.h1).toBe('Articles on Prayer');
		// blurb is the meta description; intro is the visible standfirst.
		expect(seo.blurb.length).toBeGreaterThan(0);
		expect(seo.intro.length).toBeGreaterThan(0);
	});

	it('gives every curated topic an 80–130-word visible intro', () => {
		// The full-width standfirst brief: each shelf opens with a real paragraph,
		// not a one-liner and not a wall of text.
		for (const [slug, title] of CURATED_TOPICS) {
			const n = wordCount(articleTopicSeo(slug, title).intro);
			expect(n, `${slug} intro is ${n} words (want 80–130)`).toBeGreaterThanOrEqual(80);
			expect(n, `${slug} intro is ${n} words (want 80–130)`).toBeLessThanOrEqual(130);
		}
	});

	it('keeps every curated blurb short enough to serve as a meta description', () => {
		// Why intro and blurb are separate fields: a meta description past ~160
		// chars is truncated in search. The intro can be long; the blurb cannot.
		for (const [slug, title] of CURATED_TOPICS) {
			const len = articleTopicSeo(slug, title).blurb.length;
			expect(len, `${slug} blurb is ${len} chars (keep ≤ 170)`).toBeLessThanOrEqual(170);
		}
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
		// The fallback intro is untuned (and may be short), but must never be empty
		// — the shelf always renders a standfirst.
		expect(seo.intro).toContain('brand New Topic');
		expect(seo.intro.length).toBeGreaterThan(0);
	});
});
