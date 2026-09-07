// SEO copy for a topic-filtered article shelf (`/articles/<topic>/`).
//
// The bare /articles index keeps the plain "Articles" heading; each topic view
// gets its own keyword-led H1 and standfirst, so the filtered page reads as a
// page about that subject rather than a duplicate of the index. The <title> is
// built from the H1 (`<h1> — Ochorus`, the site convention) and the standfirst
// doubles as the meta description, exactly as the topic and article pages reuse
// one description for the page and the crawl.
//
// The ten shelves are a curated set; a topic added later (the vocabulary is
// DB-owned) simply falls back to a template built from its chip title, so a new
// shelf is never wrong — only less tuned.
//
// DEBT: this is an English-only home for per-topic prose that the backend
// `Topic` model already owns a translatable form of (`Topic.description` +
// `TopicTranslation`). It is an acceptable first cut while articles are
// English-only, but when articles gain translations this copy must move to a
// translatable backend field (e.g. `Topic.article_h1` / `article_intro`) served
// through the API — this map cannot localize.

import type { ArticleSummary } from './library-public';
import { SITE_URL } from './config';
import { jsonLd } from './seo';

/** True when an article carries the given topic. `?? []` guards a lagging API
 *  that predates the `topics` field (version skew). Shared by the shelf filter,
 *  the topic page, and the legacy `?topic=` redirect so the predicate can't
 *  drift between them. */
export const articleHasTopic = (a: ArticleSummary, slug: string): boolean =>
	(a.topics ?? []).some((tc) => tc.slug === slug);

/** The `CollectionPage → hasPart → Article` JSON-LD both the index and each
 *  topic shelf emit, so the set reads as one entity to a crawler. One builder,
 *  not a copy per page (the shape intentionally differs from seo.ts's
 *  `collectionPage()` ItemList — an article collection lists Articles). */
export const articleCollectionLd = (
	name: string,
	description: string,
	url: string,
	articles: ArticleSummary[]
) =>
	jsonLd({
		'@context': 'https://schema.org',
		'@type': 'CollectionPage',
		name,
		description,
		url,
		hasPart: articles.map((a) => ({
			'@type': 'Article',
			headline: a.h1,
			url: `${SITE_URL}/articles/${a.slug}/`
		}))
	});

export interface ArticleTopicSeo {
	/** The visible <h1> for the shelf, and the stem of its <title>. */
	h1: string;
	/** Standfirst under the H1, reused as the meta description. */
	blurb: string;
}

const CURATED: Record<string, ArticleTopicSeo> = {
	prayer: {
		h1: 'Articles on Prayer',
		blurb:
			'Short readings on prayer — how to pray, how to keep praying, and how to pray ' +
			'for others — each one sending you on to a classic on the life of prayer.'
	},
	'holy-spirit': {
		h1: 'Articles on the Holy Spirit',
		blurb:
			'Plain-spoken readings on the person and work of the Holy Spirit — his ' +
			'indwelling, his power, and the Spirit-filled Christian life.'
	},
	'deeper-life': {
		h1: 'Articles on the Deeper Christian Life',
		blurb:
			'Readings on abiding in Christ, surrender, and the deeper life with God — ' +
			'each one pointing you to a classic worth reading in full.'
	},
	'grace-and-comfort': {
		h1: 'Articles on Grace & Comfort',
		blurb:
			'Readings on the grace and comfort of God — for grief, guilt, fear and ' +
			'weariness — each one pointing you to a classic that has steadied believers ' +
			'for centuries.'
	},
	'revival-and-missions': {
		h1: 'Articles on Revival & Missions',
		blurb:
			'Readings on revival, repentance, and the call to reach the lost — and the ' +
			'classics that carried the gospel to the ends of the earth.'
	},
	'faith-and-guidance': {
		h1: 'Articles on Faith & Guidance',
		blurb:
			"Readings on trusting God and finding his will — how to hear his voice, wait " +
			'on him, and grow in faith through every season.'
	},
	'the-gospel-call': {
		h1: 'Articles on the Gospel Call',
		blurb:
			'Readings on the heart of the gospel — being born again, assurance of ' +
			'salvation, and the oldest invitation there is.'
	},
	'enduring-classics': {
		h1: 'Guides to the Enduring Christian Classics',
		blurb:
			"Reader's guides to the great Christian classics — what each book is about, " +
			'why it still matters, and how to begin.'
	},
	'the-way-of-holiness': {
		h1: 'Articles on the Way of Holiness',
		blurb:
			'Readings on holiness and the pursuit of a Christlike life — overcoming sin, ' +
			'walking in humility, and following Jesus closely.'
	},
	'the-preached-word': {
		h1: 'Articles on Great Preaching',
		blurb:
			'Readings on the preached word and the sermons that shaped history — great ' +
			'preaching, and how to read it today.'
	}
};

/**
 * SEO copy for a topic shelf. Curated where we have it; otherwise a template
 * built from the localized chip title (`title`), so a DB-added topic still gets
 * a sensible, on-brand heading without a code change.
 */
export function articleTopicSeo(slug: string, title: string): ArticleTopicSeo {
	const curated = CURATED[slug];
	if (curated) return curated;
	// "The Gospel Call" → "the gospel call" for the mid-sentence blurb.
	const lower = title.charAt(0).toLowerCase() + title.slice(1);
	return {
		h1: `Articles on ${title}`,
		blurb: `Short readings on ${lower} — each one pointing you to a Christian classic worth reading in full.`
	};
}
